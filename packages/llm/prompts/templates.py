from __future__ import annotations

import json
import re

from packages.common.exceptions import UnsupportedDomainError
from packages.data_contracts.analytics import NicheBenchmarkSummary
from packages.data_contracts.retrieval import EvidenceCard

OUT_OF_DOMAIN_KEYWORDS: tuple[str, ...] = (
    "chứng khoán",
    "tiền ảo",
    "bitcoin",
    "forex",
    "bất động sản",
    "sửa xe máy",
    "lập trình kubernetes",
    "cá độ",
    "tín dụng đen",
)

FNB_SIGNAL_KEYWORDS: tuple[str, ...] = (
    "ăn",
    "uống",
    "món",
    "quán",
    "nhà hàng",
    "tiệm",
    "nấu",
    "bếp",
    "công thức",
    "review",
    "mukbang",
    "bún",
    "phở",
    "cơm",
    "mì",
    "bánh",
    "lẩu",
    "nướng",
    "buffet",
    "ốc",
    "gà",
    "bò",
    "heo",
    "cá",
    "tôm",
    "hải sản",
    "trà",
    "cà phê",
    "cafe",
    "matcha",
    "chè",
    "kem",
    "chay",
    "salad",
    "healthy",
    "thực đơn",
    "bữa",
    "đặc sản",
    "vỉa hè",
)


def is_blatant_out_of_domain_query(text: str) -> bool:
    """Return True when a query explicitly names non-F&B topics with zero culinary signals."""
    lower = (text or "").lower().strip()
    if not lower:
        return False
    has_fnb = any(kw in lower for kw in FNB_SIGNAL_KEYWORDS)
    return bool(any(bad in lower for bad in OUT_OF_DOMAIN_KEYWORDS) and not has_fnb)


def check_fnb_domain_relevance(brief: str) -> None:
    """Reject blatantly non-F&B prompts before spending retrieval/LLM budget."""
    lower = brief.lower().strip()
    has_fnb = any(kw in lower for kw in FNB_SIGNAL_KEYWORDS)
    if is_blatant_out_of_domain_query(brief):
        raise UnsupportedDomainError(
            "Yêu cầu nằm ngoài lĩnh vực Ẩm thực & F&B TikTok Việt Nam. Vui lòng nhập chủ đề món ăn, quán ăn, đồ uống hoặc nấu ăn."
        )
    if not has_fnb and len(lower.split()) >= 4:
        raise UnsupportedDomainError(
            "Chưa nhận diện được ngữ cảnh ẩm thực/đồ uống trong đề bài. Hãy nêu rõ món ăn, loại quán, nguyên liệu hoặc phong cách ẩm thực."
        )


_EPISTEMIC_CLAIM_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "epistemic_refusal_undisclosed_sponsorship",
        re.compile(
            r"(?i)(?:chứng\s*minh|kết\s*luận|khẳng\s*định|xác\s*minh|chắc\s*chắn).*(?:pr\s*ngầm|quảng\s*cáo\s*ngầm|nhận\s*tiền\s*pr|tài\s*trợ\s*ẩn)"
        ),
        "Không thể khẳng định hoặc suy diễn PR ngầm/nhận tiền tài trợ từ cờ is_ad quan sát được (M4.2 guardrail).",
    ),
    (
        "epistemic_refusal_bot_seeding",
        re.compile(
            r"(?i)(?:kết\s*luận|chứng\s*minh|xác\s*định|gán\s*nhãn).*(?:tài\s*khoản\s*bot|trả\s*tiền.*seeding|thuê\s*seeding)"
        ),
        "Chỉ báo trùng lặp/liên hệ trên bình luận là dấu hiệu quan sát được, không chứng minh bot hay seeding trả tiền (M5.1 guardrail).",
    ),
    (
        "epistemic_refusal_hygiene_certification",
        re.compile(
            r"(?i)(?:xác\s*nhận|chứng\s*nhận|kết\s*luận|chứng\s*minh).*(?:an\s*toàn\s*vệ\s*sinh\s*thực\s*phẩm|vệ\s*sinh\s*thực\s*phẩm\s*thực\s*tế)"
        ),
        "Cảm xúc bình luận khách hàng là chênh lệch cảm nhận (sentiment discrepancy), không phải chứng nhận vệ sinh an toàn thực phẩm thực tế (M5.2 guardrail).",
    ),
    (
        "epistemic_refusal_missing_audio_timestamps",
        re.compile(
            r"(?i)(?:mili\s*giây|millisecond|chính\s*xác\s*từng\s*giây).*(?:không\s*có\s*audio|phụ\s*đề\s*nội\s*suy|wps_estimated)"
        ),
        "Video không có audio chỉ có mốc ước lượng theo tốc độ từ (wps_estimated), không trích xuất được timestamp chính xác theo audio (M4.1/M6.2 guardrail).",
    ),
)


def detect_unsupported_epistemic_claim(text: str) -> tuple[str, str] | None:
    """Return (code, refusal_message) when a query asks for claims forbidden by project guardrails."""
    cleaned = text.strip()
    if not cleaned:
        return None
    for code, pattern, msg in _EPISTEMIC_CLAIM_RULES:
        if pattern.search(cleaned):
            return code, msg
    return None


def build_grounded_script_prompt(
    brief: str,
    target_duration_sec: int,
    benchmark: NicheBenchmarkSummary,
    evidence_cards: list[EvidenceCard],
) -> str:
    target_words = max(40, int(round(target_duration_sec * max(benchmark.median_word_per_second, 2.2))))
    evidence_payload = [
        {
            "video_id": card.citation.video_id,
            "author": f"@{card.citation.author_handle}",
            "viral_multiplier": card.citation.viral_multiplier,
            "play_count": card.citation.play_count,
            "video_format": card.video_format,
            "hook_text": card.hook_text,
            "body_beats": card.body_beats[:3],
            "cta_text": card.cta_text,
        }
        for card in evidence_cards
    ]

    schema_example = {
        "hook_options": ["Hook 1 gây tò mò...", "Hook 2 đánh vào giá/trải nghiệm...", "Hook 3 trực diện món ăn..."],
        "caption_draft": "Caption ngắn gọn thu hút kèm câu hỏi mở...",
        "recommended_hashtags": ["ancungtiktok", "reviewanngon"],
        "setting": "Mô tả bối cảnh quay cụ thể",
        "persona_tone": "Tự nhiên, chân thực, giàu chi tiết vị giác",
        "beats": [
            {
                "section_title": "1. Hook mở đầu",
                "visual_angle": "Cận cảnh món ăn bốc khói / góc POV...",
                "dialogue": "Lời thoại tự nhiên...",
                "cited_video_ids": [evidence_cards[0].citation.video_id if evidence_cards else ""],
            }
        ],
        "shooting_advice": {
            "camera_angles": ["Cận cảnh 45 độ khi gắp món..."],
            "lighting_and_audio": ["Thu âm ASMR tiếng giòn / xèo xèo..."],
            "pacing_and_editing": ["Chuyển cảnh nhanh 1.5-2s ở 5 giây đầu..."],
        },
    }

    return (
        "Bạn là Giám đốc Sáng tạo Nội dung TikTok Ẩm thực Việt Nam dựa trên bằng chứng thực nghiệm.\n"
        f"ĐỀ BÀI CỦA CREATOR: {brief}\n\n"
        "THÔNG SỐ CHUẨN THỰC NGHIỆM CỦA NGÁCH (NICHE BENCHMARK):\n"
        f"- Thời lượng mục tiêu: {target_duration_sec} giây (IQR ngách: {benchmark.duration_q25_sec}s - {benchmark.duration_q75_sec}s)\n"
        f"- Tốc độ nói trung vị ngách: {benchmark.median_word_per_second} từ/giây -> Tổng lời thoại toàn kịch bản khoảng {target_words} từ (±20%).\n"
        f"- Hashtag hiệu quả nhất ngách: {', '.join(benchmark.top_hashtags[:6])}\n\n"
        "BẰNG CHỨNG VIDEO THÀNH CÔNG TRONG KHO DỮ LIỆU (BẮT BUỘC THAM CHIẾU video_id):\n"
        f"{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. Chia kịch bản thành 4 phần rõ ràng (Hook mở đầu -> Khám phá bối cảnh/nguyên liệu -> Trải nghiệm hương vị & điểm nhấn -> Tổng kết & CTA).\n"
        "2. Mỗi beat PHẢI gán `cited_video_ids` sử dụng đúng `video_id` từ danh sách bằng chứng ở trên đã truyền cảm hứng cho cấu trúc/góc quay của beat đó.\n"
        "3. TUYỆT ĐỐI CẤM các câu sáo rỗng vô nghĩa như: 'ngon gì đâu luôn á', 'nhức cái nách', 'đỉnh của chóp', 'ngon xỉu up xỉu down'. Thay bằng miêu tả cảm quan cụ thể (độ giòn, vị thanh, mùi thơm bơ tỏi, mức giá thực tế).\n"
        "4. Trả về DUY NHẤT JSON hợp lệ theo đúng cấu trúc mẫu:\n"
        f"{json.dumps(schema_example, ensure_ascii=False, indent=2)}"
    )
