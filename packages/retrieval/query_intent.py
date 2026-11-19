"""Vietnamese query intent normalization: NFC Unicode, negation, F&B synonyms, and anchor guards."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from packages.retrieval.sparse.bm25 import VN_STOPWORDS, WORD_RE
from packages.taxonomy.food_hierarchy import extract_dishes_from_text

SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("sài gòn", "saigon", "hồ chí minh", "tphcm"),
    ("tàu hũ", "đậu hũ", "tào phớ", "đậu phụ"),
    ("thịt heo", "thịt lợn"),
    ("heo quay", "lợn quay"),
    ("heo", "lợn"),
    ("nước lèo", "nước dùng"),
    ("lai rai", "quán nhậu", "ăn nhậu", "nhậu"),
    ("healthy", "ăn kiêng", "giữ dáng", "ít calo", "eat clean"),
    ("mì gói", "mì tôm"),
    ("cá viên", "viên chiên", "xiên bẩn"),
    ("bánh mì que", "bánh mì cay"),
    ("hủ tiếu gõ", "hủ tiếu bình dân"),
    ("quán cóc", "vỉa hè"),
    ("xế chiều", "ăn vặt"),
    ("bánh flan", "caramen", "kem flan"),
    ("trà tắc", "trà quất"),
    ("chả giò", "nem rán"),
    ("bánh xèo miền tây", "bánh xèo"),
)

GENERIC_QUERY_TOKENS: frozenset[str] = frozenset(
    {
        *VN_STOPWORDS,
        "review", "quán", "tiệm", "nhà", "hàng", "xe", "gánh", "chợ", "cửa",
        "ăn", "uống", "thử", "ngon", "rẻ", "đắt", "đẹp", "xinh", "chill", "hot",
        "hit", "nổi", "tiếng", "đông", "khách", "chỗ", "nào", "đâu", "ở", "tại",
        "gần", "quanh", "khu", "phố", "đường", "hẻm", "ngõ", "công", "thức",
        "cách", "làm", "nấu", "chế", "biến", "hướng", "dẫn", "món", "đồ", "ẩm",
        "thực", "đặc", "sản", "người", "team", "mình", "bạn", "bè", "gia",
        "đình", "sinh", "viên", "dân", "văn", "phòng", "cặp", "đôi", "hẹn", "hò",
        "chuẩn", "vị", "gốc", "chính", "hiệu", "truyền", "thống", "siêu", "cực",
        "kỳ", "đậm", "đà", "béo", "ngậy", "giòn", "rụm", "mềm", "thơm", "nóng",
        "hổi", "lạnh", "mát", "thanh", "đạm", "nhẹ", "cay", "chua", "ngọt", "mặn",
        "đầy", "đặn", "đơn", "giản", "dễ", "nhanh", "gọn", "bữa", "sáng", "trưa",
        "chiều", "xế", "tối", "đêm", "khuya", "vỉa", "hè", "bình", "dân", "cao",
        "cấp", "sang", "chảnh", "view", "mukbang", "vlog", "tiktok", "top", "list",
        "gợi", "ý", "tìm", "kiếm", "khám", "phá", "trải", "nghiệm", "giá", "cành",
        "hợp", "lý", "hạt", "dẻ", "tự", "dưới", "trên", "khoảng", "tầm", "độ",
        "cổng", "trường", "học", "tiện", "lợi", "mua", "đóng", "gói", "cuối",
        "tuần", "buổi", "yên", "tĩnh", "tiết", "kiệm", "tụ", "tập", "cổ", "xưa",
        "mới", "cũ", "nhất", "quanh", "đây", "hôm", "nay", "ngày", "mùa",
        # Location tokens (handled via metadata or location matching, not dish OOV)
        "hồ", "chí", "minh", "sài", "gòn", "saigon", "tphcm", "hcm", "hà", "nội",
        "hanoi", "đà", "nẵng", "lạt", "huế", "cần", "thơ", "hải", "phòng", "vũng",
        "tàu", "nha", "trang", "hạ", "long", "phú", "quốc", "quy", "nhơn", "bình",
        "dương", "thạnh", "tân", "phú", "nhuận", "gò", "vấp", "thủ", "đức", "cầu",
        "giấy", "đống", "đa", "hoàn", "kiếm", "tây", "ba", "đình", "long", "biên",
        "thanh", "xuân", "cà", "mau", "sóc", "trăng", "lào", "cai", "sapa", "phan",
        "thiết", "ninh", "hội", "an", "quảng", "nam", "miền", "bắc", "trung",
        "nam", "quận", "huyện", "tỉnh", "thành", "việt", "nhật", "bản", "hàn",
        "thái", "lan", "pháp", "ý", "mỹ", "ấn",
    }
)

# Generic cooking methods / base carriers that cannot alone justify an exotic OOV noun
COOKING_OR_BASE_HELPER_TOKENS: frozenset[str] = frozenset(
    {
        "thịt", "hầm", "nướng", "chiên", "rán", "xào", "luộc", "hấp", "kho", "um",
        "om", "trộn", "nước", "khô", "tươi", "sống", "chín", "rượu", "vang", "sốt",
        "chấm", "kèm", "thêm", "ít", "nhiều", "đá", "nóng", "lạnh", "tái", "lăn",
        "mắm", "tỏi", "ớt", "sả", "tắc", "tiêu", "muối", "đường", "gừng",
        "đỏ", "trắng", "xanh", "đen", "vàng",
    }
)

_BROAD_SINGLE_WORD_DISH_HEADS: frozenset[str] = frozenset({"ốc", "chè", "kem"})

# Indivisible multi-word species/dish specifiers that must appear contiguously when requested
STRICT_COMPOUND_SPECIES: tuple[str, ...] = (
    "cá nóc",
    "thịt tuần lộc",
    "thịt lạc đà",
    "chuột túi",
    "vi cá mập",
    "vi cá",
    "gan ngỗng",
    "ốc sên pháp",
    "thịt đà điểu",
    "thịt cá sấu",
    "bánh cóng",
    "cá tầm",
    "bọ cạp chiên",
    "dế mèn chiên",
)

_PRICE_OR_NUM_RE = re.compile(r"^\d+[a-z]*$")

_NEG_MARKER_RE = re.compile(
    r"(?<!\w)(?:không\s+ăn|không\s+dùng|không\s+cho|không\s+bỏ|không\s+có|không|"
    r"chẳng\s+ăn|chẳng|đừng\s+cho|đừng\s+bỏ|đừng|(?<!ăn\s)kiêng|dị\s+ứng\s+với|dị\s+ứng|"
    r"tránh|né|ghét\s+ăn|ghét|loại\s+bỏ|bỏ\s+qua|bỏ(?!\s+(?:vào|vô|thêm)(?!\w))|trừ)\s+"
    r"([^\W_]+(?:\s+[^\W_]+){0,3})",
    flags=re.UNICODE,
)

_NEG_STOP_BOUNDARIES: frozenset[str] = frozenset(
    {
        "nhưng", "mà", "ở", "tại", "quận", "huyện", "cho", "với", "cùng", "giá",
        "buổi", "dịp", "nha", "nhé", "ạ", "không", "chẳng", "đừng", "kiêng",
        "dị", "tránh", "né", "ghét", "bỏ", "trừ", "sài", "hồ", "hà", "đà",
    }
)

_NEG_FILLERS: frozenset[str] = frozenset({"ăn", "uống", "dùng", "cho", "có", "mùi", "vị", "chất"})


@dataclass(frozen=True)
class QueryIntent:
    normalized_query: str
    positive_query: str
    expanded_bm25_query: str
    anchor_groups: tuple[tuple[str, ...], ...]
    strict_compounds: tuple[str, ...]
    negated_terms: tuple[str, ...]
    has_specific_anchors: bool
    explicit_dishes: tuple[str, ...] = ()
    culinary_synonym_groups: tuple[tuple[str, ...], ...] = ()


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def _synonyms_for_phrase_or_word(term: str) -> tuple[str, ...]:
    out: list[str] = [term]
    for grp in SYNONYM_GROUPS:
        if term in grp:
            for item in grp:
                if item not in out:
                    out.append(item)
    return tuple(out)


def parse_query_intent(query: str) -> QueryIntent:
    q_nfc = unicodedata.normalize("NFC", query or "").lower().strip()
    if not q_nfc:
        return QueryIntent(
            normalized_query="",
            positive_query="",
            expanded_bm25_query="",
            anchor_groups=(),
            strict_compounds=(),
            negated_terms=(),
            has_specific_anchors=False,
        )

    negated: list[str] = []
    spans_to_strip: list[tuple[int, int]] = []

    pos = 0
    while match := _NEG_MARKER_RE.search(q_nfc, pos):
        raw_tail = match.group(1)
        word_matches = list(WORD_RE.finditer(raw_tail))
        kept: list[str] = []
        consumed_words = 0
        for wm in word_matches:
            w = wm.group(0)
            if w in _NEG_STOP_BOUNDARIES:
                break
            consumed_words += 1
            if w in _NEG_FILLERS and not kept:
                continue
            kept.append(w)
            if len(kept) == 3:
                break
        if kept and consumed_words > 0:
            phrase = " ".join(kept)
            if phrase not in negated:
                negated.append(phrase)
            end_pos = match.start(1) + word_matches[consumed_words - 1].end()
            spans_to_strip.append((match.start(), end_pos))
            pos = end_pos
        else:
            pos = match.start(1)

    if spans_to_strip:
        chars = list(q_nfc)
        for s, e in spans_to_strip:
            for idx in range(s, min(e, len(chars))):
                chars[idx] = " "
        positive_query = re.sub(r"\s+", " ", "".join(chars)).strip()
    else:
        positive_query = q_nfc

    # Strip trailing standalone "dị ứng" left by "cho người dị ứng"
    positive_query = re.sub(r"(?<!\w)dị\s+ứng(?!\w)", " ", positive_query)
    positive_query = re.sub(r"\s+", " ", positive_query).strip()

    # Synonym expansion over positive_query
    extra_synonyms: list[str] = []
    matched_synonym_groups: list[tuple[str, ...]] = []
    for grp in SYNONYM_GROUPS:
        present = [p for p in grp if _contains_phrase(positive_query, p)]
        if present:
            for alt in grp:
                if alt not in present and alt not in extra_synonyms:
                    extra_synonyms.append(alt)
            # Keep non-location synonym groups as semantic anchor groups
            if "hồ chí minh" not in grp:
                matched_synonym_groups.append(grp)

    expanded_bm25 = (
        f"{positive_query} {' '.join(extra_synonyms)}".strip()
        if extra_synonyms
        else positive_query
    )

    strict_hits = tuple(
        comp for comp in STRICT_COMPOUND_SPECIES if _contains_phrase(positive_query, comp)
    )
    raw_explicit_dishes = extract_dishes_from_text(positive_query)
    synonym_phrases = {p for grp in matched_synonym_groups for p in grp}
    explicit_dishes = tuple(d for d in raw_explicit_dishes if d not in synonym_phrases)

    # Extract specific anchor token/phrase groups
    anchor_groups: list[tuple[str, ...]] = list(matched_synonym_groups)
    for dish_kw in explicit_dishes:
        if (dish_kw,) not in anchor_groups:
            anchor_groups.append((dish_kw,))

    covered_tokens: set[str] = {
        tok
        for grp in anchor_groups
        for phrase in grp
        if _contains_phrase(positive_query, phrase)
        for tok in WORD_RE.findall(phrase)
    }

    pos_words = [w for w in WORD_RE.findall(positive_query) if len(w) >= 2]
    specific_words = [
        w
        for w in pos_words
        if w not in GENERIC_QUERY_TOKENS
        and not _PRICE_OR_NUM_RE.match(w)
        and w not in covered_tokens
    ]

    # Separate primary culinary nouns from generic cooking/carrier helpers when primary nouns exist
    primary_nouns = [w for w in specific_words if w not in COOKING_OR_BASE_HELPER_TOKENS]
    effective_words = primary_nouns if primary_nouns else (specific_words if not anchor_groups else [])

    for w in effective_words:
        syns = _synonyms_for_phrase_or_word(w)
        if syns not in anchor_groups:
            anchor_groups.append(syns)

    has_specific = bool(anchor_groups or strict_hits)
    return QueryIntent(
        normalized_query=q_nfc,
        positive_query=positive_query,
        expanded_bm25_query=expanded_bm25,
        anchor_groups=tuple(anchor_groups),
        strict_compounds=strict_hits,
        negated_terms=tuple(negated),
        has_specific_anchors=has_specific,
        explicit_dishes=explicit_dishes,
        culinary_synonym_groups=tuple(matched_synonym_groups),
    )


def _group_in_vocab(grp: tuple[str, ...], vocab: dict[str, int]) -> bool:
    for phrase in grp:
        words = [w for w in WORD_RE.findall(phrase) if len(w) >= 2]
        if words and all(w in vocab for w in words):
            return True
    return False


def check_vocab_anchor_support(intent: QueryIntent, vocab: dict[str, int]) -> str | None:
    """Return an abstain_reason when core dish/entity anchors are absent from vocab."""
    if not intent.has_specific_anchors:
        return None

    for comp in intent.strict_compounds:
        if not _group_in_vocab((comp,), vocab):
            return f"out_of_vocabulary_query_anchor:{comp}"

    if not intent.strict_compounds:
        core_dish_groups: list[tuple[str, ...]] = [
            (d,)
            for d in intent.explicit_dishes
            if " " in d or d not in _BROAD_SINGLE_WORD_DISH_HEADS
        ] + list(intent.culinary_synonym_groups)
        if core_dish_groups and any(_group_in_vocab(g, vocab) for g in core_dish_groups):
            return None

    for grp in intent.anchor_groups:
        if not _group_in_vocab(grp, vocab):
            return f"out_of_vocabulary_query_anchor:{grp[0]}"
    return None


def row_satisfies_intent_anchors(row: dict[str, Any], intent: QueryIntent) -> bool:
    """Verify that observed video text (not noisy machine tags) matches specific culinary anchors."""
    if not intent.has_specific_anchors:
        return True

    doc_text = unicodedata.normalize(
        "NFC",
        f"{row.get('caption', '')} {row.get('poi_name') or ''} "
        f"{row.get('hook_text', '')} {row.get('transcript', '')}",
    ).lower()

    # Every strict compound species requested must appear contiguously in observed text
    for comp in intent.strict_compounds:
        if not _contains_phrase(doc_text, comp):
            return False

    # If explicit canonical dishes are named in the query, at least one must appear in observed text
    if intent.explicit_dishes:
        if not any(_contains_phrase(doc_text, dish_kw) for dish_kw in intent.explicit_dishes):
            return False

    if not intent.anchor_groups:
        return True

    # At least one specific anchor group must appear on word boundaries in observed text
    for grp in intent.anchor_groups:
        if any(_contains_phrase(doc_text, variant) for variant in grp):
            return True
    return False


def row_has_observed_anchor_word_overlap(row: dict[str, Any], intent: QueryIntent) -> bool:
    """True when observed text shares at least one non-helper word from positive anchor groups."""
    if not intent.has_specific_anchors:
        return True
    doc_text = unicodedata.normalize(
        "NFC",
        f"{row.get('caption', '')} {row.get('poi_name') or ''} "
        f"{row.get('hook_text', '')} {row.get('transcript', '')}",
    ).lower()
    if intent.strict_compounds and not all(_contains_phrase(doc_text, c) for c in intent.strict_compounds):
        return False
    doc_words = set(WORD_RE.findall(doc_text))
    anchor_words = {
        w
        for grp in intent.anchor_groups
        for variant in grp
        for w in WORD_RE.findall(variant)
        if len(w) >= 2 and w not in COOKING_OR_BASE_HELPER_TOKENS and w not in GENERIC_QUERY_TOKENS
    }
    return bool(doc_words & anchor_words) if anchor_words else True
