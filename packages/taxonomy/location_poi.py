from __future__ import annotations

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

CITY_ALIASES: dict[str, str] = {
    "sài gòn": "hồ chí minh",
    "saigon": "hồ chí minh",
    "tp hcm": "hồ chí minh",
    "tphcm": "hồ chí minh",
    "tp. hồ chí minh": "hồ chí minh",
    "tp hồ chí minh": "hồ chí minh",
    "thành phố hồ chí minh": "hồ chí minh",
    "ho chi minh": "hồ chí minh",
    "ho chi minh city": "hồ chí minh",
    "hcmc": "hồ chí minh",
    "ha noi": "hà nội",
    "hanoi": "hà nội",
    "thủ đô hà nội": "hà nội",
    "thành phố hà nội": "hà nội",
    "da nang": "đà nẵng",
    "da lat": "đà lạt",
    "can tho": "cần thơ",
    "hai phong": "hải phòng",
    "vung tau": "vũng tàu",
    "nha trang": "nha trang",
}

CITY_TO_REGION: dict[str, str] = {
    "hà nội": "north",
    "hải phòng": "north",
    "quảng ninh": "north",
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
    "sóc trăng": "south",
    "bạc liêu": "south",
    "cà mau": "south",
}


def _clean_str(val: object) -> str | None:
    if val is None:
        return None
    s = str(val).strip().lower()
    if not s or s in {"none", "null", "nan", "không có thông tin", "others", "việt nam"}:
        return None
    return CITY_ALIASES.get(s, s)


def resolve_location(
    poi_city: object = None,
    poi_address: object = None,
    llm_city: object = None,
    llm_district: object = None,
) -> tuple[str | None, str | None, str, str]:
    """Resolve (city_norm, district_norm, region, location_source) with GPS POI priority."""
    p_city = _clean_str(poi_city)
    p_addr = str(poi_address).strip().lower() if poi_address is not None and str(poi_address) != "nan" else ""
    l_city = _clean_str(llm_city)
    l_dist = _clean_str(llm_district)

    # Extract district from POI address if district missing
    resolved_dist = l_dist
    if not resolved_dist and p_addr:
        for d in HCM_DISTRICTS | HANOI_DISTRICTS:
            if d in p_addr:
                resolved_dist = d
                break

    # 1. Official GPS POI city wins
    if p_city:
        region = CITY_TO_REGION.get(p_city, "unknown")
        return p_city, resolved_dist, region, "poi_gps"

    # 2. If POI address contains unambiguous city or district
    if p_addr:
        for alias, norm_c in CITY_ALIASES.items():
            if alias in p_addr:
                return norm_c, resolved_dist, CITY_TO_REGION.get(norm_c, "unknown"), "poi_gps"
        if resolved_dist in HCM_DISTRICTS:
            return "hồ chí minh", resolved_dist, "south", "poi_gps"
        if resolved_dist in HANOI_DISTRICTS:
            return "hà nội", resolved_dist, "north", "poi_gps"

    # 3. Unambiguous district overrides conflicting dish-name LLM city (e.g. "Bún đậu Hà Nội ở Quận 7")
    if resolved_dist in HCM_DISTRICTS:
        return "hồ chí minh", resolved_dist, "south", "district_resolved"
    if resolved_dist in HANOI_DISTRICTS:
        return "hà nội", resolved_dist, "north", "district_resolved"

    # 4. Fallback to LLM inferred city
    if l_city:
        region = CITY_TO_REGION.get(l_city, "unknown")
        return l_city, resolved_dist, region, "llm_inferred"

    return None, resolved_dist, "unknown", "unknown"
