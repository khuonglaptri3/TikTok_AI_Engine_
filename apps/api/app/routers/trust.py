from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from apps.api.app.dependencies import ServiceContainer
from packages.absa import analyze_disclosure_and_promo, analyze_koc_vs_viewer_absa
from packages.absa.neural_absa import is_phobert_absa_available
from packages.common.exceptions import UnsupportedDomainError, ViralRagError
from packages.common.logging import StageTimer
from packages.data_contracts._validators import validate_timings_ms
from packages.data_contracts.multimodal import TrustAuditRequest, TrustAuditResponse
from packages.llm.prompts.templates import (
    detect_unsupported_epistemic_claim,
    is_blatant_out_of_domain_query,
)
from packages.seeding import compute_comment_filter_sensitivity, detect_seeding_comments

router = APIRouter(prefix="/api/v1/trust", tags=["seeding, absa, prosody & disclosure trust"])


def _container(request: Request) -> ServiceContainer:
    return request.app.state.container  # type: ignore[no-any-return]


class DisclosureCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    caption: str = ""
    transcript: str = ""
    hashtags: list[str] = Field(default_factory=list)
    is_ad: bool = False
    is_ec_video: bool = False
    question: str | None = None


@router.post("/audit-video", response_model=TrustAuditResponse)
async def audit_video_trust(payload: TrustAuditRequest) -> TrustAuditResponse:
    timer = StageTimer()
    if payload.absa_engine != "lexicon_v1" and not is_phobert_absa_available():
        raise ViralRagError(
            "MODEL_NOT_READY",
            "Fine-tuned PhoBERT_NER_T4-ABSA weights are not built on disk; run python -m pipelines.train_absa_phobert.",
            status_code=503,
        )
    with timer.measure("seeding_filter_ms"):
        cleansed = detect_seeding_comments(payload.video_id, payload.comments)
    with timer.measure("absa_comparison_ms"):
        comparison = analyze_koc_vs_viewer_absa(
            video_id=payload.video_id,
            caption=payload.caption,
            transcript=payload.transcript,
            comments=cleansed,
            is_ad=payload.is_ad,
            is_ec_video=payload.is_ec_video,
            hashtags=payload.hashtags,
            utterances=payload.utterances,
            absa_engine=payload.absa_engine,
        )
        sensitivity = compute_comment_filter_sensitivity(
            caption=payload.caption,
            transcript=payload.transcript,
            comments=cleansed,
            utterances=payload.utterances,
            video_id=payload.video_id,
        )
    return TrustAuditResponse(
        comparison=comparison,
        comments=cleansed,
        absa_model_used=payload.absa_engine,
        comment_filter_policy="diagnostic_only_unvalidated",
        filter_sensitivity=sensitivity,
        timings_ms=timer.finalize(),
    )


@router.get("/corpus-videos")
async def list_corpus_multimodal_videos(
    request: Request,
    require_voice: bool = Query(default=False),
    min_comments: int = Query(default=1, ge=0, le=500),
    limit: int = Query(default=60, ge=1, le=200),
) -> dict[str, Any]:
    timer = StageTimer()
    c = _container(request)
    with timer.measure("catalog_lookup_ms"):
        all_matching = c.multimodal.list_videos(
            require_voice=require_voice,
            min_comments=min_comments,
            limit=200,
        )
        sliced = all_matching[:limit]
    timings = validate_timings_ms(timer.finalize())
    return {
        "multimodal_available": c.multimodal.available,
        "snapshot_id": c.multimodal.snapshot_id,
        "total_matching": len(all_matching),
        "items": sliced,
        "timings_ms": timings,
    }


@router.get("/corpus-video/{video_id}")
async def audit_corpus_video_by_id(
    video_id: str,
    request: Request,
    absa_engine: Literal["auto", "lexicon_v1", "phobert_ner_t4_finetuned", "phobert_hybrid"] = Query(
        default="auto"
    ),
) -> dict[str, Any]:
    timer = StageTimer()
    c = _container(request)
    with timer.measure("corpus_lookup_ms"):
        bundle = c.multimodal.get_video_bundle(video_id)
    if bundle is None:
        raise ViralRagError(
            "VIDEO_NOT_FOUND",
            f"Video {video_id!r} was not found in verified multimodal corpus snapshot {c.multimodal.snapshot_id!r}.",
            status_code=404,
        )

    effective_engine: Literal["lexicon_v1", "phobert_ner_t4_finetuned", "phobert_hybrid"]
    if absa_engine == "auto":
        effective_engine = "phobert_hybrid" if is_phobert_absa_available() else "lexicon_v1"
    else:
        if absa_engine != "lexicon_v1" and not is_phobert_absa_available():
            raise ViralRagError(
                "MODEL_NOT_READY",
                "Fine-tuned PhoBERT_NER_T4-ABSA weights are not built on disk; run python -m pipelines.train_absa_phobert.",
                status_code=503,
            )
        effective_engine = absa_engine

    meta = bundle["video"]
    raw_comments = bundle["raw_comment_models"]
    raw_utterances = bundle["raw_utterance_models"]

    with timer.measure("seeding_filter_ms"):
        cleansed = detect_seeding_comments(meta["video_id"], raw_comments)
    with timer.measure("absa_comparison_ms"):
        comparison = analyze_koc_vs_viewer_absa(
            video_id=meta["video_id"],
            caption=meta["caption"],
            transcript=meta["transcript"],
            comments=cleansed,
            is_ad=bool(meta["is_ad"]),
            is_ec_video=bool(meta["is_ec_video"]),
            hashtags=meta["hashtags"],
            utterances=raw_utterances,
            absa_engine=effective_engine,
        )
        sensitivity = compute_comment_filter_sensitivity(
            caption=meta["caption"],
            transcript=meta["transcript"],
            comments=cleansed,
            utterances=raw_utterances,
            video_id=meta["video_id"],
        )

    final_timings = validate_timings_ms(timer.finalize())
    trust_resp = TrustAuditResponse(
        comparison=comparison,
        comments=cleansed,
        absa_model_used=effective_engine,
        comment_filter_policy="diagnostic_only_unvalidated",
        filter_sensitivity=sensitivity,
        timings_ms=final_timings,
    )
    return {
        "video": meta,
        "prosody_and_timing": bundle["prosody_and_timing"],
        "disclosure_and_promo": bundle["disclosure_and_promo"],
        "trust_audit": trust_resp.model_dump(),
        "timings_ms": final_timings,
    }


@router.post("/disclosure-check")
async def check_disclosure_and_promo_route(payload: DisclosureCheckRequest) -> dict[str, Any]:
    timer = StageTimer()
    if payload.question:
        epistemic = detect_unsupported_epistemic_claim(payload.question)
        if epistemic is not None:
            _, refusal_msg = epistemic
            raise UnsupportedDomainError(refusal_msg)
        if is_blatant_out_of_domain_query(payload.question):
            raise UnsupportedDomainError(
                "Câu hỏi nằm ngoài lĩnh vực kiểm toán Ẩm thực & F&B TikTok Việt Nam."
            )

    with timer.measure("disclosure_promo_ms"):
        res = analyze_disclosure_and_promo(
            caption=payload.caption,
            transcript=payload.transcript,
            is_ad=payload.is_ad,
            is_ec_video=payload.is_ec_video,
            hashtags=payload.hashtags,
        )
    timings = validate_timings_ms(timer.finalize())
    return {
        "disclosure_flag_status": res.disclosure_flag_status,
        "matched_indicators": res.matched_indicators,
        "matched_categories": res.matched_categories,
        "lexical_promo_score": res.lexical_promo_score,
        "sponsorship_ground_truth_status": res.sponsorship_ground_truth_status,
        "disclosure_target_note": res.disclosure_target_note,
        "timings_ms": timings,
    }
