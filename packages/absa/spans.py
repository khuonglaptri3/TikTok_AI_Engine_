from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from packages.data_contracts._validators import require_non_blank
from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    AspectAggregateSummary,
    AspectName,
    AspectPolaritySummaryLabel,
    AspectSpanEvidence,
    ObservedAspectPolarity,
    TextUnitSourceKind,
)


@dataclass(frozen=True)
class TextUnitInput:
    unit_id: str
    source_kind: TextUnitSourceKind
    text: str

    def __post_init__(self) -> None:
        clean_id = require_non_blank(self.unit_id)
        if clean_id != self.unit_id:
            object.__setattr__(self, "unit_id", clean_id)


def _char_preserving_lower(nfc_text: str) -> str:
    """Lowercase while guaranteeing 1-to-1 codepoint index alignment with nfc_text."""
    out: list[str] = []
    for ch in nfc_text:
        low = ch.lower()
        out.append(low if len(low) == 1 else ch)
    return "".join(out)


def _trim_offsets(nfc_text: str, start: int, end: int) -> tuple[int, int]:
    s = max(0, start)
    e = min(len(nfc_text), end)
    while s < e and (nfc_text[s].isspace() or nfc_text[s] in ",;"):
        s += 1
    while e > s and (nfc_text[e - 1].isspace() or nfc_text[e - 1] in ",;"):
        e -= 1
    return s, e


def _compile_word_phrases(phrases: tuple[str, ...]) -> str:
    ordered = sorted(phrases, key=len, reverse=True)
    escaped = [re.escape(p).replace(r"\ ", r"\s+") for p in ordered]
    return "|".join(escaped)


_SENTENCE_DELIMITER_RE = re.compile(r"[.!?…\n;]+")

_CONTRASTIVE_DELIMITER_RE = re.compile(
    r"(?:(?:,\s*|\s+)(?:"
    r"nhưng\s+mà|nhưng|tuy\s+nhiên|bù\s+lại|ngược\s+lại|"
    r"chỉ\s+có\s+điều|điểm\s+trừ\s+là|điểm\s+cộng\s+là|"
    r"mặt\s+khác|còn\s+về|chứ\s+còn"
    r")|,\s*mà)(?!\w)"
)

_COORD_DELIMITER_RE = re.compile(r",\s*|\s+(?:và|còn|mà)\s+")

_PRE_MODIFIER_TAIL_RE = re.compile(
    r"(?:(?:cũng|lại|vẫn|hơi\s+bị)\s+)?"
    r"(?:không\s+quá|không\s+hề|chẳng\s+hề|không\s+được|chưa\s+được|"
    r"không|chẳng|chả|chưa|kém|thiếu|hơi|quá|rất|khá|cực\s+kỳ|cực|siêu)\s+$"
)

_TASTE_PHRASES: tuple[str, ...] = (
    "hương vị",
    "mùi vị",
    "khẩu vị",
    "nêm nếm",
    "gia vị",
    "nước dùng",
    "nước lèo",
    "nước chấm",
    "nước sốt",
    "nước cốt",
    "nước mắm",
    "món ăn",
    "đồ ăn",
    "thức ăn",
    "món này",
    "đồ uống",
    "nước uống",
    "thịt bò",
    "thịt gà",
    "thịt heo",
    "thịt nướng",
    "thịt",
    "hải sản",
    "bò viên",
    "chả cá",
    "chả bò",
    "chả lụa",
    "chả giò",
    "topping",
    "nhân bánh",
    "vỏ bánh",
    "sợi phở",
    "sợi bún",
    "sợi mì",
    "ngon xuất sắc",
    "thơm ngon",
    "tươi ngon",
    "ngon miệng",
    "ngon",
    "đậm đà",
    "vừa miệng",
    "hợp khẩu vị",
    "thanh ngọt",
    "ngọt thanh",
    "béo ngậy",
    "thơm phức",
    "thơm",
    "tươi rói",
    "tươi",
    "giòn rụm",
    "giòn tan",
    "giòn",
    "mềm tan",
    "mềm ngọt",
    "mặn chát",
    "mặn",
    "nhạt nhẽo",
    "nhạt",
    "tanh",
    "nguội ngắt",
    "nguội lạnh",
    "nguội",
    "ngấy",
    "ngán",
    "dở tệ",
    "dở ẹc",
    "dở",
    "khô khốc",
    "bị khô",
    "hơi khô",
    "khô",
    "bở",
    "ôi thiu",
    "ngọt gắt",
)

_PRICE_PHRASES: tuple[str, ...] = (
    "giá cả",
    "giá tiền",
    "mức giá",
    "chi phí",
    "hóa đơn",
    "tính tiền",
    "hạt dẻ",
    "bình dân",
    "phải chăng",
    "hợp túi tiền",
    "đáng tiền",
    "rẻ bèo",
    "rẻ",
    "đắt đỏ",
    "đắt",
    "mắc",
    "chặt chém",
    "giá chát",
    "hơi chát",
    "giá cao",
    "giá hơi cao",
    "giá mềm",
    "giá tốt",
    "ít đồ",
)

_HYGIENE_PHRASES: tuple[str, ...] = (
    "an toàn thực phẩm",
    "kém vệ sinh",
    "mất vệ sinh",
    "thiếu vệ sinh",
    "nhà vệ sinh",
    "vệ sinh",
    "sạch sẽ",
    "sạch tinh",
    "sạch",
    "hợp vệ sinh",
    "đảm bảo vệ sinh",
    "gọn gàng",
    "ngăn nắp",
    "thoáng mát",
    "thoáng đãng",
    "không gian",
    "chỗ ngồi",
    "bàn ghế",
    "sàn nhà",
    "toilet",
    "bát đũa",
    "chén đũa",
    "muỗng đũa",
    "dơ bẩn",
    "dơ",
    "bẩn",
    "mùi hôi",
    "hôi hám",
    "ruồi nhặng",
    "ruồi",
    "gián",
    "chuột",
    "côn trùng",
    "sợi tóc",
    "có tóc",
    "dị vật",
    "đầy khói",
    "ám khói",
    "khói",
    "nóng bức",
    "nóng nực",
    "ngột ngạt",
    "bí bách",
    "nhếch nhác",
    "ẩm mốc",
    "nhớp nháp",
)

_SERVICE_PHRASES: tuple[str, ...] = (
    "nhân viên",
    "phục vụ",
    "chủ quán",
    "anh chủ",
    "chị chủ",
    "cô chủ",
    "thu ngân",
    "bảo vệ",
    "gọi món",
    "lên món",
    "ra món",
    "quên món",
    "nhầm món",
    "sai món",
    "thái độ",
    "nhiệt tình",
    "niềm nở",
    "thân thiện",
    "chu đáo",
    "lịch sự",
    "nhanh nhẹn",
    "nhanh chóng",
    "nhanh",
    "chậm chạp",
    "quá chậm",
    "hơi chậm",
    "chậm",
    "chờ hơi lâu",
    "đợi hơi lâu",
    "chờ quá lâu",
    "đợi quá lâu",
    "chờ khá lâu",
    "đợi khá lâu",
    "lên món lâu",
    "ra món lâu",
    "gọi món lâu",
    "phục vụ lâu",
    "chờ món",
    "đợi món",
    "chờ lâu",
    "đợi lâu",
    "phải chờ",
    "phải đợi",
    "cọc cằn",
    "cọc lốc",
    "cọc",
    "cáu gắt",
    "lồi lõm",
    "khinh khách",
    "thô lỗ",
    "chảnh",
)

_IGNORED_ASPECT_COMPOUNDS: tuple[str, ...] = (
    "thú vị",
    "quý vị",
    "đơn vị",
    "định vị",
    "học vị",
    "vị trí",
    "đánh giá",
    "cá nhân",
    "tất cả",
    "ăn lâu",
    "ngồi lâu",
    "lâu đời",
    "lâu năm",
    "lâu rồi",
    "lâu lắm",
    "lâu nay",
    "lâu lâu",
    "bao lâu",
    "ăn sạch",
    "húp sạch",
    "uống sạch",
    "hết sạch",
    "bán sạch",
    "giá như",
    "giá mà",
    "giá đỗ",
    "rau giá",
    "giá sống",
    "giá trụng",
)

_IGNORED_ASPECT_COMPOUNDS_RE = re.compile(
    r"(?<!\w)(?:" + _compile_word_phrases(_IGNORED_ASPECT_COMPOUNDS) + r")(?!\w)"
)

_ASPECT_PATTERNS: dict[AspectName, re.Pattern[str]] = {
    "taste": re.compile(
        r"(?<!\w)(?:"
        + _compile_word_phrases(_TASTE_PHRASES)
        + r"|vị|cá|tôm|mực"
        + r")(?!\w)"
    ),
    "price": re.compile(
        r"(?<!\w)(?:"
        + _compile_word_phrases(_PRICE_PHRASES)
        + r"|giá"
        + r"|\d{1,4}\s*(?:k|ka|cành|nghìn|ngàn|đồng|vnđ|vnd)"
        r"(?!\s*(?:views?|lượt\s*xem|fl|follows?|followers?|tim|likes?|subs?|subscribers?|km|kg|ml|kcal|calo)\b)"
        + r"|\d{2,3}[.,]\d{3}\s*(?:đ|đồng|vnđ|vnd)"
        + r")(?!\w)"
    ),
    "hygiene": re.compile(r"(?<!\w)(?:" + _compile_word_phrases(_HYGIENE_PHRASES) + r")(?!\w)"),
    "service": re.compile(r"(?<!\w)(?:" + _compile_word_phrases(_SERVICE_PHRASES) + r")(?!\w)"),
}

_POS_PHRASES: tuple[str, ...] = (
    "ngon xuất sắc",
    "xuất sắc",
    "tuyệt vời",
    "đỉnh của chóp",
    "thơm ngon",
    "tươi ngon",
    "ngon miệng",
    "ngon lành",
    "ngon",
    "đậm đà",
    "vừa miệng",
    "hợp khẩu vị",
    "thanh ngọt",
    "ngọt thanh",
    "béo ngậy",
    "thơm phức",
    "thơm",
    "tươi rói",
    "tươi",
    "giòn rụm",
    "giòn tan",
    "giòn",
    "mềm tan",
    "mềm ngọt",
    "mềm",
    "nóng hổi",
    "đầy đặn",
    "chất lượng",
    "ưng ý",
    "rất ưng",
    "ưng",
    "rẻ bèo",
    "rẻ",
    "hạt dẻ",
    "bình dân",
    "phải chăng",
    "hợp túi tiền",
    "hợp lý",
    "đáng tiền",
    "xứng đáng",
    "giá mềm",
    "giá tốt",
    "hời",
    "sạch sẽ",
    "sạch tinh",
    "sạch",
    "hợp vệ sinh",
    "đảm bảo vệ sinh",
    "gọn gàng",
    "ngăn nắp",
    "thoáng mát",
    "thoáng đãng",
    "thoáng",
    "mát mẻ",
    "rộng rãi",
    "nhiệt tình",
    "niềm nở",
    "thân thiện",
    "chu đáo",
    "lịch sự",
    "dễ thương",
    "nhanh nhẹn",
    "nhanh chóng",
    "nhanh",
    "tận tình",
    "tận tâm",
    "chuyên nghiệp",
    "tốt",
)

_NEG_PHRASES: tuple[str, ...] = (
    "kém chất lượng",
    "kém vệ sinh",
    "mất vệ sinh",
    "thiếu vệ sinh",
    "quảng cáo lố",
    "pr lố",
    "chặt chém",
    "khinh khách",
    "thái độ với khách",
    "rất thái độ",
    "thái độ quá",
    "thái độ lắm",
    "thái độ kém",
    "dở tệ",
    "dở ẹc",
    "dở",
    "mặn chát",
    "mặn",
    "nhạt nhẽo",
    "nhạt",
    "tanh",
    "nguội ngắt",
    "nguội lạnh",
    "nguội",
    "khô khốc",
    "khô cứng",
    "bị khô",
    "hơi khô",
    "bở",
    "ngấy",
    "ngán",
    "ôi thiu",
    "ngọt gắt",
    "đắt đỏ",
    "đắt",
    "mắc",
    "giá chát",
    "hơi chát",
    "giá cao",
    "giá hơi cao",
    "ít đồ",
    "hơi ít",
    "quá ít",
    "phí tiền",
    "dơ bẩn",
    "dơ",
    "bẩn",
    "mùi hôi",
    "hôi hám",
    "hôi",
    "ruồi nhặng",
    "ruồi",
    "gián",
    "chuột",
    "côn trùng",
    "sợi tóc",
    "có tóc",
    "dị vật",
    "đầy khói",
    "ám khói",
    "khói",
    "nóng bức",
    "nóng nực",
    "ngột ngạt",
    "bí bách",
    "nhếch nhác",
    "ẩm mốc",
    "nhớp nháp",
    "chậm chạp",
    "quá chậm",
    "hơi chậm",
    "chậm",
    "chờ lâu",
    "đợi lâu",
    "lâu",
    "cọc cằn",
    "cọc lốc",
    "cọc",
    "cáu gắt",
    "lồi lõm",
    "quên món",
    "nhầm món",
    "sai món",
    "thô lỗ",
    "chảnh",
    "tệ hại",
    "quá tệ",
    "tệ",
    "thất vọng",
    "chán",
)

_NEUTRAL_PHRASES: tuple[str, ...] = (
    "chấp nhận được",
    "bình thường",
    "tạm ổn",
    "tạm được",
    "ổn áp",
    "vừa phải",
    "tầm trung",
    "cũng ổn",
)

_LITOTES_NEG_TARGETS: tuple[str, ...] = (
    "đắt đỏ",
    "đắt",
    "mắc",
    "chát",
    "cao",
    "tệ",
    "dở",
    "mặn",
    "nhạt",
    "tanh",
    "nguội",
    "ngấy",
    "ngán",
    "khô",
    "bở",
    "bẩn",
    "dơ",
    "hôi",
    "chậm",
    "lâu",
    "khó ăn",
)

_DISH_DRY_COMPOUNDS: tuple[str, ...] = (
    "hủ tiếu khô",
    "phở khô",
    "mì khô",
    "bún khô",
    "miến khô",
    "khô mực",
    "khô bò",
    "khô gà",
    "khô cá",
    "khô heo",
)

_POLARITY_MASK_COMPOUNDS: tuple[str, ...] = (
    "ăn lâu",
    "ngồi lâu",
    "lâu đời",
    "lâu năm",
    "lâu rồi",
    "lâu lắm",
    "lâu nay",
    "lâu lâu",
    "bao lâu",
    "ăn sạch",
    "húp sạch",
    "uống sạch",
    "hết sạch",
    "bán sạch",
)

_NEGATED_NEUTRAL_TARGETS: tuple[str, ...] = (
    "thể chấp nhận được",
    "thể chấp nhận",
    "chấp nhận được",
    "chấp nhận",
    "ổn áp",
    "ổn",
)

_POS_ALT = _compile_word_phrases(_POS_PHRASES)
_NEG_ALT = _compile_word_phrases(_NEG_PHRASES) + r"|khô"
_NEUTRAL_ALT = _compile_word_phrases(_NEUTRAL_PHRASES + _DISH_DRY_COMPOUNDS)
_LITOTES_ALT = _compile_word_phrases(_LITOTES_NEG_TARGETS)
_POLARITY_MASK_ALT = _compile_word_phrases(_POLARITY_MASK_COMPOUNDS)
_NEGATED_NEUTRAL_ALT = _compile_word_phrases(_NEGATED_NEUTRAL_TARGETS)

_POLARITY_MASK_RE = re.compile(r"(?<!\w)(?:" + _POLARITY_MASK_ALT + r")(?!\w)")

_LITOTES_RE = re.compile(
    r"(?<!\w)(?:không|chẳng|chả|chưa)\s+(?:quá\s+|hề\s+|bị\s+|đến\s+nỗi\s+)?(?:"
    + _LITOTES_ALT
    + r")(?:\s+lắm)?(?!\w)"
)

_NEGATED_POS_RE = re.compile(
    r"(?<!\w)(?:không|chẳng|chả|chưa|kém|thiếu)"
    r"(?:\s+(?:được|hề|có|mấy|quá|rất|thấy))?\s+(?:"
    + _POS_ALT
    + r")(?!\w)"
)

_NEGATED_NEUTRAL_RE = re.compile(
    r"(?<!\w)(?:không|chẳng|chả|chưa|khó)"
    r"(?:\s+(?:thể|hề|được|mấy|thấy|có))?\s+(?:"
    + _NEGATED_NEUTRAL_ALT
    + r")(?!\w)"
)

_NEUTRAL_RE = re.compile(r"(?<!\w)(?:" + _NEUTRAL_ALT + r")(?!\w)")
_POS_RE = re.compile(r"(?<!\w)(?:" + _POS_ALT + r")(?!\w)")
_NEG_RE = re.compile(r"(?<!\w)(?:" + _NEG_ALT + r")(?!\w)")


def _split_by_regex(text: str, start: int, end: int, pattern: re.Pattern[str]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    cursor = start
    for match in pattern.finditer(text, start, end):
        if match.start() > cursor:
            out.append((cursor, match.start()))
        cursor = match.end()
    if cursor < end:
        out.append((cursor, end))
    return out


def _detect_aspects_in_range(lower_text: str, start: int, end: int) -> list[tuple[int, int, AspectName]]:
    scan_start = max(0, start - 24)
    scan_end = min(len(lower_text), end + 24)
    ignored = [
        (m.start(), m.end())
        for m in _IGNORED_ASPECT_COMPOUNDS_RE.finditer(lower_text, scan_start, scan_end)
    ]
    hits: list[tuple[int, int, AspectName]] = []
    for aspect in ASPECT_NAMES:
        for match in _ASPECT_PATTERNS[aspect].finditer(lower_text, start, end):
            if not _overlaps_any(match.start(), match.end(), ignored):
                hits.append((match.start(), match.end(), aspect))
    hits.sort(key=lambda item: (item[0], -(item[1] - item[0]), ASPECT_NAMES.index(item[2])))
    # Filter overlapping aspect matches by keeping earliest/longest first
    deduped: list[tuple[int, int, AspectName]] = []
    last_end = -1
    for m_start, m_end, aspect in hits:
        if m_start >= last_end:
            deduped.append((m_start, m_end, aspect))
            last_end = m_end
    return deduped


def _subsplit_coordinated_clause(
    lower_text: str,
    c_start: int,
    c_end: int,
    *,
    polarity_tau: float,
) -> list[tuple[int, int]]:
    raw_chunks = _split_by_regex(lower_text, c_start, c_end, _COORD_DELIMITER_RE)
    if len(raw_chunks) <= 1:
        return [(c_start, c_end)]

    chunk_aspects: list[set[AspectName]] = [
        {aspect for _, _, aspect in _detect_aspects_in_range(lower_text, s, e)}
        for s, e in raw_chunks
    ]

    # Merge adjacent coordinated chunks unless BOTH sides contain distinct aspects or opposing polarities
    merged: list[tuple[int, int, set[AspectName]]] = []
    for (s, e), aspects in zip(raw_chunks, chunk_aspects, strict=True):
        if not merged:
            merged.append((s, e, set(aspects)))
            continue
        prev_s, prev_e, prev_aspects = merged[-1]
        if prev_aspects and aspects:
            distinct = prev_aspects != aspects or len(prev_aspects | aspects) > 1
            if not distinct:
                _, prev_lbl = _score_local_polarity(lower_text[prev_s:prev_e], polarity_tau=polarity_tau)
                _, curr_lbl = _score_local_polarity(lower_text[s:e], polarity_tau=polarity_tau)
                opposing = (
                    prev_lbl in {"positive", "negative"}
                    and curr_lbl in {"positive", "negative"}
                    and prev_lbl != curr_lbl
                )
            else:
                opposing = False
            if distinct or opposing:
                merged.append((s, e, set(aspects)))
            else:
                merged[-1] = (prev_s, e, prev_aspects | aspects)
        elif not prev_aspects and aspects:
            prev_score, _ = _score_local_polarity(
                lower_text[prev_s:prev_e], polarity_tau=polarity_tau
            )
            if prev_score != 0.0:
                merged[-1] = (prev_s, e, set(aspects))
            else:
                # Drop leading aspect-free filler chunk (e.g., "Hôm qua ghé quán, ") when followed by an aspect chunk
                merged[-1] = (s, e, set(aspects))
        else:
            # Keep trailing predicate/modifier chunk attached to preceding aspect chunk
            merged[-1] = (prev_s, e, prev_aspects | aspects)

    return [(s, e) for s, e, _ in merged]


def _partition_multi_aspect_clause(
    lower_text: str, c_start: int, c_end: int
) -> list[tuple[int, int, AspectName]]:
    hits = _detect_aspects_in_range(lower_text, c_start, c_end)
    if not hits:
        return []

    distinct_aspects = {aspect for _, _, aspect in hits}
    if len(distinct_aspects) == 1:
        only_aspect = hits[0][2]
        return [(c_start, c_end, only_aspect)]

    # Group consecutive hits of the same aspect into runs
    runs: list[tuple[int, int, AspectName]] = []
    for m_start, m_end, aspect in hits:
        if runs and runs[-1][2] == aspect:
            runs[-1] = (runs[-1][0], m_end, aspect)
        else:
            runs.append((m_start, m_end, aspect))

    boundaries: list[int] = [c_start]
    for idx in range(len(runs) - 1):
        prev_end = runs[idx][1]
        next_start = runs[idx + 1][0]
        between = lower_text[prev_end:next_start]
        mod_match = _PRE_MODIFIER_TAIL_RE.search(between)
        split_at = prev_end + mod_match.start() if mod_match is not None else next_start
        boundaries.append(split_at)
    boundaries.append(c_end)

    partitions: list[tuple[int, int, AspectName]] = []
    for idx, (_r_start, _r_end, aspect) in enumerate(runs):
        partitions.append((boundaries[idx], boundaries[idx + 1], aspect))
    return partitions


def _overlaps_any(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
    return any(start < occ_e and end > occ_s for occ_s, occ_e in occupied)


def _score_local_polarity(
    lower_slice: str,
    *,
    polarity_tau: float,
) -> tuple[float, ObservedAspectPolarity]:
    occupied: list[tuple[int, int]] = []
    pos = 0.0
    neg = 0.0

    # 0. Non-sentiment idioms/temporal compounds ("lâu đời", "ăn sạch", "bán sạch") -> mask 0.0
    for m in _POLARITY_MASK_RE.finditer(lower_slice):
        if not _overlaps_any(m.start(), m.end(), occupied):
            occupied.append((m.start(), m.end()))

    # 1. Softened litotes ("không quá đắt", "không tệ") -> neutral 0.0
    for m in _LITOTES_RE.finditer(lower_slice):
        if not _overlaps_any(m.start(), m.end(), occupied):
            occupied.append((m.start(), m.end()))

    # 2. Negated positive phrases ("không ngon", "chưa sạch", "kém nhiệt tình") -> negative
    for m in _NEGATED_POS_RE.finditer(lower_slice):
        if not _overlaps_any(m.start(), m.end(), occupied):
            occupied.append((m.start(), m.end()))
            neg += 1.0

    # 3. Negated neutral/acceptability phrases ("không chấp nhận được", "không ổn", "chưa ổn") -> negative
    for m in _NEGATED_NEUTRAL_RE.finditer(lower_slice):
        if not _overlaps_any(m.start(), m.end(), occupied):
            occupied.append((m.start(), m.end()))
            neg += 1.0

    # 4. Explicit neutral phrases ("bình thường", "tạm ổn", "ổn áp", "vừa phải", "tầm trung") -> neutral 0.0
    for m in _NEUTRAL_RE.finditer(lower_slice):
        if not _overlaps_any(m.start(), m.end(), occupied):
            occupied.append((m.start(), m.end()))

    # 5. Remaining unnegated positive phrases
    for m in _POS_RE.finditer(lower_slice):
        if not _overlaps_any(m.start(), m.end(), occupied):
            occupied.append((m.start(), m.end()))
            pos += 1.0

    # 6. Remaining unnegated negative phrases
    for m in _NEG_RE.finditer(lower_slice):
        if not _overlaps_any(m.start(), m.end(), occupied):
            occupied.append((m.start(), m.end()))
            neg += 1.0

    total = pos + neg
    score = 0.0 if total == 0.0 else round(max(-1.0, min(1.0, (pos - neg) / total)), 4)

    if score >= polarity_tau:
        label: ObservedAspectPolarity = "positive"
    elif score <= -polarity_tau:
        label = "negative"
    else:
        label = "neutral"

    return score, label


def extract_unit_aspect_spans(
    unit: TextUnitInput,
    *,
    polarity_tau: float = 0.15,
) -> list[AspectSpanEvidence]:
    """Extract NFC-exact 4-aspect span evidence from a single creator or viewer text unit."""
    if not (0.0 <= polarity_tau <= 1.0):
        raise ValueError("polarity_tau must be within [0.0, 1.0]")

    nfc_text = unicodedata.normalize("NFC", unit.text)
    if not nfc_text.strip():
        return []

    lower_text = _char_preserving_lower(nfc_text)
    spans: list[AspectSpanEvidence] = []

    for sent_start, sent_end in _split_by_regex(lower_text, 0, len(lower_text), _SENTENCE_DELIMITER_RE):
        for cont_start, cont_end in _split_by_regex(
            lower_text, sent_start, sent_end, _CONTRASTIVE_DELIMITER_RE
        ):
            for coord_start, coord_end in _subsplit_coordinated_clause(
                lower_text,
                cont_start,
                cont_end,
                polarity_tau=polarity_tau,
            ):
                for raw_s, raw_e, aspect in _partition_multi_aspect_clause(
                    lower_text, coord_start, coord_end
                ):
                    s, e = _trim_offsets(nfc_text, raw_s, raw_e)
                    if s >= e:
                        continue
                    span_text = nfc_text[s:e]
                    assert nfc_text[s:e] == span_text
                    score, label = _score_local_polarity(
                        lower_text[s:e],
                        polarity_tau=polarity_tau,
                    )
                    spans.append(
                        AspectSpanEvidence(
                            unit_id=unit.unit_id,
                            source_kind=unit.source_kind,
                            aspect=aspect,
                            polarity_label=label,
                            polarity_score=score,
                            start_char=s,
                            end_char=e,
                            span_text=span_text,
                        )
                    )

    return spans


def summarize_units_aspects(
    units: list[TextUnitInput],
    *,
    min_support_units: int = 1,
    polarity_tau: float = 0.15,
) -> tuple[dict[AspectName, AspectAggregateSummary], list[AspectSpanEvidence], list[str]]:
    """Aggregate extracted aspect spans across units while preserving absent_unknown vs observed neutral."""
    if min_support_units < 1:
        raise ValueError("min_support_units must be >= 1")
    if not (0.0 <= polarity_tau <= 1.0):
        raise ValueError("polarity_tau must be within [0.0, 1.0]")

    all_spans: list[AspectSpanEvidence] = []
    pain_points: list[str] = []

    for unit in units:
        unit_spans = extract_unit_aspect_spans(unit, polarity_tau=polarity_tau)
        all_spans.extend(unit_spans)
        for sp in unit_spans:
            if sp.polarity_label == "negative" and len(pain_points) < 6:
                item = f"[{sp.aspect}] {sp.span_text[:110]}"
                if item not in pain_points:
                    pain_points.append(item)

    summaries: dict[AspectName, AspectAggregateSummary] = {}
    for aspect in ASPECT_NAMES:
        aspect_spans = [sp for sp in all_spans if sp.aspect == aspect]
        mention_unit_count = len({sp.unit_id for sp in aspect_spans})
        span_count = len(aspect_spans)
        if mention_unit_count == 0:
            summaries[aspect] = AspectAggregateSummary(
                aspect=aspect,
                presence_status="absent_unknown",
                polarity_label="unknown",
                mean_score=None,
                mention_unit_count=0,
                span_count=0,
                sufficient_support=False,
            )
            continue

        mean_val = round(
            sum(sp.polarity_score for sp in aspect_spans) / span_count,
            4,
        )
        if mean_val >= polarity_tau:
            summary_label: AspectPolaritySummaryLabel = "positive"
        elif mean_val <= -polarity_tau:
            summary_label = "negative"
        else:
            summary_label = "neutral"

        summaries[aspect] = AspectAggregateSummary(
            aspect=aspect,
            presence_status="observed",
            polarity_label=summary_label,
            mean_score=mean_val,
            mention_unit_count=mention_unit_count,
            span_count=span_count,
            sufficient_support=mention_unit_count >= min_support_units,
        )

    return summaries, all_spans, pain_points
