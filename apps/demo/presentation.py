from __future__ import annotations

from typing import Any


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


def format_trust_audit_markdown(data: dict[str, Any], hide_seeding: bool = True) -> str:
    comp = data.get("comparison") or {}
    koc = comp.get("koc_scores") or {}
    viewer = comp.get("viewer_clean_scores") or {}
    gap = float(comp.get("pr_hype_gap") or 0.0)
    risk = float(comp.get("undisclosed_pr_risk") or 0.0)
    pains = comp.get("viewer_pain_points") or []
    comments = data.get("comments") or []

    lines = [
        "### Chẩn Đoán ABSA Và Mẫu Bình Luận (Baseline Heuristic)",
        "_Điểm chưa được hiệu chuẩn trên nhãn độc lập; không xác minh khách thật, bot, seeding hay tài trợ không công khai._",
        f"- **Chênh lệch điểm cảm xúc heuristic:** `{gap:+.2f}` • **Chỉ số quảng bá heuristic:** `{risk:.2f}` (không phải xác suất)",
        f"- **Bình luận hợp lệ:** `{comp.get('clean_comment_count', 0)}` • **Bình luận nghi Seeding/Spam bị lọc:** `{comp.get('seeding_comment_count', 0)}`",
        "",
        "| Khía cạnh (Aspect) | Điểm lời thoại | Điểm bình luận giữ lại | Chênh lệch |",
        "| :--- | :---: | :---: | :--- |",
    ]
    for key, label in (
        ("taste", "Hương vị (Taste)"),
        ("price", "Giá cả (Price)"),
        ("hygiene", "Vệ sinh & Không gian (Hygiene)"),
        ("service", "Phục vụ (Service)"),
    ):
        ks = float(koc.get(key) or 0.0)
        vs = float(viewer.get(key) or 0.0)
        note = f"{ks - vs:+.2f}; cần kiểm tra nguồn và độ phủ khía cạnh"
        lines.append(f"| **{label}** | `{ks:+.2f}` | `{vs:+.2f}` | {note} |")

    if pains:
        lines.append("\n#### Điểm Phàn Nàn Thực Tế Từ Người Xem (Pain Points)")
        lines.extend(f"- {p}" for p in pains)

    shown = [c for c in comments if (not hide_seeding or not c.get("is_seeding"))]
    lines.append(f"\n#### Danh Sách Bình Luận ({'Đã ẩn Seeding' if hide_seeding else 'Hiển thị tất cả'})")
    for c in shown:
        tag = f"🚫 `[SEEDING: {c.get('seeding_reason')}]`" if c.get("is_seeding") else "✅ `[CLEAN]`"
        lines.append(f"- {tag} **@{c.get('author_handle') or 'user'}**: {c.get('text')}")
    return "\n".join(lines)

