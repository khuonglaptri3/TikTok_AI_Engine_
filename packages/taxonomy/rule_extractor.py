from __future__ import annotations

import math
import re

PRICE_K_REGEX = re.compile(r"\b(\d{1,4})\s*(?:k|cành|ngàn|nghìn)\b", re.IGNORECASE)
SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?…])\s+|\n+")

LEGACY_FORMAT_MAP: dict[str, str] = {
    "Nấu ăn": "Hướng dẫn nấu ăn",
    "Hướng dẫn nấu ăn": "Hướng dẫn nấu ăn",
    "Review quán ăn": "Review quán ăn",
    "Review món ăn": "Review món ăn",
    "Review sản phẩm ăn uống": "Review sản phẩm ăn uống",
    "Mukbang": "Mukbang",
}

_NULL_STRINGS = frozenset({"none", "null", "nan", "[]"})


def _clean_optional_text(val: object) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    s = str(val).strip()
    if s.lower() in _NULL_STRINGS:
        return ""
    return s


def infer_video_format(
    legacy_cat: object,
    desc: str,
    transcript: str,
    poi_name: str | None,
    is_ec_video: bool,
) -> str:
    if isinstance(legacy_cat, str) and legacy_cat in LEGACY_FORMAT_MAP:
        return LEGACY_FORMAT_MAP[legacy_cat]
    combined = f"{desc} {transcript[:400]}".lower()
    if "mukbang" in combined or "asmr" in combined:
        return "Mukbang"
    if any(kw in combined for kw in ("công thức", "cách làm", "cách nấu", "vào bếp", "nguyên liệu")):
        return "Hướng dẫn nấu ăn"
    if is_ec_video or any(kw in combined for kw in ("giỏ hàng", "unbox", "đập hộp", "siêu thị", "gói này")):
        return "Review sản phẩm ăn uống"
    if poi_name or any(kw in combined for kw in ("quán ", "tiệm ", "nhà hàng", "địa chỉ", "chi nhánh", "hẻm ")):
        return "Review quán ăn"
    return "Review món ăn"


def extract_price_tier(text: str, video_format: str) -> str:
    lower = (text or "").lower()
    if video_format == "Hướng dẫn nấu ăn" and not PRICE_K_REGEX.search(lower):
        return "home_cooking"
    if any(kw in lower for kw in ("fine dining", "sang chảnh", "5 sao", "khách sạn 5", "tiền triệu")):
        return "premium_gt500k"
    matches = [int(m.group(1)) for m in PRICE_K_REGEX.finditer(lower)]
    valid_prices = [p for p in matches if 5 <= p <= 2000]
    if valid_prices:
        median_p = sorted(valid_prices)[len(valid_prices) // 2]
        if median_p < 50:
            return "budget_lt50k"
        if median_p <= 150:
            return "mid_50_150k"
        if median_p <= 500:
            return "casual_150_500k"
        return "premium_gt500k"
    if any(kw in lower for kw in ("học sinh", "sinh viên", "vỉa hè", "bình dân", "hạt dẻ", "siêu rẻ")):
        return "budget_lt50k"
    if "buffet" in lower:
        return "casual_150_500k"
    return "unspecified"


def extract_occasions(text: str, video_format: str) -> list[str]:
    lower = (text or "").lower()
    occ: list[str] = []
    if any(kw in lower for kw in ("ăn sáng", "bữa sáng", "cơm trưa", "ăn trưa", "dân văn phòng")):
        occ.append("an_sang_trua_nhanh")
    if any(kw in lower for kw in ("ăn đêm", "khuya", "cú đêm", "2h sáng", "12h đêm")):
        occ.append("an_dem")
    if any(kw in lower for kw in ("hẹn hò", "người yêu", "cặp đôi", "kỷ niệm", "lãng mạn")):
        occ.append("hen_ho")
    if any(kw in lower for kw in ("tụ tập", "nhậu", "bạn bè", "đám bạn", "lai rai")):
        occ.append("tu_tap_ban_be")
    if any(kw in lower for kw in ("gia đình", "bố mẹ", "cả nhà", "cuối tuần")):
        occ.append("gia_dinh")
    if any(kw in lower for kw in ("du lịch", "đặc sản", "food tour", "phượt")):
        occ.append("du_lich_kham_pha")
    if video_format == "Hướng dẫn nấu ăn" or any(kw in lower for kw in ("cơm nhà", "ở trọ", "tự nấu")):
        occ.append("nau_an_tai_nha")
    if any(kw in lower for kw in ("ăn vặt", "xế chiều", "cổng trường")):
        occ.append("an_vat_xe_chieu")
    return occ[:4]


def extract_script_anatomy(
    transcript: str,
    llm_hook: object = None,
    llm_cta: object = None,
    takeaways: list[str] | None = None,
) -> tuple[str, list[str], str]:
    clean_tr = (transcript or "").strip()
    if not clean_tr:
        return "", [], ""

    sentences = [s.strip() for s in SENTENCE_SPLIT_REGEX.split(clean_tr) if s.strip()]
    if not sentences:
        words = clean_tr.split()
        hook_fallback = " ".join(words[:22])
        cta_fallback = " ".join(words[-20:]) if len(words) > 25 else ""
        return hook_fallback, takeaways or [], cta_fallback

    hook_str = _clean_optional_text(llm_hook)
    if not hook_str:
        hook_str = sentences[0]
        if len(hook_str.split()) < 8 and len(sentences) > 1:
            hook_str = f"{sentences[0]} {sentences[1]}"
        hook_words = hook_str.split()
        if len(hook_words) > 32:
            hook_str = " ".join(hook_words[:32]) + "..."

    cta_str = _clean_optional_text(llm_cta)
    if not cta_str:
        last_sent = sentences[-1] if len(sentences) > 1 else ""
        words = clean_tr.split()
        cta_str = last_sent if len(last_sent.split()) <= 35 else " ".join(words[-25:])

    beats = [clean for item in (takeaways or []) if (clean := _clean_optional_text(item))]
    if not beats and len(sentences) >= 3:
        mid = sentences[1:-1]
        step = max(1, len(mid) // 3)
        beats = [mid[i][:160] for i in range(0, min(len(mid), step * 3), step)][:3]

    return hook_str, beats, cta_str
