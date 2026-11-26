"""Bounded Gemini Free-Tier client, evidence-grounded prompts, and deterministic guardrails."""

from packages.llm.clients.gemini import BoundedGeminiClient, SlidingWindowRateLimiter
from packages.llm.guardrails.verifier import CLICHE_PHRASES, recalculate_timeline_and_verify
from packages.llm.prompts.templates import (
    build_grounded_script_prompt,
    check_fnb_domain_relevance,
    detect_unsupported_epistemic_claim,
    is_blatant_out_of_domain_query,
)

__all__ = [
    "BoundedGeminiClient",
    "CLICHE_PHRASES",
    "SlidingWindowRateLimiter",
    "build_grounded_script_prompt",
    "check_fnb_domain_relevance",
    "detect_unsupported_epistemic_claim",
    "is_blatant_out_of_domain_query",
    "recalculate_timeline_and_verify",
]
