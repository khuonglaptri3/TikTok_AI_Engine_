"""Write frozen disjoint 20-dev and 20-locked-test M2.2 queries (including genuine NFD Unicode queries)."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
PILOT_DIR = ROOT / "data/evaluation/v2_pilot"


def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


DEV_QUERIES: list[dict[str, Any]] = [
    {"query_id": "d_k01", "split": "dev", "author": "K", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "tàu hũ nước đường gừng nóng ở Sài Gòn"},
    {"query_id": "d_k02", "split": "dev", "author": "K", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "quán nhậu lai rai mồi bén buổi tối cùng bạn bè"},
    {"query_id": "d_n01", "split": "dev", "author": "N", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "bánh mì thịt heo quay da giòn rụm buổi sáng"},
    {"query_id": "d_n02", "split": "dev", "author": "N", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "thực đơn ăn kiêng ít calo giữ dáng cho dân văn phòng"},
    {"query_id": "d_k03", "split": "dev", "author": "K", "phenomenon": "unicode_nfd", "expect_no_answer": False, "filters": {}, "query": _nfd("bánh cuốn nóng nhân thịt mộc nhĩ Hà Nội")},
    {"query_id": "d_k04", "split": "dev", "author": "K", "phenomenon": "unicode_nfd", "expect_no_answer": False, "filters": {}, "query": _nfd("lẩu bò nhúng dấm nước dừa thanh ngọt")},
    {"query_id": "d_n03", "split": "dev", "author": "N", "phenomenon": "unicode_nfd", "expect_no_answer": False, "filters": {}, "query": _nfd("cơm gà xối mỡ da giòn Quận 1")},
    {"query_id": "d_k05", "split": "dev", "author": "K", "phenomenon": "negation", "expect_no_answer": False, "filters": {}, "query": "bún đậu chấm nước mắm không mắm tôm"},
    {"query_id": "d_n04", "split": "dev", "author": "N", "phenomenon": "negation", "expect_no_answer": False, "filters": {}, "query": "lẩu hải sản thanh ngọt không cay cho gia đình"},
    {"query_id": "d_n05", "split": "dev", "author": "N", "phenomenon": "negation", "expect_no_answer": False, "filters": {}, "query": "trà trái cây tươi thanh mát không trà sữa"},
    {"query_id": "d_k06", "split": "dev", "author": "K", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"city_norm": "hà nội", "food_category": "Món nước & Sợi"}, "query": "review bún riêu cua đồng đậm đà"},
    {"query_id": "d_k07", "split": "dev", "author": "K", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"city_norm": "hồ chí minh", "video_format": "Review quán ăn"}, "query": "quán ốc hương xào bơ tỏi bình dân"},
    {"query_id": "d_k08", "split": "dev", "author": "K", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"video_format": "Hướng dẫn nấu ăn"}, "query": "cách ướp thịt nướng mật ong mềm ngon"},
    {"query_id": "d_n06", "split": "dev", "author": "N", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"city_norm": "hà nội", "food_category": "Đồ ngọt, Trà & Cà phê"}, "query": "tiệm bánh ngọt tiramisu hẹn hò lãng mạn"},
    {"query_id": "d_n07", "split": "dev", "author": "N", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"video_format": "Mukbang"}, "query": "mukbang gà rán sốt phô mai giòn tan"},
    {"query_id": "d_n08", "split": "dev", "author": "N", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"city_norm": "vũng tàu"}, "query": "hải sản tươi sống giá hợp lý gần biển"},
    {"query_id": "d_k09", "split": "dev", "author": "K", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {}, "query": "công thức nấu thịt kangaroo hầm rượu vang đỏ"},
    {"query_id": "d_k10", "split": "dev", "author": "K", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {}, "query": "review nhà hàng sashimi cá nóc fugu chuẩn Nhật"},
    {"query_id": "d_n09", "split": "dev", "author": "N", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {}, "query": "cách làm bánh haggis truyền thống Scotland tại nhà"},
    {"query_id": "d_n10", "split": "dev", "author": "N", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {}, "query": "review quán thịt tuần lộc nướng Bắc Âu ở Lào Cai"},
]

TEST_QUERIES: list[dict[str, Any]] = [
    {"query_id": "t_k01", "split": "locked_test", "author": "K", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "hủ tiếu nước lèo ngọt xương ăn khuya Sài Gòn"},
    {"query_id": "t_k02", "split": "locked_test", "author": "K", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "xiên bẩn viên chiên cổng trường xế chiều"},
    {"query_id": "t_n01", "split": "locked_test", "author": "N", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "công thức làm chả giò giòn lâu tại nhà"},
    {"query_id": "t_n02", "split": "locked_test", "author": "N", "phenomenon": "synonym", "expect_no_answer": False, "filters": {}, "query": "bánh flan kem trứng béo mịn tráng miệng"},
    {"query_id": "t_k03", "split": "locked_test", "author": "K", "phenomenon": "unicode_nfd", "expect_no_answer": False, "filters": {}, "query": _nfd("bún chả nướng than hoa chuẩn Hà Nội")},
    {"query_id": "t_n03", "split": "locked_test", "author": "N", "phenomenon": "unicode_nfd", "expect_no_answer": False, "filters": {}, "query": _nfd("bánh xèo tôm nhảy giòn rụm miền Trung")},
    {"query_id": "t_n04", "split": "locked_test", "author": "N", "phenomenon": "unicode_nfd", "expect_no_answer": False, "filters": {}, "query": _nfd("trà mãng cầu chua ngọt giải nhiệt mùa hè")},
    {"query_id": "t_k04", "split": "locked_test", "author": "K", "phenomenon": "negation", "expect_no_answer": False, "filters": {}, "query": "phở bò nước trong thanh ngọt không hành"},
    {"query_id": "t_k05", "split": "locked_test", "author": "K", "phenomenon": "negation", "expect_no_answer": False, "filters": {}, "query": "mì trộn tóp mỡ đậm đà không cay"},
    {"query_id": "t_n05", "split": "locked_test", "author": "N", "phenomenon": "negation", "expect_no_answer": False, "filters": {}, "query": "ức gà áp chảo ăn kiêng không dầu mỡ"},
    {"query_id": "t_k06", "split": "locked_test", "author": "K", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"city_norm": "hồ chí minh", "food_category": "Món nước & Sợi"}, "query": "review bánh canh cua đặc quánh chả cua"},
    {"query_id": "t_k07", "split": "locked_test", "author": "K", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"city_norm": "hà nội", "food_category": "Đồ ngọt, Trà & Cà phê"}, "query": "quán cà phê trứng phố cổ thơm béo"},
    {"query_id": "t_k08", "split": "locked_test", "author": "K", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"video_format": "Hướng dẫn nấu ăn"}, "query": "hướng dẫn làm sườn xào chua ngọt đưa cơm"},
    {"query_id": "t_n06", "split": "locked_test", "author": "N", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"city_norm": "đà lạt"}, "query": "review lẩu gà lá é nóng hổi buổi tối"},
    {"query_id": "t_n07", "split": "locked_test", "author": "N", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"food_category": "Ăn vặt & Đường phố"}, "query": "bánh tráng nướng giòn rụm ăn vặt sinh viên"},
    {"query_id": "t_n08", "split": "locked_test", "author": "N", "phenomenon": "filtered", "expect_no_answer": False, "filters": {"food_category": "Ẩm thực Chay & Healthy"}, "query": "nhà hàng đồ chay thanh tịnh cho gia đình"},
    {"query_id": "t_k09", "split": "locked_test", "author": "K", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {"city_norm": "cà mau"}, "query": "review quán bánh quesadilla phô mai chuẩn Mexico ở Cà Mau"},
    {"query_id": "t_k10", "split": "locked_test", "author": "K", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {}, "query": "hướng dẫn chế biến escargot ốc sên Pháp đút lò bơ tỏi"},
    {"query_id": "t_n09", "split": "locked_test", "author": "N", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {}, "query": "mukbang dế mèn chiên bọ cạp chiên giòn kiểu Campuchia"},
    {"query_id": "t_n10", "split": "locked_test", "author": "N", "phenomenon": "no_answer", "expect_no_answer": True, "filters": {}, "query": "review nhà hàng thịt lạc đà nướng tảng chuẩn Dubai"},
]


def _write(path: Path, items: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite frozen query file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as fp:
        for row in items:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    assert len(DEV_QUERIES) == 20 and len(TEST_QUERIES) == 20
    _write(PILOT_DIR / "dev_queries.jsonl", DEV_QUERIES)
    _write(PILOT_DIR / "test_queries.jsonl", TEST_QUERIES)
    print("Wrote dev_queries.jsonl (20) and test_queries.jsonl (20)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
