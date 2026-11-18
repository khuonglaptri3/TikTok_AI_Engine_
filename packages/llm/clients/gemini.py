from __future__ import annotations

import json
import re
import threading
import time
from collections import deque
from typing import Any

from packages.common.exceptions import ProviderKeyMissingError, QuotaBlockedError
from packages.common.logging import redact_secrets
from packages.common.settings import MAX_LLM_CALLS_PER_TURN, AppSettings


class SlidingWindowRateLimiter:
    """Thread-safe RPM sliding-window limiter (optional Redis backend, in-memory fallback)."""

    def __init__(self, max_rpm: int = 15, redis_url: str | None = None) -> None:
        self.max_rpm = max(1, max_rpm)
        self._lock = threading.Lock()
        self._timestamps: deque[float] = deque()
        self._redis: Any = None
        if redis_url:
            try:
                import redis  # type: ignore[import-not-found, import-untyped]

                client = redis.Redis.from_url(redis_url, socket_connect_timeout=0.3, socket_timeout=0.3)
                client.ping()
                self._redis = client
            except Exception:
                self._redis = None

    def acquire(self, key: str = "gemini_free_tier") -> None:
        now = time.time()
        window_start = now - 60.0

        if self._redis is not None:
            try:
                r_key = f"tiktok_rag:ratelimit:{key}"
                pipe = self._redis.pipeline()
                pipe.zremrangebyscore(r_key, 0, window_start)
                pipe.zcard(r_key)
                _, current_count = pipe.execute()
                if int(current_count) >= self.max_rpm:
                    raise QuotaBlockedError(
                        f"Free-Tier RPM limit ({self.max_rpm} req/min) reached. Wait briefly or use 'offline_grounded' mode."
                    )
                self._redis.zadd(r_key, {f"{now:.6f}": now})
                self._redis.expire(r_key, 65)
                return
            except QuotaBlockedError:
                raise
            except Exception:
                self._redis = None

        with self._lock:
            while self._timestamps and self._timestamps[0] <= window_start:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.max_rpm:
                raise QuotaBlockedError(
                    f"Free-Tier RPM limit ({self.max_rpm} req/min) reached. Wait briefly or use 'offline_grounded' mode."
                )
            self._timestamps.append(now)


class BoundedGeminiClient:
    """Zero-paid-fallback Gemini client reading GEMINI_API_KEY strictly from AppSettings."""

    def __init__(
        self,
        settings: AppSettings,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        self.settings = settings
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(
            max_rpm=settings.rate_limit_rpm,
            redis_url=settings.redis_url,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.gemini_api_key.strip())

    def _call_gemini_sdk(self, prompt: str, timeout_ms: int) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ProviderKeyMissingError(f"google-genai SDK is unavailable: {exc}") from exc

        api_key = self.settings.gemini_api_key.strip()
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )
        resp = client.models.generate_content(
            model=self.settings.gemini_fast_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.35,
                response_mime_type="application/json",
            ),
        )
        return (resp.text or "").strip()

    def generate_structured_json(self, prompt: str, turn_calls_used: int = 0) -> dict[str, Any]:
        api_key = self.settings.gemini_api_key.strip()
        if not api_key:
            raise ProviderKeyMissingError(
                "GEMINI_API_KEY is not set in .env. Configure a Free-Tier Gemini key or switch generation_mode to 'offline_grounded'."
            )
        if type(turn_calls_used) is not int or turn_calls_used < 0:
            raise QuotaBlockedError("Consumed LLM call count must be a non-negative integer.")
        configured_budget = self.settings.max_llm_calls_per_turn
        if type(configured_budget) is not int or configured_budget < 1:
            raise QuotaBlockedError("Configured LLM call budget must be a positive integer.")
        turn_call_budget = min(configured_budget, MAX_LLM_CALLS_PER_TURN)
        if turn_calls_used >= turn_call_budget:
            raise QuotaBlockedError(
                f"Per-turn LLM call budget ({turn_call_budget} calls/turn) reached. Switch to 'offline_grounded'."
            )

        self.rate_limiter.acquire()
        timeout_ms = max(1000, int(round(self.settings.llm_deadline_seconds * 1000.0)))

        try:
            raw_text = self._call_gemini_sdk(prompt, timeout_ms=timeout_ms)
        except ProviderKeyMissingError:
            raise
        except TimeoutError as exc:
            raise QuotaBlockedError(
                f"Gemini request deadline exceeded ({self.settings.llm_deadline_seconds:.1f}s timeout)."
            ) from exc
        except Exception as exc:
            msg = redact_secrets(str(exc))
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                raise QuotaBlockedError(f"Gemini Free-Tier quota exhausted: {msg[:180]}") from exc
            if "timeout" in msg.lower() or "timed out" in msg.lower() or "deadline" in msg.lower():
                raise QuotaBlockedError(
                    f"Gemini request timeout ({self.settings.llm_deadline_seconds:.1f}s): {msg[:160]}"
                ) from exc
            raise QuotaBlockedError(f"Gemini generation failed within Free-Tier bounds: {msg[:180]}") from exc

        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.DOTALL).strip()

        parsed = json.loads(raw_text, strict=False)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini structured response did not return a JSON object")
        return parsed
