from __future__ import annotations

COMMON_DISH_KEYWORDS: tuple[str, ...] = (
    "bún bò",
    "bún đậu",
    "bún chả",
    "bún riêu",
    "bún thái",
    "bún mắm",
    "phở bò",
    "phở gà",
    "hủ tiếu",
    "bánh canh",
    "mì cay",
    "mì quảng",
    "mì trộn",
    "cơm tấm",
    "cơm gà",
    "cơm chiên",
    "bánh mì",
    "bánh tráng trộn",
    "bánh tráng nướng",
    "bánh cuốn",
    "bánh xèo",
    "bánh khọt",
    "chân gà",
    "ốc",
    "hải sản",
    "lẩu bò",
    "lẩu thái",
    "lẩu cá",
    "thịt nướng",
    "đồ nướng",
    "buffet",
    "gà rán",
    "xúc xích",
    "xiên bẩn",
    "cá viên chiên",
    "trà sữa",
    "cà phê",
    "matcha",
    "chè",
    "bánh ngọt",
    "tirami",
    "kem",
    "đồ chay",
    "salad",
)

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Ẩm thực Chay & Healthy", ("chay", "healthy", "eat clean", "ức gà", "salad", "kiêng", "ít calo")),
    (
        "Lẩu & Nướng",
        ("lẩu", "nướng", "bbq", "buffet", "bò tơ", "lòng nướng", "hải sản nướng"),
    ),
    (
        "Món nước & Sợi",
        ("phở", "bún", "mì ", "mì cay", "mì trộn", "mì quảng", "hủ tiếu", "bánh canh", "miến", "cháo", "súp"),
    ),
    (
        "Đồ ngọt, Trà & Cà phê",
        ("trà sữa", "cà phê", "cafe", "coffee", "matcha", "chè", "kem", "bánh ngọt", "bánh kem", "sinh tố", "nước ép", "trà trái cây"),
    ),
    (
        "Ăn vặt & Đường phố",
        ("bánh tráng", "xiên", "cá viên", "chân gà", "ốc", "ăn vặt", "bánh mì", "há cảo", "xôi", "bánh xèo", "gỏi cuốn", "nem nướng", "bắp xào", "trứng cút"),
    ),
    (
        "Cơm & Bữa chính",
        ("cơm tấm", "cơm gà", "cơm ", "cá kho", "thịt kho", "canh ", "bò né", "bít tết", "gà luộc", "vịt quay"),
    ),
    (
        "Đồ đóng gói & Tiện lợi",
        ("mì gói", "snack", "bánh kẹo", "đóng gói", "siêu thị", "cửa hàng tiện lợi", "circle k", "gs25"),
    ),
]


def extract_dishes_from_text(text: str) -> list[str]:
    lower = text.lower()
    found = [kw for kw in COMMON_DISH_KEYWORDS if kw in lower]
    return found[:8]


def map_food_category(dishes: list[str], text: str, poi_cat: str | None = None) -> str:
    combined = " ".join(dishes).lower() + " " + (text or "").lower() + " " + (poi_cat or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in combined for kw in keywords):
            return category
    return "Ẩm thực Tổng hợp"
