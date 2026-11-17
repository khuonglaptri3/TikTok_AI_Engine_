from __future__ import annotations

from typing import Any

from packages.data_contracts.script import GuardrailReport, ScriptBeat

CLICHE_PHRASES: tuple[str, ...] = (
    "ngon gì đâu luôn á",
    "nhức cái nách",
    "cứu cái nách",
    "đỉnh của chóp",
    "ngon xỉu up xỉu down",
    "siêu phẩm vũ trụ",
)


def _fmt_mm_ss(seconds: float) -> str:
    sec_int = max(0, int(round(seconds)))
    mins, secs = divmod(sec_int, 60)
    return f"{mins:02d}:{secs:02d}"


def recalculate_timeline_and_verify(
    raw_beats: list[dict[str, Any]],
    hook_options: list[str],
    target_duration_sec: float,
    niche_wps: float,
    valid_evidence_ids: set[str],
) -> tuple[list[ScriptBeat], GuardrailReport]:
    """Deterministically recompute mm:ss beat timestamps from word counts and audit citations/clichés."""
    effective_wps = max(2.0, min(float(niche_wps or 3.3), 5.0))
    cursor_sec = 0.0
    verified_beats: list[ScriptBeat] = []

    total_citations = 0
    valid_citations = 0

    all_text_parts = list(hook_options)

    for idx, b in enumerate(raw_beats, start=1):
        dialogue = str(b.get("dialogue") or "").strip()
        all_text_parts.append(dialogue)
        wc = len(dialogue.split())
        beat_dur = max(3.0, wc / effective_wps)
        start_sec = cursor_sec
        end_sec = cursor_sec + beat_dur
        cursor_sec = end_sec

        submitted = b.get("cited_video_ids")
        raw_cites = submitted if isinstance(submitted, list) else []
        clean_cites: list[str] = []
        for cid in raw_cites:
            cid_s = str(cid).strip()
            if not cid_s:
                continue
            total_citations += 1
            if cid_s in valid_evidence_ids:
                valid_citations += 1
                if cid_s not in clean_cites:
                    clean_cites.append(cid_s)

        verified_beats.append(
            ScriptBeat(
                section_title=str(b.get("section_title") or f"Phần {idx}"),
                time_range=f"{_fmt_mm_ss(start_sec)}-{_fmt_mm_ss(end_sec)}",
                visual_angle=str(b.get("visual_angle") or "Góc cận cảnh món ăn ánh sáng tự nhiên"),
                dialogue=dialogue,
                word_count=wc,
                cited_video_ids=clean_cites,
            )
        )

    combined_lower = " ".join(all_text_parts).lower()
    detected_cliches = [phrase for phrase in CLICHE_PHRASES if phrase in combined_lower]

    total_words = sum(beat.word_count for beat in verified_beats)
    estimated_sec = round(cursor_sec, 1)
    delta_sec = round(estimated_sec - target_duration_sec, 1)
    cite_ratio = round(valid_citations / total_citations, 3) if total_citations > 0 else 0.0
    covered_beats = sum(bool(beat.cited_video_ids) for beat in verified_beats)
    coverage = covered_beats / len(verified_beats) if verified_beats else 0.0
    complete_content = bool(verified_beats) and all(beat.word_count > 0 for beat in verified_beats)
    timing_valid = target_duration_sec > 0 and abs(delta_sec) <= max(2.0, target_duration_sec * 0.05)

    warnings: list[str] = []
    if detected_cliches:
        warnings.append(f"Phát hiện cụm từ sáo rỗng cần tránh: {', '.join(detected_cliches)}")
    if not timing_valid:
        warnings.append(
            f"Thời lượng ước tính ({estimated_sec}s) lệch {delta_sec:+.1f}s so với mục tiêu ({target_duration_sec}s) ở tốc độ {effective_wps:.2f} từ/giây."
        )
    if cite_ratio < 1.0:
        warnings.append("Một số mã trích dẫn video không khớp kho bằng chứng đã được lọc bỏ tự động.")
    if not complete_content:
        warnings.append("Kịch bản cần có lời thoại không rỗng trong mọi phân đoạn.")
    if coverage < 1.0:
        warnings.append("Một số phân đoạn chưa có video tham chiếu; hệ thống không tự gán nguồn.")
    warnings.append("Kiểm tra cấu trúc, mã nguồn và thời lượng; chưa xác minh nội dung từng nhận định với nguồn.")

    passed = complete_content and timing_valid and not detected_cliches and cite_ratio == 1.0 and coverage == 1.0
    report = GuardrailReport(
        passed=passed,
        estimated_duration_sec=estimated_sec,
        target_duration_sec=round(float(target_duration_sec), 1),
        duration_delta_sec=delta_sec,
        total_words=total_words,
        valid_citations_ratio=cite_ratio,
        cliche_phrases_detected=detected_cliches,
        warnings=warnings,
        citation_coverage_ratio=coverage,
        timing_valid=timing_valid,
    )
    return verified_beats, report
