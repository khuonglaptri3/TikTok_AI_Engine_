from __future__ import annotations

import math
import re

HCM_DISTRICTS: set[str] = {
    "quận 1",
    "quận 2",
    "quận 3",
    "quận 4",
    "quận 5",
    "quận 6",
    "quận 7",
    "quận 8",
    "quận 9",
    "quận 10",
    "quận 11",
    "quận 12",
    "thủ đức",
    "thành phố thủ đức",
    "bình thạnh",
    "phú nhuận",
    "gò vấp",
    "tân bình",
    "tân phú",
    "bình tân",
    "bình chánh",
    "nhà bè",
    "hóc môn",
    "củ chi",
    "cần giờ",
}

HANOI_DISTRICTS: set[str] = {
    "ba đình",
    "hoàn kiếm",
    "hai bà trưng",
    "đống đa",
    "cầu giấy",
    "thanh xuân",
    "tây hồ",
    "hà đông",
    "long biên",
    "bắc từ liêm",
    "nam từ liêm",
    "hoàng mai",
    "gia lâm",
    "đông anh",
    "thanh trì",
}

DISTRICT_ALIASES: dict[str, str] = {
    **{f"district {i}": f"quận {i}" for i in range(1, 13)},
    "binh thanh": "bình thạnh",
    "phu nhuan": "phú nhuận",
    "go vap": "gò vấp",
    "tan binh": "tân bình",
    "tan phu": "tân phú",
    "binh tan": "bình tân",
    "binh chanh": "bình chánh",
    "nha be": "nhà bè",
    "hoc mon": "hóc môn",
    "cu chi": "củ chi",
    "can gio": "cần giờ",
    "thu duc": "thủ đức",
    "ba dinh": "ba đình",
    "hoan kiem": "hoàn kiếm",
    "hai ba trung": "hai bà trưng",
    "dong da": "đống đa",
    "cau giay": "cầu giấy",
    "thanh xuan": "thanh xuân",
    "tay ho": "tây hồ",
    "ha dong": "hà đông",
    "long bien": "long biên",
    "hoang mai": "hoàng mai",
    "gia lam": "gia lâm",
    "dong anh": "đông anh",
    "thanh tri": "thanh trì",
}

_ALL_DISTRICT_KEYS = sorted(
    [*HCM_DISTRICTS, *HANOI_DISTRICTS, *DISTRICT_ALIASES.keys()],
    key=len,
    reverse=True,
)
_DISTRICT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (DISTRICT_ALIASES.get(key, key), re.compile(rf"(?<!\w){re.escape(key)}(?!\w)"))
    for key in _ALL_DISTRICT_KEYS
]

CITY_ALIASES: dict[str, str] = {
    "hồ chí minh": "hồ chí minh",
    "sài gòn": "hồ chí minh",
    "saigon": "hồ chí minh",
    "tp hcm": "hồ chí minh",
    "tphcm": "hồ chí minh",
    "tp.hcm": "hồ chí minh",
    "tp. hồ chí minh": "hồ chí minh",
    "tp hồ chí minh": "hồ chí minh",
    "thành phố hồ chí minh": "hồ chí minh",
    "ho chi minh": "hồ chí minh",
    "ho chi minh city": "hồ chí minh",
    "hcmc": "hồ chí minh",
    "hà nội": "hà nội",
    "ha noi": "hà nội",
    "hanoi": "hà nội",
    "thủ đô hà nội": "hà nội",
    "thành phố hà nội": "hà nội",
    "đà nẵng": "đà nẵng",
    "da nang": "đà nẵng",
    "đà lạt": "đà lạt",
    "da lat": "đà lạt",
    "thành phố đà lạt": "đà lạt",
    "huế": "huế",
    "hue": "huế",
    "thành phố huế": "huế",
    "thừa thiên huế": "huế",
    "thừa thiên - huế": "huế",
    "cần thơ": "cần thơ",
    "can tho": "cần thơ",
    "hải phòng": "hải phòng",
    "hai phong": "hải phòng",
    "vũng tàu": "vũng tàu",
    "vung tau": "vũng tàu",
    "nha trang": "nha trang",
    "hạ long": "hạ long",
    "ha long": "hạ long",
    "phú quốc": "phú quốc",
    "phu quoc": "phú quốc",
    "quy nhơn": "quy nhơn",
    "quy nhon": "quy nhơn",
    "bình dương": "bình dương",
    "binh duong": "bình dương",
    "biên hòa": "biên hòa",
    "bien hoa": "biên hòa",
    "phan thiết": "phan thiết",
    "phan thiet": "phan thiết",
    "thành phố phan thiết": "phan thiết",
    "ninh bình": "ninh bình",
    "ninh binh": "ninh bình",
}

_CITY_ALIAS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (norm_c, re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)"))
    for alias, norm_c in sorted(CITY_ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True)
]

CITY_TO_REGION: dict[str, str] = {
    "hà nội": "north",
    "hải phòng": "north",
    "quảng ninh": "north",
    "quảng yên": "north",
    "hạ long": "north",
    "bắc ninh": "north",
    "hải dương": "north",
    "hưng yên": "north",
    "nam định": "north",
    "thái bình": "north",
    "ninh bình": "north",
    "thái nguyên": "north",
    "lạng sơn": "north",
    "lào cai": "north",
    "sapa": "north",
    "hà giang": "north",
    "cao bằng": "north",
    "sơn la": "north",
    "vĩnh phúc": "north",
    "tam đảo": "north",
    "bắc giang": "north",
    "hà nam": "north",
    "phú thọ": "north",
    "đà nẵng": "central",
    "huế": "central",
    "thừa thiên huế": "central",
    "hội an": "central",
    "quảng nam": "central",
    "nha trang": "central",
    "khánh hòa": "central",
    "đà lạt": "central",
    "lâm đồng": "central",
    "bảo lộc": "central",
    "quy nhơn": "central",
    "bình định": "central",
    "phan thiết": "central",
    "bình thuận": "central",
    "phan rang": "central",
    "vinh": "central",
    "nghệ an": "central",
    "thanh hóa": "central",
    "hà tĩnh": "central",
    "quảng bình": "central",
    "đồng hới": "central",
    "quảng ngãi": "central",
    "tuy hòa": "central",
    "phú yên": "central",
    "buôn ma thuột": "central",
    "đắk lắk": "central",
    "pleiku": "central",
    "gia lai": "central",
    "kon tum": "central",
    "hồ chí minh": "south",
    "cần thơ": "south",
    "vũng tàu": "south",
    "bà rịa - vũng tàu": "south",
    "bình dương": "south",
    "thủ dầu một": "south",
    "thuận an": "south",
    "dĩ an": "south",
    "đồng nai": "south",
    "biên hòa": "south",
    "tây ninh": "south",
    "long an": "south",
    "tiền giang": "south",
    "mỹ tho": "south",
    "bến tre": "south",
    "vĩnh long": "south",
    "trà vinh": "south",
    "đồng tháp": "south",
    "an giang": "south",
    "châu đốc": "south",
    "long xuyên": "south",
    "kiên giang": "south",
    "rạch giá": "south",
    "phú quốc": "south",
    "hà tiên": "south",
    "sóc trăng": "south",
    "bạc liêu": "south",
    "cà mau": "south",
}


def _clean_str(val: object) -> str | None:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    s = str(val).strip().lower()
    if not s or s in {"none", "null", "nan", "không có thông tin", "others", "việt nam", "vietnam"}:
        return None
    if s in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[s]
    return CITY_ALIASES.get(s, s)


def _extract_district(text: str) -> str | None:
    for norm_dist, pattern in _DISTRICT_PATTERNS:
        if pattern.search(text):
            return norm_dist
    return None


def _extract_city(text: str) -> str | None:
    for norm_city, pattern in _CITY_ALIAS_PATTERNS:
        if pattern.search(text):
            return norm_city
    return None


def _district_parent(dist: str | None) -> tuple[str | None, str | None]:
    if dist in HCM_DISTRICTS:
        return "hồ chí minh", "south"
    if dist in HANOI_DISTRICTS:
        return "hà nội", "north"
    return None, None


def resolve_location(
    poi_city: object = None,
    poi_address: object = None,
    llm_city: object = None,
    llm_district: object = None,
    poi_name: object = None,
) -> tuple[str | None, str | None, str, str]:
    """Resolve (city_norm, district_norm, region, location_source) with GPS POI priority."""
    p_city = _clean_str(poi_city)
    p_name = _clean_str(poi_name)
    p_addr_clean = _clean_str(poi_address) or ""
    l_city = _clean_str(llm_city)
    l_dist = _clean_str(llm_district)

    # Extract district from POI address or POI name when district is missing
    resolved_dist = l_dist
    if not resolved_dist and p_addr_clean:
        resolved_dist = _extract_district(p_addr_clean)
    if not resolved_dist and p_name:
        resolved_dist = _extract_district(p_name)

    # 1. Official GPS POI city wins (also handles district names in poi.city)
    if p_city:
        p_parent_city, p_parent_reg = _district_parent(p_city)
        if p_parent_city and p_parent_reg:
            return p_parent_city, resolved_dist or p_city, p_parent_reg, "poi_gps"
        region = CITY_TO_REGION.get(p_city, "unknown")
        return p_city, resolved_dist, region, "poi_gps"

    # 2. If POI address contains unambiguous city or district
    if p_addr_clean:
        addr_city = _extract_city(p_addr_clean)
        if addr_city:
            return addr_city, resolved_dist, CITY_TO_REGION.get(addr_city, "unknown"), "poi_gps"
        parent_city, parent_reg = _district_parent(resolved_dist)
        if parent_city and parent_reg:
            return parent_city, resolved_dist, parent_reg, "poi_gps"

    # 3. If POI name itself states a city or district (e.g., "Ho Chi Minh City", "Hanoi", "Gò Vấp")
    if p_name:
        name_city = _extract_city(p_name)
        if name_city:
            return name_city, resolved_dist, CITY_TO_REGION.get(name_city, "unknown"), "poi_gps"
        name_dist = _extract_district(p_name)
        if name_dist:
            parent_city, parent_reg = _district_parent(name_dist)
            if parent_city and parent_reg:
                return parent_city, resolved_dist or name_dist, parent_reg, "poi_gps"

    # 4. Unambiguous district overrides conflicting dish-name LLM city (e.g. "Bún đậu Hà Nội ở Quận 7")
    parent_city, parent_reg = _district_parent(resolved_dist)
    if parent_city and parent_reg:
        return parent_city, resolved_dist, parent_reg, "district_resolved"

    # 5. Handle district mistakenly stored inside llm_city (e.g., "nhà bè", "long biên")
    if l_city:
        l_parent_city, l_parent_reg = _district_parent(l_city)
        if l_parent_city and l_parent_reg:
            return l_parent_city, resolved_dist or l_city, l_parent_reg, "district_resolved"
        region = CITY_TO_REGION.get(l_city, "unknown")
        return l_city, resolved_dist, region, "llm_inferred"

    return None, resolved_dist, "unknown", "unknown"


DISH_ORIGIN_CITY_PHRASES_RE: re.Pattern[str] = re.compile(
    r"(?i)\b(?:"
    r"bún\s+bò\s+huế|nem\s+nướng\s+nha\s+trang|bánh\s+mì\s+(?:cay\s+)?hải\s+phòng|"
    r"cơm\s+gà\s+hội\s+an|cao\s+lầu\s+hội\s+an|hủ\s+tiếu\s+mỹ\s+tho|"
    r"(?:xôi\s+cua|bánh\s+tầm(?:\s+cay)?|cua)\s+cà\s+mau|"
    r"(?:chuẩn\s+vị|hương\s+vị|phong\s+cách|kiểu)\s+(?:hà\s+nội|sài\s+gòn|huế|đà\s+nẵng|nha\s+trang|cà\s+mau)"
    r")\b"
)


def resolve_location_from_caption(caption: str) -> tuple[str | None, str | None, str]:
    """Infer venue location from caption/brief text while masking dish-origin city idioms."""
    cleaned = DISH_ORIGIN_CITY_PHRASES_RE.sub(" ", caption or "").strip()
    if not cleaned:
        return None, None, "unknown"
    city, dist, region, _ = resolve_location(poi_address=cleaned)
    return city, dist, region
