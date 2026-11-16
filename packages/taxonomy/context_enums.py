from __future__ import annotations

VIDEO_FORMATS = (
    "Review quán ăn",
    "Review món ăn",
    "Review sản phẩm ăn uống",
    "Hướng dẫn nấu ăn",
    "Mukbang",
)

FOOD_CATEGORIES = (
    "Món nước & Sợi",
    "Cơm & Bữa chính",
    "Ăn vặt & Đường phố",
    "Lẩu & Nướng",
    "Đồ ngọt, Trà & Cà phê",
    "Đồ đóng gói & Tiện lợi",
    "Ẩm thực Chay & Healthy",
    "Ẩm thực Tổng hợp",
)

PRICE_TIERS = (
    "budget_lt50k",
    "mid_50_150k",
    "casual_150_500k",
    "premium_gt500k",
    "home_cooking",
    "unspecified",
)

OCCASION_LABELS = (
    "an_sang_trua_nhanh",
    "an_vat_xe_chieu",
    "an_dem",
    "hen_ho",
    "tu_tap_ban_be",
    "gia_dinh",
    "nau_an_tai_nha",
    "du_lich_kham_pha",
)

DURATION_BUCKETS = (
    "ultra_short_lt20s",
    "short_20_45s",
    "medium_45_90s",
    "long_gt90s",
)


def classify_duration_bucket(duration_sec: float | int | None) -> str:
    val = float(duration_sec or 0.0)
    if val < 20.0:
        return "ultra_short_lt20s"
    if val <= 45.0:
        return "short_20_45s"
    if val <= 90.0:
        return "medium_45_90s"
    return "long_gt90s"
