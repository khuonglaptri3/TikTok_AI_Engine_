"""Observable duplicate, contact/link, and noise comment indicators (M5.1)."""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

from packages.data_contracts.multimodal import CommentRecord, RawCommentInput

ObservableCommentLabel = Literal[
    "observable_duplicate",
    "contact_or_link",
    "noise_or_empty",
    "template_phrase_match",
    "no_indicator_observed",
    "unknown_ambiguous",
]

URL_OR_CONTACT_RE = re.compile(
    r"(?:https?://|www\.|t\.me/|telegram|fb\.com/|facebook\.com/|zalo|inbox\s+em|ib\s+nhận|tuyển\s+ctv|(?<!\d)0\d{2}[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d))",
    flags=re.IGNORECASE,
)
WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
REPEATED_CHAR_NOISE_RE = re.compile(r"^(?:(.)\1{5,}|[0-9\W_]+)$", flags=re.UNICODE)

CANONICAL_TEMPLATE_PHRASES: tuple[str, ...] = (
    "quán ruột của mình mỗi tuần đều ghé",
    "đồ ăn chất lượng phục vụ 10 điểm không có nhưng",
    "mới đi hôm qua công nhận xuất sắc y như lời đồn",
    "lưu ngay địa chỉ cuối tuần lập kèo liền",
)

# Short generic diner reactions and ordinary 5-8 syllable Vietnamese venue/price inquiries
# are commonly repeated organically across distinct viewers and must not be flagged as duplicates.
SHORT_ORGANIC_PHRASES: frozenset[str] = frozenset(
    {
        "ngon quá",
        "ngon lắm",
        "xin địa chỉ",
        "quán ở đâu",
        "quán ở đâu vậy",
        "quán này ở đâu vậy",
        "cho mình xin địa chỉ",
        "giá bao nhiêu",
        "nhìn ngon quá",
        "xuất sắc",
    }
)

ORGANIC_DINER_INQUIRY_RE = re.compile(
    r"^(?:cho\s+(?:mình|em|tôi)\s+(?:xin|hỏi)\s+(?:địa\s+chỉ|giá|menu)(?:\s+quán)?|"
    r"quán(?:\s+này)?\s+(?:ở\s+đâu|mở\s+cửa\s+mấy\s+giờ|bán\s+đến\s+mấy\s+giờ)|"
    r"xin\s+địa\s+chỉ(?:\s+quán)?|một\s+(?:phần|tô|suất)\s+(?:giá\s+)?bao\s+nhiêu)"
    r"(?:\s+(?:vậy|ạ|với|nhỉ|nha|nhé|ơi|shop|ad))*$"
)


def _shingles(text: str) -> set[str]:
    nfc = unicodedata.normalize("NFC", text).lower()
    words = WORD_RE.findall(nfc)
    if len(words) < 2:
        return set(words)
    return {f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1)} | set(words)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


def _norm_author(handle: str | None) -> str:
    return (handle or "").strip().lstrip("@").lower()


def _is_noise_tokens(words: list[str], normalized_text: str) -> bool:
    if not words:
        return True
    compact = "".join(words)
    return bool(REPEATED_CHAR_NOISE_RE.match(compact) or REPEATED_CHAR_NOISE_RE.match(normalized_text))


def _is_organic_short_or_inquiry(words: list[str], min_duplicate_words: int) -> bool:
    if not words:
        return False
    if len(words) < min_duplicate_words:
        return True
    if min_duplicate_words >= 5 and len(words) <= 9:
        phrase = " ".join(words)
        if phrase in SHORT_ORGANIC_PHRASES or ORGANIC_DINER_INQUIRY_RE.match(phrase):
            return True
    return False


def detect_seeding_comments(
    video_id: str,
    raw_comments: list[RawCommentInput],
    duplicate_threshold: float = 0.72,
    min_duplicate_words: int = 5,
) -> list[CommentRecord]:
    """Flag observable contact/link, empty/emoji noise, template, and multi-word near-duplicate comments.

    Preserves raw original text, keeps observable labels distinct from bot/payment claims,
    isolates contact/noise before pairwise clustering, and exempts short/ordinary Vietnamese
    diner inquiries from duplicate false positives.
    """
    if not raw_comments:
        return []

    n = len(raw_comments)
    norm_texts = [unicodedata.normalize("NFC", c.text.strip()).lower() for c in raw_comments]
    word_lists = [WORD_RE.findall(low) for low in norm_texts]
    authors = [_norm_author(c.author_handle) for c in raw_comments]

    is_contact = [bool(URL_OR_CONTACT_RE.search(low)) for low in norm_texts]
    is_noise = [
        (not is_contact[i]) and _is_noise_tokens(word_lists[i], norm_texts[i])
        for i in range(n)
    ]
    is_template = [
        (not is_contact[i])
        and (not is_noise[i])
        and any(tpl in norm_texts[i] for tpl in CANONICAL_TEMPLATE_PHRASES)
        for i in range(n)
    ]
    is_organic_exempt = [
        (not is_contact[i])
        and (not is_noise[i])
        and (not is_template[i])
        and _is_organic_short_or_inquiry(word_lists[i], min_duplicate_words)
        for i in range(n)
    ]

    # Exclude contact/link, noise, and exempted short organic inquiries before duplicate clustering
    # so spam comments never contaminate clean viewer questions into duplicate clusters.
    token_sets = [
        _shingles(c.text)
        if not (is_contact[i] or is_noise[i] or is_organic_exempt[i])
        and len(word_lists[i]) >= min_duplicate_words
        else set()
        for i, c in enumerate(raw_comments)
    ]

    max_sim = [0.0] * n
    parent = list(range(n))
    in_dup_pair = [False] * n

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(a: int, b: int) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            if ra < rb:
                parent[rb] = ra
            else:
                parent[ra] = rb

    short_phrase_freq: dict[str, int] = {}
    for i, words in enumerate(word_lists):
        if is_organic_exempt[i]:
            phrase = " ".join(words)
            short_phrase_freq[phrase] = short_phrase_freq.get(phrase, 0) + 1

    for i in range(n):
        if not token_sets[i]:
            continue
        for j in range(i + 1, n):
            if not token_sets[j]:
                continue
            # Require known, distinct normalized author handles for cross-account duplicate clustering
            if not authors[i] or not authors[j] or authors[i] == authors[j]:
                continue
            sim = _jaccard(token_sets[i], token_sets[j])
            if sim >= duplicate_threshold:
                max_sim[i] = max(max_sim[i], sim)
                max_sim[j] = max(max_sim[j], sim)
                in_dup_pair[i] = True
                in_dup_pair[j] = True
                _union(i, j)

    cluster_ids: list[int | None] = [None] * n
    root_to_cid: dict[int, int] = {}
    next_cid = 1
    for i in range(n):
        if in_dup_pair[i]:
            root = _find(i)
            if root not in root_to_cid:
                root_to_cid[root] = next_cid
                next_cid += 1
            cluster_ids[i] = root_to_cid[root]

    records: list[CommentRecord] = []
    for idx, c in enumerate(raw_comments):
        txt = c.text.strip()
        words = word_lists[idx]

        reason: str | None = None
        observable_label: ObservableCommentLabel = "no_indicator_observed"
        reason_codes: list[str] = []

        if is_contact[idx]:
            reason = "contact_or_link_spam"
            observable_label = "contact_or_link"
            reason_codes.append("regex_url_zalo_phone_or_cta")
        elif is_noise[idx]:
            reason = "emoji_or_empty_noise"
            observable_label = "noise_or_empty"
            reason_codes.append(
                "zero_lexical_tokens" if len(words) == 0 else "repeated_char_noise"
            )
        elif is_template[idx]:
            reason = "canned_praise_template"
            observable_label = "template_phrase_match"
            reason_codes.append("canonical_template_substring")
            if max_sim[idx] >= duplicate_threshold:
                reason_codes.append(f"near_duplicate_jaccard={round(max_sim[idx], 3)}")
        elif max_sim[idx] >= duplicate_threshold:
            reason = "duplicate_seeding_cluster"
            observable_label = "observable_duplicate"
            reason_codes.append(f"near_duplicate_jaccard={round(max_sim[idx], 3)}")
        elif is_organic_exempt[idx]:
            phrase = " ".join(words)
            if short_phrase_freq.get(phrase, 0) > 1 or phrase in SHORT_ORGANIC_PHRASES or ORGANIC_DINER_INQUIRY_RE.match(phrase):
                reason_codes.append("short_organic_phrase_exempt")

        records.append(
            CommentRecord(
                comment_id=c.comment_id,
                video_id=video_id,
                author_handle=c.author_handle,
                text=txt,
                original_text=c.text,
                like_count=c.like_count,
                reply_count=c.reply_count,
                is_seeding=reason is not None,
                seeding_reason=reason,
                observable_label=observable_label,
                observable_reason_codes=reason_codes,
                diagnostic_only=True,
                similarity_score=round(max_sim[idx], 4),
                cluster_id=cluster_ids[idx],
            )
        )
    return records


detect_comment_indicators = detect_seeding_comments

__all__ = [
    "CANONICAL_TEMPLATE_PHRASES",
    "ORGANIC_DINER_INQUIRY_RE",
    "ObservableCommentLabel",
    "SHORT_ORGANIC_PHRASES",
    "detect_comment_indicators",
    "detect_seeding_comments",
]
