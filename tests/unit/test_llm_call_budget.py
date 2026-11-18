from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.common.exceptions import QuotaBlockedError
from packages.common.settings import AppSettings
from packages.llm import BoundedGeminiClient, SlidingWindowRateLimiter


@pytest.mark.parametrize("budget", [3, 5, 0, -1])
def test_settings_reject_out_of_policy_call_budgets(budget: int) -> None:
    with pytest.raises(ValidationError):
        AppSettings(max_llm_calls_per_turn=budget)


@pytest.mark.parametrize("budget", ["3", "5"])
def test_environment_cannot_raise_the_two_call_ceiling(
    budget: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TIKTOK_RAG_MAX_LLM_CALLS_PER_TURN", budget)
    monkeypatch.setenv("GEMINI_API_KEY", "")
    with pytest.raises(ValidationError):
        AppSettings.from_env(dotenv_path=tmp_path / "absent.env")


@pytest.mark.parametrize("used", [2, 3])
def test_client_blocks_exhausted_budget_even_with_unvalidated_settings(
    used: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pydantic model_copy intentionally skips validation; the client must retain its own cap.
    settings = AppSettings(gemini_api_key="synthetic-offline-key").model_copy(
        update={"max_llm_calls_per_turn": 5}
    )
    limiter = SlidingWindowRateLimiter(max_rpm=1, redis_url=None)
    client = BoundedGeminiClient(settings, rate_limiter=limiter)
    sdk_calls: list[str] = []

    def fake_sdk(prompt: str, timeout_ms: int) -> str:
        sdk_calls.append(prompt)
        return '{"unexpected": true}'

    monkeypatch.setattr(client, "_call_gemini_sdk", fake_sdk)
    with pytest.raises(QuotaBlockedError):
        client.generate_structured_json("exhausted budget", turn_calls_used=used)
    assert sdk_calls == []
    # Rejected budget checks must not consume the one remaining RPM slot.
    limiter.acquire()


@pytest.mark.parametrize("used", [-1, True, 0.5, float("nan"), float("inf"), "0", None])
def test_invalid_consumed_call_counts_fail_closed(
    used: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = BoundedGeminiClient(
        AppSettings(gemini_api_key="synthetic-offline-key"),
        rate_limiter=SlidingWindowRateLimiter(max_rpm=1, redis_url=None),
    )

    def fake_sdk(prompt: str, timeout_ms: int) -> str:
        return '{"unexpected": true}'

    monkeypatch.setattr(client, "_call_gemini_sdk", fake_sdk)
    with pytest.raises(QuotaBlockedError):
        client.generate_structured_json("invalid counter", turn_calls_used=used)  # type: ignore[arg-type]
    client.rate_limiter.acquire()


@pytest.mark.parametrize("budget", [float("nan"), float("inf")])
@pytest.mark.parametrize("used", [0, 2])
def test_nonfinite_copied_budgets_fail_closed(
    budget: float, used: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = AppSettings(gemini_api_key="synthetic-offline-key").model_copy(
        update={"max_llm_calls_per_turn": budget}
    )
    client = BoundedGeminiClient(
        settings, rate_limiter=SlidingWindowRateLimiter(max_rpm=1, redis_url=None)
    )
    sdk_calls: list[str] = []

    def fake_sdk(prompt: str, timeout_ms: int) -> str:
        sdk_calls.append(prompt)
        return '{"unexpected": true}'

    monkeypatch.setattr(client, "_call_gemini_sdk", fake_sdk)
    with pytest.raises(QuotaBlockedError):
        client.generate_structured_json("invalid copied budget", turn_calls_used=used)
    assert sdk_calls == []
    client.rate_limiter.acquire()


@pytest.mark.parametrize(("budget", "used"), [(1, 1), (2, 2), (2, 3)])
def test_configured_call_budget_still_blocks_at_its_own_boundary(
    budget: int, used: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = BoundedGeminiClient(
        AppSettings(gemini_api_key="synthetic-offline-key", max_llm_calls_per_turn=budget),
        rate_limiter=SlidingWindowRateLimiter(max_rpm=1, redis_url=None),
    )

    def fake_sdk(prompt: str, timeout_ms: int) -> str:
        return '{"unexpected": true}'

    monkeypatch.setattr(client, "_call_gemini_sdk", fake_sdk)
    with pytest.raises(QuotaBlockedError):
        client.generate_structured_json("configured exhausted budget", turn_calls_used=used)
    client.rate_limiter.acquire()


@pytest.mark.parametrize(("budget", "used"), [(1, 0), (2, 0), (2, 1)])
def test_eligible_calls_return_the_provider_json(
    budget: int, used: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = BoundedGeminiClient(
        AppSettings(gemini_api_key="synthetic-offline-key", max_llm_calls_per_turn=budget),
        rate_limiter=SlidingWindowRateLimiter(max_rpm=1, redis_url=None),
    )

    def fake_sdk(prompt: str, timeout_ms: int) -> str:
        assert prompt == "eligible budget"
        assert timeout_ms == 30000
        return '{"answer": "allowed"}'

    monkeypatch.setattr(client, "_call_gemini_sdk", fake_sdk)
    assert client.generate_structured_json("eligible budget", turn_calls_used=used) == {
        "answer": "allowed"
    }
