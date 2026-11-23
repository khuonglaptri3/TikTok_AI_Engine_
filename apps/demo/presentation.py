from __future__ import annotations

import re
from typing import Any

_HANDLE_PREFIX_RE = re.compile(
    r"^(?:@([A-Za-z0-9_.\-]{1,32})|([A-Za-z0-9_.\-]*[0-9_.][A-Za-z0-9_.\-]*)):\s*(?!//)(.+)$",
    flags=re.DOTALL,
)


def parse_demo_comment_lines(raw_comments_lines: str) -> list[dict[str, str]]:
    """Parse manual demo comment lines without breaking bare https:// URLs or non-handle colons."""
    comments_payload: list[dict[str, str]] = []
    for idx, line in enumerate(raw_comments_lines.splitlines(), start=1):
        clean = line.strip()
        if not clean:
            continue
        m = _HANDLE_PREFIX_RE.match(clean)
        if m is not None:
            handle = (m.group(1) or m.group(2) or f"viewer_{idx}").strip().lstrip("@")
            txt = m.group(3).strip()
        else:
            handle = f"viewer_{idx}"
            txt = clean
        comments_payload.append({"comment_id": f"c{idx}", "author_handle": handle, "text": txt})
    return comments_payload


def format_benchmark_markdown(bench: dict[str, Any]) -> str:
    hours = bench.get("top_posting_hours") or []
    abstained = bool(bench.get("sparse_slice_abstained"))
    hours_str = ", ".join(
        f"**{h['hour']:02d}:00** ({int(h['median_plays']):,} views)" for h in hours[:4]
    ) or ("Tạm dừng xếp hạng do không đủ mẫu (< 5 video)" if abstained else "Chưa đủ mẫu")
    tags = ", ".join(f"`#{t}`" for t in (bench.get("top_hashtags") or [])[:6]) or "Không có"
    pois = " • ".join((bench.get("top_poi_venues") or [])[:5]) or (
        "Tạm dừng xếp hạng POI do không đủ mẫu (< 5 video)" if abstained else "Không có POI định vị trong lát cắt này"
    )
    applied = bench.get("applied_filters") or {}
    filter_desc = ", ".join(f"`{k}={v}`" for k, v in applied.items()) if applied else "Toàn bộ kho dữ liệu"
    cohort_start = bench.get("cohort_window_start") or "N/A"
    cohort_end = bench.get("cohort_window_end") or "N/A"
    obs_snap = bench.get("observation_snapshot") or "N/A"
    miss = bench.get("missingness") or {}
    miss_str = (
        f"thiếu lời thoại `{miss.get('transcript_missing_pct', 0):.1f}%` • "
        f"thiếu POI `{miss.get('poi_missing_pct', 0):.1f}%` • "
        f"thiếu thành phố `{miss.get('city_missing_pct', 0):.1f}%`"
        if miss
        else "không có dữ liệu thiếu (lát cắt rỗng)"
    )

    return (
        f"### Thống Kê Mô Tả Ngách Trong Kho Lịch Sử\n"
        f"- **Khoảng dữ liệu cohort:** `{cohort_start}` → `{cohort_end}` • **Mốc thu thập:** `{obs_snap}`\n"
        f"- **Lát cắt dữ liệu:** {filter_desc}\n"
        f"- **Quy mô mẫu (n):** `{bench.get('matched_videos', 0):,}` video "
        f"(`{bench.get('transcribed_videos', 0):,}` có lời thoại • `{bench.get('poi_tagged_videos', 0):,}` gắn GPS POI)\n"
        f"- **Tỷ lệ thiếu dữ liệu (Missingness):** {miss_str}\n"
        f"- **Lượt xem trung vị / P75:** `{int(bench.get('median_plays', 0)):,}` / `{int(bench.get('p75_plays', 0)):,}` views "
        f"(Tương tác trung vị: `{bench.get('median_engagement_rate', 0.0) * 100:.2f}%`)\n"
        f"- **Phân bố thời lượng (IQR Q25 – Trung vị – Q75):** `{bench.get('duration_q25_sec', 0):.0f}s` – "
        f"**`{bench.get('duration_median_sec', 0):.0f}s`** – `{bench.get('duration_q75_sec', 0):.0f}s`\n"
        f"- **Mật độ lời thoại ước tính:** `{bench.get('median_word_per_second', 0):.2f}` đơn vị cách trắng/giây "
        f"• **Số lượng Hashtag IQR:** `{bench.get('hashtag_q25', 0)}–{bench.get('hashtag_q75', 0)}` thẻ ({tags})\n"
        f"- **Giờ đăng có lượt xem trung vị cao trong mẫu:** {hours_str}\n"
        f"- **POI do nền tảng ghi nhận:** {pois}\n"
        "_Thống kê lịch sử có thiên lệch chọn mẫu; không chứng minh tác động tăng viral hay xu hướng hiện tại._"
    )


def format_evidence_cards_markdown(items: list[dict[str, Any]], mode: str = "bm25", total_cands: int = 0) -> str:
    if not items:
        return "_Không tìm thấy video bằng chứng phù hợp._"

    lines = [
        f"### Bằng Chứng Video Viral Truy Xuất (`mode={mode}`, `{total_cands}` ứng viên)\n"
    ]
    for card in items:
        cit = card.get("citation") or {}
        vid = cit.get("video_id", "")
        handle = cit.get("author_handle", "")
        url = cit.get("tiktok_url", "#")
        plays = int(cit.get("play_count") or 0)
        v_mult = float(cit.get("viral_multiplier") or 0.0)
        loc_parts = [p for p in (card.get("poi_name"), card.get("district_norm"), card.get("city_norm")) if p]
        loc_str = " — ".join(loc_parts) if loc_parts else "Việt Nam"
        beats = card.get("body_beats") or []
        beat_preview = "; ".join(beats[:2]) if beats else card.get("transcript_excerpt", "")[:180]

        lines.append(
            f"#### #{card.get('rank')} • [@{handle}]({url}) (`{vid}`) — **{plays:,} views** (`{v_mult:.1f}x` trung vị kênh)\n"
            f"- **Phân loại:** `{card.get('video_format')}` | `{card.get('food_category')}` | "
            f"`{card.get('price_tier')}` | `{card.get('duration_sec')}s` | 📍 {loc_str}\n"
            f"- **Hook gốc:** _{card.get('hook_text', '')}_\n"
            f"- **Ý chính / Nội dung:** {beat_preview}\n"
        )
    return "\n".join(lines)


def format_script_markdown(resp: dict[str, Any]) -> str:
    hooks = resp.get("hook_options") or []
    hooks_md = "\n".join(f"{i}. {h}" for i, h in enumerate(hooks, start=1))
    tags = " ".join(f"#{t}" for t in (resp.get("recommended_hashtags") or []))

    lines = [
        f"### Bản Nháp Kịch Bản (`mode={resp.get('generation_mode')}`, model=`{resp.get('model_used')}`)",
        "_Nội dung sáng tạo từ nguồn tham khảo lịch sử; cần kiểm chứng nhận định và trải nghiệm trước khi sử dụng._",
        f"**Bối cảnh quay:** {resp.get('setting')}  \n**Giọng điệu (Persona):** {resp.get('persona_tone')}",
        "#### 3 Phương Án Hook Mở Đầu (0–4s)",
        hooks_md,
        "#### Bảng Phân Cảnh & Lời Thoại Tính Theo Tốc Độ Nói Thực Nghiệm",
        "| Phân đoạn | Mốc thời gian | Góc máy & Hình ảnh | Lời thoại chi tiết | Số từ | Video tham chiếu |",
        "| :--- | :---: | :--- | :--- | :---: | :--- |",
    ]

    for b in resp.get("beats") or []:
        cites = ", ".join(f"`{c}`" for c in (b.get("cited_video_ids") or []))
        lines.append(
            f"| **{b.get('section_title')}** | `{b.get('time_range')}` | {b.get('visual_angle')} | "
            f"{b.get('dialogue')} | `{b.get('word_count')}` | {cites} |"
        )

    sa = resp.get("shooting_advice") or {}
    cam = "\n".join(f"- **Góc quay:** {x}" for x in (sa.get("camera_angles") or []))
    aud = "\n".join(f"- **Ánh sáng & Âm thanh:** {x}" for x in (sa.get("lighting_and_audio") or []))
    pac = "\n".join(f"- **Nhịp dựng:** {x}" for x in (sa.get("pacing_and_editing") or []))

    guard = resp.get("guardrail") or {}
    badge = "ĐẠT KIỂM TRA CẤU TRÚC" if guard.get("passed") else "CẦN CHỈNH SỬA"
    warn_list = guard.get("warnings") or []
    warn_md = "\n".join(f"  - ⚠️ {w}" for w in warn_list) if warn_list else "  - Chưa có kết quả xác minh nội dung từng nhận định."

    lines.extend(
        [
            f"\n**Caption gợi ý:** {resp.get('caption_draft')}  \n**Hashtags:** `{tags}`",
            "#### Hướng Dẫn Quay Dựng Thực Chiến",
            cam,
            aud,
            pac,
            f"#### Kiểm Định Guardrail: **{badge}**",
            f"- Tổng số từ: `{guard.get('total_words')}` từ • Thời lượng ước tính: `{guard.get('estimated_duration_sec')}s` "
            f"(Mục tiêu: `{guard.get('target_duration_sec')}s`, lệch `{guard.get('duration_delta_sec'):+.1f}s`) "
            f"• Tỷ lệ trích dẫn hợp lệ: `{guard.get('valid_citations_ratio', 1.0) * 100:.0f}%`\n{warn_md}",
        ]
    )
    return "\n".join(lines)


def format_timings_markdown(timings: dict[str, Any]) -> str:
    if not timings:
        return ""
    parts = [f"`{k}`: **{v} ms**" for k, v in timings.items()]
    return "**Độ trễ từng chặng (Stage Timings):** " + " • ".join(parts)


def format_trust_audit_markdown(data: dict[str, Any], hide_seeding: bool = False) -> str:
    comp = data.get("comparison") or {}
    koc = comp.get("koc_scores") or {}
    viewer = comp.get("viewer_clean_scores") or {}
    gap = float(comp.get("pr_hype_gap") or 0.0)
    risk = float(comp.get("undisclosed_pr_risk") or 0.0)
    flag_status = str(comp.get("disclosure_flag_status") or "unlabeled_unknown")
    lex_score = float(comp.get("lexical_promo_score") or 0.0)
    lex_cues = comp.get("promotional_language_indicators") or []
    pains = comp.get("viewer_pain_points") or []
    comments = data.get("comments") or []
    filter_policy = str(data.get("comment_filter_policy") or "diagnostic_only_unvalidated")
    sens = data.get("filter_sensitivity") or {}

    koc_summaries = comp.get("koc_aspect_summaries") or {}
    viewer_summaries = comp.get("viewer_aspect_summaries") or {}
    aspect_discrepancies = comp.get("aspect_discrepancies") or {}
    supported_aspects = comp.get("supported_overlapping_aspects") or []
    supported_disc = comp.get("supported_sentiment_discrepancy")
    abstention_reason = comp.get("discrepancy_abstention_reason")
    source_spans = comp.get("source_spans") or []
    has_m52 = bool(koc_summaries or viewer_summaries or aspect_discrepancies)

    sens_line = ""
    m52_filter_line = ""
    threshold_line = ""
    if sens:
        b_mean = sens.get("before_filter_viewer_mean")
        b_str = f"`{float(b_mean):+.4f}`" if b_mean is not None else "`N/A`"
        if sens.get("after_filter_abstained") or sens.get("after_filter_viewer_mean") is None:
            sens_line = (
                f"- **Độ nhạy trước/sau lọc (Filter Sensitivity):** Trước lọc {b_str} "
                f"→ Sau loại `{sens.get('flagged_indicator_count', 0)}` bình luận có chỉ dấu: "
                "`tạm dừng (0 bình luận chưa gắn cờ — không suy diễn điểm 0.0)`"
            )
        else:
            sens_line = (
                f"- **Độ nhạy trước/sau lọc (Filter Sensitivity):** Trước lọc {b_str} "
                f"→ Sau loại `{sens.get('flagged_indicator_count', 0)}` bình luận có chỉ dấu: "
                f"`{float(sens.get('after_filter_viewer_mean') or 0.0):+.4f}` "
                f"(chênh `{float(sens.get('mean_score_shift') or 0.0):+.4f}`)"
            )

        if (
            "before_filter_supported_discrepancy" in sens
            or "after_filter_supported_discrepancy" in sens
        ):
            b_sup_disc = sens.get("before_filter_supported_discrepancy")
            a_sup_disc = sens.get("after_filter_supported_discrepancy")
            sup_shift = sens.get("supported_discrepancy_shift")
            b_sup_str = (
                f"`{float(b_sup_disc):+.4f}`"
                if b_sup_disc is not None
                else "`tạm dừng (<3 bình luận)`"
            )
            a_sup_str = (
                f"`{float(a_sup_disc):+.4f}`"
                if a_sup_disc is not None
                else "`tạm dừng (<3 bình luận)`"
            )
            shift_str = f" (chênh `{float(sup_shift):+.4f}`)" if sup_shift is not None else ""
            m52_filter_line = (
                f"- **Độ nhạy độ lệch giao thoa M5.2 (Supported Discrepancy Shift):** "
                f"Trước lọc {b_sup_str} → Sau lọc {a_sup_str}{shift_str}"
            )

        grid = sens.get("threshold_sensitivity")
        if isinstance(grid, list) and grid:
            valid_discs = [
                float(cell["supported_sentiment_discrepancy"])
                for cell in grid
                if cell.get("supported_sentiment_discrepancy") is not None
            ]
            aspect_counts = [int(cell.get("supported_aspect_count") or 0) for cell in grid]
            if valid_discs:
                threshold_line = (
                    f"- **Độ nhạy ngưỡng M5.2 (`polarity_tau` × `min_viewer_comments`):** "
                    f"`{len(valid_discs)}/{len(grid)}` cấu hình đủ hỗ trợ; độ lệch từ "
                    f"`{min(valid_discs):+.4f}` đến `{max(valid_discs):+.4f}` "
                    f"(số khía cạnh giao thoa `{min(aspect_counts)}..{max(aspect_counts)}`)"
                )
            else:
                threshold_line = (
                    f"- **Độ nhạy ngưỡng M5.2 (`polarity_tau` × `min_viewer_comments`):** "
                    f"`0/{len(grid)}` cấu hình đủ hỗ trợ (`tạm dừng` trên toàn lưới; số khía cạnh giao thoa `0`)"
                )

    m52_disc_line = ""
    if has_m52 or supported_disc is not None or abstention_reason:
        if supported_disc is not None and supported_aspects:
            aspect_tags = ", ".join(f"`{a}`" for a in supported_aspects)
            m52_disc_line = (
                f"- **Độ lệch cảm xúc quan sát được (Sentiment Discrepancy):** "
                f"`{float(supported_disc):+.2f}` trên khía cạnh giao thoa đủ hỗ trợ (`>=3` bình luận): "
                f"{aspect_tags} _(chỉ phản ánh chênh lệch lời thoại vs bình luận quan sát được; "
                "không khẳng định lừa dối, sự thật vệ sinh hay đồng thuận thực khách)_"
            )
        else:
            reason_str = str(
                abstention_reason or "insufficient_overlapping_aspect_support_min_3_comments"
            )
            m52_disc_line = (
                f"- **Độ lệch cảm xúc quan sát được (Sentiment Discrepancy):** "
                f"`tạm dừng ({reason_str})` — số bình luận người xem chưa gắn cờ trên khía cạnh "
                "giao thoa `< 3` (cần `>= 3` để so sánh) _(không suy diễn điểm `0.0`, không khẳng định "
                "lừa dối, sự thật vệ sinh hay đồng thuận thực khách)_"
            )

    cues_preview = ", ".join(f"`{c}`" for c in lex_cues[:5]) if lex_cues else "_Không ghi nhận từ khóa quảng bá_"
    lines = [
        "### Chẩn Đoán ABSA Và Chỉ Dấu Bình Luận (Baseline Chẩn Đoán)",
        "_Điểm chưa hiệu chuẩn trên nhãn độc lập; chỉ hiển thị chỉ dấu quan sát (trùng lặp/liên hệ/nhiễu), không khẳng định bot, thanh toán, tài trợ ngầm hay danh tính khách._",
        f"- **Trạng thái gắn cờ nền tảng (Observed Flag):** `{flag_status}` _(mục chưa gắn cờ vẫn là `unlabeled_unknown`, không phải bằng chứng không tài trợ)_",
        f"- **Chỉ dấu ngôn ngữ quảng bá (Lexical Promo):** `{lex_score:.2f}` • {cues_preview}",
        f"- **Chính sách lọc M5.1:** `{filter_policy}` (không tự động ẩn cho tới khi đạt chuẩn xác thực `>=150` bình luận thật)",
        f"- **Chênh lệch điểm cảm xúc heuristic:** `{gap:+.2f}` • **Heuristic tổng hợp cũ:** `{risk:.2f}` _(không phải xác suất tài trợ ngầm; nghiên cứu tài trợ ẩn đang hoãn)_",
        *( [m52_disc_line] if m52_disc_line else [] ),
        f"- **Bình luận không có chỉ dấu:** `{comp.get('clean_comment_count', 0)}` • **Bình luận có chỉ dấu quan sát:** `{comp.get('seeding_comment_count', 0)}`",
        *( [sens_line] if sens_line else [] ),
        *( [m52_filter_line] if m52_filter_line else [] ),
        *( [threshold_line] if threshold_line else [] ),
        "",
        "| Khía cạnh (Aspect) | Điểm lời thoại | Điểm bình luận chưa gắn cờ | Độ lệch quan sát (Sentiment Discrepancy) |",
        "| :--- | :---: | :---: | :--- |",
    ]
    for key, label in (
        ("taste", "Hương vị (Taste)"),
        ("price", "Giá cả (Price)"),
        ("hygiene", "Vệ sinh & Không gian (Hygiene)"),
        ("service", "Phục vụ (Service)"),
    ):
        if has_m52:
            k_sum = koc_summaries.get(key) or {}
            k_pres = str(k_sum.get("presence_status") or "absent_unknown")
            k_pol = str(k_sum.get("polarity_label") or "unknown")
            k_mean = k_sum.get("mean_score")
            k_cnt = int(k_sum.get("mention_unit_count") or 0)
            if k_pres == "observed" and k_mean is not None:
                k_cell = f"`observed` • `{k_pol}` (`{float(k_mean):+.2f}`, `n={k_cnt}`)"
            else:
                k_cell = "`absent_unknown` (`unknown`, `N/A`, `n=0`)"

            v_sum = viewer_summaries.get(key) or {}
            v_pres = str(v_sum.get("presence_status") or "absent_unknown")
            v_pol = str(v_sum.get("polarity_label") or "unknown")
            v_mean = v_sum.get("mean_score")
            v_cnt = int(v_sum.get("mention_unit_count") or 0)
            if v_pres == "observed" and v_mean is not None:
                v_cell = f"`observed` • `{v_pol}` (`{float(v_mean):+.2f}`, `n={v_cnt}`)"
            else:
                v_cell = f"`absent_unknown` (`unknown`, `N/A`, `n={v_cnt}`)"

            d_det = aspect_discrepancies.get(key) or {}
            c_status = str(d_det.get("comparison_status") or "abstained_creator_absent")
            s_disc = d_det.get("sentiment_discrepancy")
            v_sup = int(
                d_det["viewer_support_count"]
                if d_det.get("viewer_support_count") is not None
                else v_cnt
            )
            min_req = int(d_det.get("min_viewer_support_required") or 3)
            if c_status == "compared_supported_overlap" and s_disc is not None:
                d_cell = f"`{float(s_disc):+.2f}` (`{c_status}`, `n={v_sup}>={min_req}`)"
            else:
                d_cell = f"`tạm dừng` (`{c_status}`, `n={v_sup}/{min_req}`)"
            lines.append(f"| **{label}** | {k_cell} | {v_cell} | {d_cell} |")
        else:
            ks = float(koc.get(key) or 0.0)
            vs = float(viewer.get(key) or 0.0)
            note = f"{ks - vs:+.2f}; cần kiểm tra nguồn và độ phủ khía cạnh"
            lines.append(f"| **{label}** | `{ks:+.2f}` | `{vs:+.2f}` | {note} |")

    if pains:
        lines.append("\n#### Điểm Phàn Nàn Thực Tế Từ Người Xem (Pain Points)")
        lines.extend(f"- {p}" for p in pains)

    if source_spans:
        lines.append("\n#### Bằng Chứng Trích Dẫn Gốc (Source Spans)")
        for sp in source_spans:
            unit_id = str(sp.get("unit_id") or "unit")
            start_c = int(sp.get("start_char") or 0)
            end_c = int(sp.get("end_char") or 0)
            aspect = str(sp.get("aspect") or "")
            pol_lbl = str(sp.get("polarity_label") or "neutral")
            pol_score = float(sp.get("polarity_score") or 0.0)
            span_txt = " ".join(str(sp.get("span_text") or "").splitlines())
            lines.append(
                f'- `[{unit_id} @ {start_c}:{end_c}]` (`{aspect}`, `{pol_lbl}`, `{pol_score:+.2f}`): "{span_txt}"'
            )

    shown = [c for c in comments if (not hide_seeding or not c.get("is_seeding"))]
    lines.append(
        f"\n#### Danh Sách Bình Luận ({'Đã ẩn bình luận có chỉ dấu' if hide_seeding else 'Chế độ chẩn đoán — hiển thị đầy đủ'})"
    )
    for c in shown:
        obs_lbl = c.get("observable_label") or (c.get("seeding_reason") if c.get("is_seeding") else "no_indicator_observed")
        tag = f"⚑ `[{obs_lbl}]`" if c.get("is_seeding") else "ℹ️ `[no_indicator_observed]`"
        safe_txt = " ".join(str(c.get("text") or "").splitlines())
        lines.append(f"- {tag} **@{c.get('author_handle') or 'user'}**: {safe_txt}")
    return "\n".join(lines)

