"""Visual HTML renderers and design-system tokens for the mounted Gradio /demo/ UI."""
from __future__ import annotations

import html
from typing import Any

import gradio as gr

DEMO_CSS = """
:root {
  --vfs-primary: #1e40af;
  --vfs-primary-soft: #eff6ff;
  --vfs-secondary: #3b82f6;
  --vfs-accent: #d97706;
  --vfs-bg: #f8fafc;
  --vfs-card: #ffffff;
  --vfs-border: #e2e8f0;
  --vfs-text: #0f172a;
  --vfs-muted: #475569;
  --vfs-mono: "JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, monospace;
  --vfs-sans: "Be Vietnam Pro", "Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.gradio-container {
  font-family: var(--vfs-sans) !important;
  background: var(--vfs-bg) !important;
  color: var(--vfs-text) !important;
  max-width: 1440px !important;
  margin: 0 auto !important;
}
.vfs-hero {
  background: var(--vfs-card);
  border: 1px solid var(--vfs-border);
  border-left: 5px solid var(--vfs-primary);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.vfs-hero-top {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.vfs-hero h1 {
  margin: 0 0 4px 0;
  font-size: 1.35rem;
  font-weight: 700;
  color: #1e3a8a;
}
.vfs-hero p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--vfs-muted);
}
.vfs-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.vfs-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  border: 1px solid var(--vfs-border);
  background: #f1f5f9;
  color: #334155;
  font-variant-numeric: tabular-nums;
}
.vfs-pill-blue { background: #eff6ff; color: #1e40af; border-color: #bfdbfe; }
.vfs-pill-green { background: #ecfdf5; color: #065f46; border-color: #a7f3d0; }
.vfs-pill-amber { background: #fffbeb; color: #92400e; border-color: #fde68a; }
.vfs-pill-red { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
.vfs-pill-mono { font-family: var(--vfs-mono); font-size: 0.74rem; }
.vfs-card {
  background: var(--vfs-card);
  border: 1px solid var(--vfs-border);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.vfs-card h3, .vfs-card h4 {
  margin: 0 0 8px 0;
  color: #0f172a;
}
.vfs-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
  margin: 8px 0 10px 0;
}
.vfs-kpi {
  background: #f8fafc;
  border: 1px solid var(--vfs-border);
  border-radius: 8px;
  padding: 8px 10px;
}
.vfs-kpi-label {
  font-size: 0.74rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.vfs-kpi-val {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
  margin-top: 2px;
}
.vfs-alert {
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #7f1d1d;
}
.vfs-alert-amber {
  border-color: #fde68a;
  background: #fffbeb;
  color: #78350f;
}
.vfs-empty {
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 18px;
  text-align: center;
  color: #64748b;
  background: #ffffff;
  font-size: 0.9rem;
}
.vfs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.86rem;
  margin-top: 6px;
}
.vfs-table th {
  text-align: left;
  background: #f1f5f9;
  color: #334155;
  padding: 7px 10px;
  border-bottom: 1px solid #cbd5e1;
  font-weight: 600;
}
.vfs-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
}
.vfs-beat {
  border: 1px solid var(--vfs-border);
  border-left: 4px solid var(--vfs-secondary);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #ffffff;
}
.vfs-quote {
  background: #f8fafc;
  border-left: 3px solid #94a3b8;
  padding: 6px 10px;
  margin: 6px 0;
  font-size: 0.88rem;
  color: #1e293b;
}
"""


def build_demo_theme() -> gr.themes.Soft:
    """Build light slate/indigo theme aligned with ui-ux-pro-max Data-Dense Dashboard tokens."""
    return gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="amber",
        neutral_hue="slate",
    )


def _esc(val: Any) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def _safe_url(raw_url: Any) -> str:
    txt = str(raw_url or "").strip()
    if txt.startswith(("https://", "http://")):
        return html.escape(txt, quote=True)
    return "#"


def render_placeholder_html(text: str) -> str:
    return f'<div class="vfs-empty">{_esc(text)}</div>'


def render_hero_banner_html(
    *,
    snapshot_id: str,
    total_videos: int,
    total_creators: int,
    poi_tagged_videos: int,
    transcribed_videos: int,
    gemini_configured: bool,
    multimodal_snapshot_id: str | None = None,
    multimodal_comments: int = 0,
    multimodal_voice_segments: int = 0,
) -> str:
    llm_pill = (
        '<span class="vfs-pill vfs-pill-amber">Gemini Free-Tier Key Active</span>'
        if gemini_configured
        else '<span class="vfs-pill vfs-pill-green">Offline CPU ($0 Verified)</span>'
    )
    mm_chips = ""
    if multimodal_snapshot_id:
        mm_chips = (
            f'<span class="vfs-pill vfs-pill-green vfs-pill-mono">Multimodal: {_esc(multimodal_snapshot_id)}</span>'
            f'<span class="vfs-pill vfs-pill-green">{int(multimodal_comments):,} real comments</span>'
            f'<span class="vfs-pill vfs-pill-green">{int(multimodal_voice_segments):,} audio_derived segs</span>'
        )
    return (
        '<div class="vfs-hero">'
        '<div class="vfs-hero-top">'
        '<div>'
        '<h1>🍜 ViralFoodRAG — TikTok F&amp;B Intelligence &amp; Trust Studio</h1>'
        '<p>Phân tích chuẩn ngách từ dữ liệu thực tế, truy xuất bằng chứng video có trích dẫn và kiểm toán đa phương thức M3–M5 (Prosody, Disclosure, Seeding, ABSA) không bịa nguồn.</p>'
        '</div>'
        f'<div>{llm_pill}</div>'
        '</div>'
        '<div class="vfs-chip-row">'
        f'<span class="vfs-pill vfs-pill-blue vfs-pill-mono">Snapshot: {_esc(snapshot_id)}</span>'
        f'<span class="vfs-pill">{total_videos:,} videos</span>'
        f'<span class="vfs-pill">{total_creators:,} creators</span>'
        f'<span class="vfs-pill">{transcribed_videos:,} transcripts</span>'
        f'<span class="vfs-pill">{poi_tagged_videos:,} GPS POIs</span>'
        f'{mm_chips}'
        '</div></div>'
    )


def render_error_alert_html(code: Any, message: Any, *, amber: bool = False) -> str:
    cls = "vfs-alert vfs-alert-amber" if amber else "vfs-alert"
    return (
        f'<div class="{cls}" role="alert">'
        f'<strong>⚠️ {_esc(code)}</strong>'
        f'<div style="margin-top:4px;font-size:0.9rem;">{_esc(message)}</div>'
        '</div>'
    )


def render_timings_html(timings: dict[str, Any], *, label: str = "Stage Timings") -> str:
    if not timings:
        return '<div class="vfs-pill" role="status">⏱ Chưa có số đo thời gian (sẵn sàng chạy)</div>'
    pills = "".join(
        f'<span class="vfs-pill vfs-pill-mono">{_esc(k)}: <strong>{_esc(v)} ms</strong></span>'
        for k, v in timings.items()
    )
    return (
        '<div class="vfs-chip-row" role="status" aria-live="polite">'
        f'<span class="vfs-pill vfs-pill-blue">⏱ {_esc(label)}</span>{pills}'
        '</div>'
    )


def render_benchmark_html(bench: dict[str, Any]) -> str:
    if not bench:
        return render_placeholder_html("Chưa có dữ liệu Niche Micro-Benchmark.")
    applied = bench.get("applied_filters") or {}
    filter_chips = (
        "".join(f'<span class="vfs-pill vfs-pill-blue vfs-pill-mono">{_esc(k)}={_esc(v)}</span>' for k, v in applied.items())
        or '<span class="vfs-pill">Toàn bộ kho dữ liệu</span>'
    )
    abstained = bool(bench.get("sparse_slice_abstained"))
    hours = bench.get("top_posting_hours") or []
    hours_chips = "".join(
        f'<span class="vfs-pill vfs-pill-mono">{int(h["hour"]):02d}:00 ({int(h["median_plays"]):,} views)</span>'
        for h in hours[:4]
    ) or f'<span class="vfs-pill vfs-pill-amber">{"Tạm dừng (< 5 video)" if abstained else "Chưa đủ mẫu"}</span>'
    tags_chips = "".join(
        f'<span class="vfs-pill">#{_esc(t)}</span>' for t in (bench.get("top_hashtags") or [])[:6]
    ) or '<span class="vfs-pill">Không có</span>'
    pois = " • ".join(_esc(p) for p in (bench.get("top_poi_venues") or [])[:5]) or (
        "Tạm dừng xếp hạng POI (< 5 video)" if abstained else "Không có POI định vị trong lát cắt"
    )
    miss = bench.get("missingness") or {}
    miss_txt = (
        f"thiếu transcript {miss.get('transcript_missing_pct', 0):.1f}% • "
        f"thiếu POI {miss.get('poi_missing_pct', 0):.1f}% • "
        f"thiếu thành phố {miss.get('city_missing_pct', 0):.1f}%"
        if miss
        else "Lát cắt rỗng"
    )
    return (
        '<div class="vfs-card">'
        '<h3>📊 Niche Micro-Benchmark (Kho Lịch Sử)</h3>'
        f'<div class="vfs-chip-row">{filter_chips}'
        f'<span class="vfs-pill vfs-pill-mono">{_esc(bench.get("cohort_window_start", "N/A"))} → {_esc(bench.get("cohort_window_end", "N/A"))}</span>'
        f'<span class="vfs-pill">Mốc: {_esc(bench.get("observation_snapshot", "N/A"))}</span></div>'
        '<div class="vfs-kpi-grid">'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Quy mô mẫu (n)</div><div class="vfs-kpi-val">{int(bench.get("matched_videos", 0)):,}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Median / P75 Views</div><div class="vfs-kpi-val">{int(bench.get("median_plays", 0)):,} / {int(bench.get("p75_plays", 0)):,}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Tương tác trung vị</div><div class="vfs-kpi-val">{float(bench.get("median_engagement_rate", 0.0)) * 100:.2f}%</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Thời lượng IQR</div><div class="vfs-kpi-val">{float(bench.get("duration_q25_sec", 0)):.0f}–{float(bench.get("duration_median_sec", 0)):.0f}–{float(bench.get("duration_q75_sec", 0)):.0f}s</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Tốc độ nói ước tính</div><div class="vfs-kpi-val">{float(bench.get("median_word_per_second", 0)):.2f} từ/s</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Có Transcript / POI</div><div class="vfs-kpi-val">{int(bench.get("transcribed_videos", 0)):,} / {int(bench.get("poi_tagged_videos", 0)):,}</div></div>'
        '</div>'
        f'<div style="font-size:0.84rem;color:#475569;margin:4px 0;"><strong>Missingness:</strong> {_esc(miss_txt)}</div>'
        f'<div class="vfs-chip-row"><span style="font-size:0.84rem;font-weight:600;color:#334155;">Giờ đăng nổi bật:</span>{hours_chips}</div>'
        f'<div class="vfs-chip-row"><span style="font-size:0.84rem;font-weight:600;color:#334155;">Hashtags:</span>{tags_chips}</div>'
        f'<div style="font-size:0.84rem;color:#475569;margin-top:6px;"><strong>POI nền tảng:</strong> {pois}</div>'
        '<div style="font-size:0.78rem;color:#64748b;margin-top:6px;"><em>Lưu ý: Thống kê mô tả trên lát cắt lịch sử; không chứng minh quan hệ nhân quả tăng viral.</em></div>'
        '</div>'
    )


def render_evidence_cards_html(
    items: list[dict[str, Any]],
    *,
    mode: str = "bm25",
    total_cands: int = 0,
    insufficient_evidence: bool = False,
    abstain_reason: str | None = None,
) -> str:
    if insufficient_evidence:
        return render_error_alert_html(
            f"Từ chối / Không đủ bằng chứng ({abstain_reason or 'insufficient_evidence'})",
            "Kho dữ liệu không có bằng chứng phù hợp hoặc yêu cầu bị giới hạn theo guardrail — hệ thống không bịa kết quả.",
            amber=True,
        )
    if not items:
        return render_placeholder_html("Không tìm thấy video bằng chứng phù hợp.")

    cards_html: list[str] = [
        f'<div class="vfs-chip-row"><span class="vfs-pill vfs-pill-blue">🎬 Bằng chứng truy xuất ({len(items)} kết quả)</span>'
        f'<span class="vfs-pill vfs-pill-mono">mode={_esc(mode)}</span>'
        f'<span class="vfs-pill vfs-pill-mono">{int(total_cands)} ứng viên</span></div>'
    ]
    for card in items:
        cit = card.get("citation") or {}
        vid = str(cit.get("video_id") or "")
        handle = str(cit.get("author_handle") or "unknown")
        url = _safe_url(cit.get("tiktok_url"))
        plays = int(cit.get("play_count") or 0)
        v_mult = float(cit.get("viral_multiplier") or 0.0)
        loc_parts = [str(p) for p in (card.get("poi_name"), card.get("district_norm"), card.get("city_norm")) if p]
        loc_str = " — ".join(loc_parts) if loc_parts else "Việt Nam (chưa gắn POI)"
        beats = card.get("body_beats") or []
        beat_preview = "; ".join(str(b) for b in beats[:2]) if beats else str(card.get("transcript_excerpt") or "")[:200]
        v_cls = "vfs-pill-green" if v_mult >= 2.0 else "vfs-pill-blue"

        cards_html.append(
            '<div class="vfs-card">'
            '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;">'
            f'<div><span class="vfs-pill vfs-pill-blue">#{_esc(card.get("rank"))}</span> '
            f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="font-weight:700;color:#1e40af;text-decoration:none;">@{_esc(handle)}</a> '
            f'<span class="vfs-pill vfs-pill-mono">{_esc(vid)}</span></div>'
            f'<div><span class="vfs-pill {v_cls}">{v_mult:.1f}x trung vị</span> '
            f'<span class="vfs-pill">{plays:,} views</span></div>'
            '</div>'
            '<div class="vfs-chip-row">'
            f'<span class="vfs-pill">{_esc(card.get("video_format"))}</span>'
            f'<span class="vfs-pill">{_esc(card.get("food_category"))}</span>'
            f'<span class="vfs-pill">{_esc(card.get("price_tier"))}</span>'
            f'<span class="vfs-pill vfs-pill-mono">{_esc(card.get("duration_sec"))}s</span>'
            f'<span class="vfs-pill">📍 {_esc(loc_str)}</span>'
            '</div>'
            f'<div class="vfs-quote"><strong>Hook gốc:</strong> {_esc(card.get("hook_text", ""))}</div>'
            f'<div style="font-size:0.86rem;color:#334155;"><strong>Ý chính:</strong> {_esc(beat_preview)}</div>'
            '</div>'
        )
    return "".join(cards_html)


def render_script_html(resp: dict[str, Any]) -> str:
    guard = resp.get("guardrail") or {}
    passed = bool(guard.get("passed"))
    badge_cls = "vfs-pill-green" if passed else "vfs-pill-amber"
    badge_txt = "ĐẠT KIỂM TRA CẤU TRÚC" if passed else "CẦN KIỂM TRA / THIẾU NGUỒN"

    hooks = resp.get("hook_options") or []
    hooks_html = "".join(
        f'<div class="vfs-quote"><strong>Hook {i}:</strong> {_esc(h)}</div>'
        for i, h in enumerate(hooks, start=1)
    )

    beats_html: list[str] = []
    for b in resp.get("beats") or []:
        cites = "".join(f'<span class="vfs-pill vfs-pill-blue vfs-pill-mono">{_esc(c)}</span>' for c in (b.get("cited_video_ids") or []))
        if not cites:
            cites = '<span class="vfs-pill vfs-pill-amber">Không có mã nguồn khớp</span>'
        beats_html.append(
            '<div class="vfs-beat">'
            '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px;">'
            f'<strong>{_esc(b.get("section_title"))}</strong>'
            f'<div><span class="vfs-pill vfs-pill-mono">{_esc(b.get("time_range"))}</span> '
            f'<span class="vfs-pill">{_esc(b.get("word_count"))} từ</span></div>'
            '</div>'
            f'<div style="font-size:0.82rem;color:#475569;margin-bottom:4px;"><strong>Góc máy:</strong> {_esc(b.get("visual_angle"))}</div>'
            f'<div style="font-size:0.92rem;color:#0f172a;line-height:1.45;">{_esc(b.get("dialogue"))}</div>'
            f'<div class="vfs-chip-row"><span style="font-size:0.78rem;color:#64748b;">Tham chiếu:</span>{cites}</div>'
            '</div>'
        )

    sa = resp.get("shooting_advice") or {}
    advice_items = (
        [f"<strong>Góc quay:</strong> {_esc(x)}" for x in (sa.get("camera_angles") or [])]
        + [f"<strong>Ánh sáng &amp; âm thanh:</strong> {_esc(x)}" for x in (sa.get("lighting_and_audio") or [])]
        + [f"<strong>Nhịp dựng:</strong> {_esc(x)}" for x in (sa.get("pacing_and_editing") or [])]
    )
    advice_html = "".join(f'<li style="margin-bottom:4px;">{item}</li>' for item in advice_items)

    warns = guard.get("warnings") or []
    warn_html = "".join(f'<li>⚠️ {_esc(w)}</li>' for w in warns)
    tags = " ".join(f"#{_esc(t)}" for t in (resp.get("recommended_hashtags") or []))

    return (
        '<div class="vfs-card">'
        '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;">'
        f'<h3>📜 Bản Nháp Kịch Bản ({_esc(resp.get("generation_mode"))})</h3>'
        f'<span class="vfs-pill {badge_cls}">{badge_txt}</span>'
        '</div>'
        '<div style="font-size:0.82rem;color:#64748b;margin-bottom:8px;">'
        '<em>Bản nháp tham khảo từ nguồn lịch sử; thời lượng tính theo tốc độ từ (wps_estimated), cần kiểm chứng khi quay thực tế.</em></div>'
        '<div class="vfs-kpi-grid">'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Tổng số từ</div><div class="vfs-kpi-val">{_esc(guard.get("total_words"))}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Thời lượng (Mục tiêu)</div><div class="vfs-kpi-val">{_esc(guard.get("estimated_duration_sec"))}s ({_esc(guard.get("target_duration_sec"))}s)</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Chênh lệch</div><div class="vfs-kpi-val">{float(guard.get("duration_delta_sec") or 0.0):+.1f}s</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Trích dẫn hợp lệ</div><div class="vfs-kpi-val">{float(guard.get("valid_citations_ratio") or 0.0) * 100:.0f}%</div></div>'
        '</div>'
        f'<div style="font-size:0.86rem;margin-bottom:8px;"><strong>Bối cảnh:</strong> {_esc(resp.get("setting"))} • <strong>Persona:</strong> {_esc(resp.get("persona_tone"))}</div>'
        '<h4>3 Phương án Hook mở đầu (0–4s)</h4>'
        f'{hooks_html}'
        '<h4 style="margin-top:10px;">Phân cảnh &amp; Lời thoại</h4>'
        f'{"".join(beats_html)}'
        f'<div class="vfs-quote"><strong>Caption gợi ý:</strong> {_esc(resp.get("caption_draft"))}<br><span style="color:#1e40af;font-family:var(--vfs-mono);font-size:0.8rem;">{tags}</span></div>'
        '<h4>Hướng dẫn quay dựng</h4>'
        f'<ul style="margin:4px 0 8px 18px;font-size:0.85rem;">{advice_html}</ul>'
        + (f'<div class="vfs-alert vfs-alert-amber" style="margin-bottom:0;"><ul style="margin:0 0 0 16px;font-size:0.84rem;">{warn_html}</ul></div>' if warn_html else "")
        + '</div>'
    )


def render_trust_audit_html(data: dict[str, Any], *, hide_seeding: bool = False) -> str:
    comp = data.get("comparison") or {}
    koc_sums = comp.get("koc_aspect_summaries") or {}
    v_sums = comp.get("viewer_aspect_summaries") or {}
    discs = comp.get("aspect_discrepancies") or {}
    sens = data.get("filter_sensitivity") or {}
    spans = comp.get("source_spans") or []
    comments = data.get("comments") or []
    filter_policy = str(data.get("comment_filter_policy") or "diagnostic_only_unvalidated")
    flag_status = str(comp.get("disclosure_flag_status") or "unlabeled_unknown")
    lex_score = float(comp.get("lexical_promo_score") or 0.0)
    sup_disc = comp.get("supported_sentiment_discrepancy")
    abs_reason = comp.get("discrepancy_abstention_reason")

    def _pol_pill(pol: str, pres: str, mean: Any, cnt: int) -> str:
        if pres != "observed" or mean is None:
            return f'<span class="vfs-pill">absent_unknown (n={cnt})</span>'
        cls = {"positive": "vfs-pill-green", "negative": "vfs-pill-red", "neutral": "vfs-pill-blue"}.get(pol, "vfs-pill")
        return f'<span class="vfs-pill {cls}">observed • {_esc(pol)} ({float(mean):+.2f}, n={cnt})</span>'

    rows_html: list[str] = []
    for key, label in (
        ("taste", "Hương vị (Taste)"),
        ("price", "Giá cả (Price)"),
        ("hygiene", "Vệ sinh (Hygiene)"),
        ("service", "Phục vụ (Service)"),
    ):
        ks = koc_sums.get(key) or {}
        vs = v_sums.get(key) or {}
        dd = discs.get(key) or {}
        k_badge = _pol_pill(str(ks.get("polarity_label") or ""), str(ks.get("presence_status") or "absent_unknown"), ks.get("mean_score"), int(ks.get("mention_unit_count") or 0))
        v_badge = _pol_pill(str(vs.get("polarity_label") or ""), str(vs.get("presence_status") or "absent_unknown"), vs.get("mean_score"), int(vs.get("mention_unit_count") or 0))
        c_status = str(dd.get("comparison_status") or "abstained_creator_absent")
        s_val = dd.get("sentiment_discrepancy")
        sup_n = int(dd["viewer_support_count"] if dd.get("viewer_support_count") is not None else (vs.get("mention_unit_count") or 0))
        min_req = int(dd.get("min_viewer_support_required") or 3)
        if c_status == "compared_supported_overlap" and s_val is not None:
            d_badge = f'<span class="vfs-pill vfs-pill-blue">{float(s_val):+.2f} ({_esc(c_status)}, n={sup_n}>={min_req})</span>'
        else:
            d_badge = f'<span class="vfs-pill vfs-pill-amber">tạm dừng ({_esc(c_status)}, n={sup_n}/{min_req})</span>'
        rows_html.append(f"<tr><td><strong>{_esc(label)}</strong></td><td>{k_badge}</td><td>{v_badge}</td><td>{d_badge}</td></tr>")

    sens_block = ""
    if sens:
        b_mean = sens.get("before_filter_viewer_mean")
        b_txt = f"{float(b_mean):+.4f}" if b_mean is not None else "N/A"
        if sens.get("after_filter_abstained") or sens.get("after_filter_viewer_mean") is None:
            a_txt = "tạm dừng (0 bình luận sạch)"
        else:
            a_txt = f"{float(sens.get('after_filter_viewer_mean') or 0.0):+.4f} (chênh {float(sens.get('mean_score_shift') or 0.0):+.4f})"
        sens_block = f'<div style="font-size:0.84rem;color:#334155;margin-top:6px;"><strong>Độ nhạy bộ lọc:</strong> Trước lọc <code>{_esc(b_txt)}</code> → Sau lọc <code>{_esc(a_txt)}</code></div>'

    span_items = "".join(
        f'<div class="vfs-quote"><span class="vfs-pill vfs-pill-mono">[{_esc(sp.get("unit_id"))} @ {int(sp.get("start_char") or 0)}:{int(sp.get("end_char") or 0)}]</span> '
        f'<span class="vfs-pill">{_esc(sp.get("aspect"))} • {_esc(sp.get("polarity_label"))} ({float(sp.get("polarity_score") or 0.0):+.2f})</span> '
        f'"{_esc(" ".join(str(sp.get("span_text") or "").splitlines()))}"</div>'
        for sp in spans
    ) or '<div style="font-size:0.84rem;color:#64748b;">Không có span khía cạnh được phát hiện.</div>'

    shown = [c for c in comments if (not hide_seeding or not c.get("is_seeding"))]
    cmt_items = "".join(
        '<div style="padding:6px 8px;border-bottom:1px solid #e2e8f0;font-size:0.86rem;">'
        + (
            f'<span class="vfs-pill vfs-pill-red">⚑ {_esc(c.get("observable_label") or c.get("seeding_reason"))}</span> '
            if c.get("is_seeding")
            else '<span class="vfs-pill">ℹ️ no_indicator_observed</span> '
        )
        + f'<strong>@{_esc(c.get("author_handle") or "user")}</strong>: {_esc(" ".join(str(c.get("text") or "").splitlines()))}'
        '</div>'
        for c in shown
    ) or '<div style="font-size:0.84rem;color:#64748b;">Không có bình luận hiển thị theo bộ lọc hiện tại.</div>'

    absa_model = str(data.get("absa_model_used") or "lexicon_v1")
    disc_banner = (
        f'<span class="vfs-pill vfs-pill-green vfs-pill-mono">ABSA Engine: {_esc(absa_model)}</span> '
        + (
            f'<span class="vfs-pill vfs-pill-blue">Sentiment Discrepancy: {float(sup_disc):+.2f}</span>'
            if sup_disc is not None
            else f'<span class="vfs-pill vfs-pill-amber">Discrepancy tạm dừng ({_esc(abs_reason or "insufficient_overlapping_aspect_support_min_3_comments")})</span>'
        )
    )

    return (
        '<div class="vfs-card">'
        '<h3>🛡️ Chẩn Đoán Bình Luận (M5.1) &amp; ABSA 4 Khía Cạnh (M5.2)</h3>'
        '<div class="vfs-alert vfs-alert-amber" style="font-size:0.84rem;">'
        'Chế độ chẩn đoán quan sát được: chỉ báo trùng lặp/liên hệ/nhiễu không khẳng định bot hay trả tiền thuê seeding; '
        'độ lệch ABSA chỉ đo chênh lệch lời thoại vs bình luận trên khía cạnh đủ &ge; 3 bình luận sạch.'
        '</div>'
        '<div class="vfs-kpi-grid">'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Observed Flag</div><div class="vfs-kpi-val" style="font-size:0.9rem;">{_esc(flag_status)}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Lexical Promo Score</div><div class="vfs-kpi-val">{lex_score:.2f}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Clean / Flagged Cmt</div><div class="vfs-kpi-val">{int(comp.get("clean_comment_count", 0))} / {int(comp.get("seeding_comment_count", 0))}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Chính sách lọc M5.1</div><div class="vfs-kpi-val" style="font-size:0.82rem;">{_esc(filter_policy)}</div></div>'
        '</div>'
        f'<div class="vfs-chip-row">{disc_banner}</div>'
        f'{sens_block}'
        '<table class="vfs-table"><thead><tr><th>Khía cạnh</th><th>Lời thoại KOC</th><th>Bình luận sạch</th><th>Độ lệch quan sát</th></tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table>'
        '<h4 style="margin-top:12px;">Bằng chứng trích dẫn gốc (NFC Source Spans)</h4>'
        f'{span_items}'
        f'<h4 style="margin-top:12px;">Bình luận ({"Đã tạm ẩn mục có chỉ dấu" if hide_seeding else "Hiển thị đầy đủ"})</h4>'
        f'<div style="border:1px solid #e2e8f0;border-radius:8px;">{cmt_items}</div>'
        '</div>'
    )


def render_corpus_video_header_html(video: dict[str, Any]) -> str:
    vid = _esc(video.get("video_id", ""))
    handle = _esc(video.get("author_handle", "creator"))
    url = _safe_url(video.get("tiktok_url"))
    snap = _esc(video.get("snapshot_id", "multimodal_gold"))
    plays = int(video.get("play_count") or 0)
    dur = int(video.get("duration_sec") or 0)
    cat = _esc(video.get("food_category") or "F&B")
    city = _esc(video.get("city_norm") or "Việt Nam")
    cap = _esc(video.get("caption") or "(Không có caption)")
    tags = " ".join(f"#{_esc(t)}" for t in (video.get("hashtags") or []))
    return (
        '<div class="vfs-card">'
        '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;">'
        f'<h3>🎬 Video Thực Tế Từ Kho Gold: <a href="{url}" target="_blank" rel="noopener noreferrer">@{handle}</a> '
        f'<span class="vfs-pill vfs-pill-mono">{vid}</span></h3>'
        f'<span class="vfs-pill vfs-pill-blue vfs-pill-mono">{snap}</span>'
        '</div>'
        '<div class="vfs-chip-row">'
        f'<span class="vfs-pill">{plays:,} views</span>'
        f'<span class="vfs-pill">{dur}s</span>'
        f'<span class="vfs-pill">{cat}</span>'
        f'<span class="vfs-pill">📍 {city}</span>'
        f'<span class="vfs-pill">is_ad={_esc(bool(video.get("is_ad", False)))}</span>'
        f'<span class="vfs-pill">is_ec_video={_esc(bool(video.get("is_ec_video", False)))}</span>'
        '</div>'
        f'<div class="vfs-quote" style="margin-top:8px;"><strong>Caption gốc:</strong> {cap}'
        + (f'<br><span style="color:#1e40af;font-family:var(--vfs-mono);font-size:0.78rem;">{tags}</span>' if tags else "")
        + '</div></div>'
    )


def render_disclosure_promo_html(disc: dict[str, Any]) -> str:
    flag_status = str(disc.get("disclosure_flag_status") or "unlabeled_unknown")
    flag_cls = "vfs-pill-amber" if flag_status != "unlabeled_unknown" else "vfs-pill"
    lex_score = float(disc.get("lexical_promo_score") or 0.0)
    gt_status = str(disc.get("sponsorship_ground_truth_status") or "undisclosed_sponsorship_deferred")
    note = str(disc.get("disclosure_target_note") or "")
    cats = disc.get("matched_categories") or []
    inds = disc.get("matched_indicators") or []

    cat_pills = "".join(f'<span class="vfs-pill vfs-pill-blue">{_esc(c)}</span>' for c in cats) or (
        '<span class="vfs-pill">Không có nhóm từ khóa khuyến mãi</span>'
    )
    ind_pills = "".join(f'<span class="vfs-pill vfs-pill-mono">{_esc(i)}</span>' for i in inds) or (
        '<span class="vfs-pill">0 từ khóa khuyến mãi khớp</span>'
    )
    return (
        '<div class="vfs-card">'
        '<h3>🏷️ Tách Bạch Cờ Công Khai &amp; Từ Ngữ Khuyến Mãi (M4.2)</h3>'
        f'<div class="vfs-alert vfs-alert-amber" style="font-size:0.83rem;">{_esc(note)}</div>'
        '<div class="vfs-kpi-grid">'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Observed Platform Flag</div><div class="vfs-kpi-val" style="font-size:0.88rem;"><span class="vfs-pill {flag_cls}">{_esc(flag_status)}</span></div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Lexical Promo Density</div><div class="vfs-kpi-val">{lex_score:.2f}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Matched Cue Count</div><div class="vfs-kpi-val">{len(inds)}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Hidden Sponsorship</div><div class="vfs-kpi-val" style="font-size:0.78rem;"><span class="vfs-pill vfs-pill-amber">{_esc(gt_status)}</span></div></div>'
        '</div>'
        f'<div style="font-size:0.84rem;margin-bottom:6px;"><strong>Nhóm chỉ dấu từ vựng:</strong> {cat_pills}</div>'
        f'<div style="font-size:0.84rem;"><strong>Từ khóa quan sát được:</strong> {ind_pills}</div>'
        '</div>'
    )


def render_prosody_segments_html(prosody: dict[str, Any]) -> str:
    seg_cnt = int(prosody.get("segment_count") or 0)
    aud_cnt = int(prosody.get("audio_derived_segments") or 0)
    wps_cnt = int(prosody.get("wps_estimated_segments") or 0)
    med_wps = prosody.get("median_words_per_sec")
    mean_pitch = prosody.get("mean_pitch_std_hz")
    mean_energy = prosody.get("mean_energy_cv")
    note = str(prosody.get("descriptive_note") or "")
    inv = prosody.get("temporal_invariants") or {}
    inv_ok = bool(inv.get("meets_100pct_invariant_gate", True))
    inv_cls = "vfs-pill-green" if inv_ok else "vfs-pill-red"
    inv_txt = (
        f"Temporal Invariants PASS ({int(inv.get('valid_segments') or seg_cnt)}/{int(inv.get('total_segments') or seg_cnt)})"
        if seg_cnt > 0
        else "Chưa có phân đoạn Whisper/ASR cho video này"
    )

    wps_str = f"{float(med_wps):.2f} từ/s" if med_wps is not None else "N/A"
    pitch_str = f"{float(mean_pitch):.2f} Hz" if mean_pitch is not None else "N/A"
    energy_str = f"{float(mean_energy):.4f}" if mean_energy is not None else "N/A"

    segs = prosody.get("voice_segments") or []
    seg_rows: list[str] = []
    for s in segs[:40]:
        src = str(s.get("timestamp_source") or "audio_derived")
        src_cls = "vfs-pill-green" if src == "audio_derived" else "vfs-pill-amber"
        st = float(s.get("start_sec") or 0.0)
        en = float(s.get("end_sec") or 0.0)
        p_val = f"{float(s['pitch_std']):.1f} Hz" if s.get("pitch_std") is not None else "—"
        e_val = f"{float(s['energy_cv']):.3f}" if s.get("energy_cv") is not None else "—"
        seg_rows.append(
            "<tr>"
            f'<td style="white-space:nowrap;font-family:var(--vfs-mono);font-size:0.78rem;">{st:05.2f}s → {en:05.2f}s</td>'
            f'<td><span class="vfs-pill {src_cls} vfs-pill-mono">{_esc(src)}</span></td>'
            f'<td style="white-space:nowrap;">{float(s.get("words_per_sec") or 0.0):.2f} w/s • {p_val} • CV {e_val}</td>'
            f'<td>{_esc(s.get("text") or "")}</td>'
            "</tr>"
        )
    table_html = (
        '<div style="max-height:260px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:8px;margin-top:8px;">'
        '<table class="vfs-table" style="margin-top:0;">'
        '<thead><tr><th>Mốc giây</th><th>Nguồn mốc</th><th>Prosody mô tả</th><th>Lời thoại ASR</th></tr></thead>'
        f'<tbody>{"".join(seg_rows)}</tbody></table></div>'
        if seg_rows
        else '<div style="font-size:0.84rem;color:#64748b;margin-top:6px;">Video này chỉ có metadata + bình luận thực tế (chưa chạy bóc băng .mp3 M4.1).</div>'
    )

    return (
        '<div class="vfs-card">'
        '<div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px;">'
        '<h3>🎙️ Mốc Thời Gian Lời Thoại &amp; Ngữ Điệu Mô Tả (M4.1)</h3>'
        f'<span class="vfs-pill {inv_cls}">{_esc(inv_txt)}</span>'
        '</div>'
        f'<div style="font-size:0.82rem;color:#475569;margin-bottom:8px;"><em>{_esc(note)}</em></div>'
        '<div class="vfs-kpi-grid">'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Utterances (audio_derived / wps)</div><div class="vfs-kpi-val">{aud_cnt} / {wps_cnt}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Median Speaking Rate</div><div class="vfs-kpi-val">{_esc(wps_str)}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Mean F0 Pitch Std</div><div class="vfs-kpi-val">{_esc(pitch_str)}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Mean Energy CV</div><div class="vfs-kpi-val">{_esc(energy_str)}</div></div>'
        '</div>'
        f'{table_html}'
        '</div>'
    )


def render_milestone_evaluations_html(ms_data: dict[str, Any]) -> str:
    milestones = (ms_data or {}).get("milestones") or {}
    if not milestones:
        return render_placeholder_html("Chưa có dữ liệu tổng hợp thực nghiệm M2–M6.")
    rows: list[str] = []
    for mid, item in milestones.items():
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "UNKNOWN")
        s_cls = (
            "vfs-pill-green"
            if status == "COMPLETE"
            else ("vfs-pill-blue" if status == "IN_PROGRESS" else "vfs-pill-amber")
        )
        title = _esc(item.get("title") or mid)
        headline = _esc(item.get("headline") or "Chưa có biên bản JSON trên đĩa")
        rows.append(
            "<tr>"
            f'<td><span class="vfs-pill vfs-pill-mono"><strong>{_esc(mid)}</strong></span></td>'
            f'<td><span class="vfs-pill {s_cls}">{_esc(status)}</span></td>'
            f'<td><strong>{title}</strong></td>'
            f'<td style="font-family:var(--vfs-mono);font-size:0.8rem;">{headline}</td>'
            "</tr>"
        )
    return (
        '<div class="vfs-card">'
        '<h3>📊 Bảng Điểm Thực Nghiệm Xác Minh Toàn Dự Án (M2.2 – M6.2)</h3>'
        '<table class="vfs-table">'
        '<thead><tr><th>Task</th><th>Trạng thái</th><th>Hạng mục AI</th><th>Số liệu kiểm chứng thực tế trên kho lưu trữ</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '</div>'
    )


def render_system_status_html(ready_data: dict[str, Any], eval_data: dict[str, Any]) -> str:
    mm_snap = ready_data.get("multimodal_snapshot_id") or "N/A"
    mm_cmts = int(ready_data.get("multimodal_total_comments") or 0)
    mm_segs = int(ready_data.get("multimodal_voice_segments") or 0)
    return (
        '<div class="vfs-card">'
        '<h3>⚙️ Tình Trạng Hệ Thống &amp; Kho Dữ Liệu Đa Phương Thức</h3>'
        '<div class="vfs-kpi-grid">'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Status</div><div class="vfs-kpi-val">{_esc(ready_data.get("status", "unknown"))}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Gold Snapshot</div><div class="vfs-kpi-val" style="font-size:0.86rem;">{_esc(ready_data.get("corpus_snapshot_id", "N/A"))}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">BM25 Indexed Videos</div><div class="vfs-kpi-val">{int(ready_data.get("indexed_bm25_videos", 0)):,}</div></div>'
        f'<div class="vfs-kpi"><div class="vfs-kpi-label">Eval Summary ID</div><div class="vfs-kpi-val" style="font-size:0.86rem;">{_esc(eval_data.get("benchmark_id", "N/A"))}</div></div>'
        '</div>'
        '<div class="vfs-chip-row">'
        f'<span class="vfs-pill">Total Videos: {int(ready_data.get("total_videos", 0)):,}</span>'
        f'<span class="vfs-pill">Creators: {int(ready_data.get("total_creators", 0)):,}</span>'
        f'<span class="vfs-pill vfs-pill-green vfs-pill-mono">Multimodal: {_esc(mm_snap)}</span>'
        f'<span class="vfs-pill vfs-pill-green">Real Comments: {mm_cmts:,}</span>'
        f'<span class="vfs-pill vfs-pill-green">Voice Segments: {mm_segs:,}</span>'
        f'<span class="vfs-pill">Qdrant Ready: {_esc(ready_data.get("qdrant_dense_ready", False))}</span>'
        f'<span class="vfs-pill">Gemini Key Configured: {_esc(ready_data.get("gemini_key_configured", False))}</span>'
        '</div></div>'
    )
