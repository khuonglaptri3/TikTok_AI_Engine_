from __future__ import annotations

from fastapi import APIRouter

from packages.absa import analyze_koc_vs_viewer_absa
from packages.common.logging import StageTimer
from packages.data_contracts.multimodal import TrustAuditRequest, TrustAuditResponse
from packages.seeding import compute_comment_filter_sensitivity, detect_seeding_comments

router = APIRouter(prefix="/api/v1/trust", tags=["seeding & absa trust"])


@router.post("/audit-video", response_model=TrustAuditResponse)
async def audit_video_trust(payload: TrustAuditRequest) -> TrustAuditResponse:
    timer = StageTimer()
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
        comment_filter_policy="diagnostic_only_unvalidated",
        filter_sensitivity=sensitivity,
        timings_ms=timer.finalize(),
    )
