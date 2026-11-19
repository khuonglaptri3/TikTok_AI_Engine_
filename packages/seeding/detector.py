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
    r"(?:https?://|www\.|zalo|inbox\s+em|ib\s+nhận|tuyển\s+ctv|0\d{2}[\s.\-]?\d{3}[\s.\-]?\d{4})",
    flags=re.IGNORECASE,
)
WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)

CANONICAL_TEMPLATE_PHRASES: tuple[str, ...] = (
    "quán ruột của mình mỗi tuần đều ghé",
    "đồ ăn chất lượng phục vụ 10 điểm không có nhưng",
    "mới đi hôm qua công nhận xuất sắc y như lời đồn",
    "lưu ngay địa chỉ cuối tuần lập kèo liền",
)

# Short generic diner reactions are commonly repeated organically across distinct viewers
# and must not be flagged as near-duplicate clusters without deeper thread evidence.
SHORT_ORGANIC_PHRASES: frozenset[str] = frozenset(
    {
        "ngon quá",
        "ngon lắm",
        "xin địa chỉ",
        "quán ở đâu",
        "quán ở đâu vậy",
        "giá bao nhiêu",
        "nhìn ngon quá",
        "xuất sắc",
    }
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


def detect_seeding_comments(
    video_id: str,
    raw_comments: list[RawCommentInput],
    duplicate_threshold: float = 0.72,
    min_duplicate_words: int = 5,
) -> list[CommentRecord]:
    """Flag observable contact/link, empty/emoji noise, and multi-word near-duplicate comments.

    Preserves raw original text, keeps observable labels distinct from bot/payment claims,
    and exempts short organic repeated phrases (< min_duplicate_words) from duplicate flagging.
    """
    if not raw_comments:
        return []

    word_lists = [WORD_RE.findall(unicodedata.normalize("NFC", c.text).lower()) for c in raw_comments]
    token_sets = [
        _shingles(c.text) if len(words) >= min_duplicate_words else set()
        for c, words in zip(raw_comments, word_lists)
    ]
    n = len(raw_comments)
    max_sim = [0.0] * n
    cluster_ids: list[int | None] = [None] * n
    next_cluster = 1

    # Track short identical reactions solely for transparent auditability (never flagged positive)
    short_phrase_freq: dict[str, int] = {}
    for words in word_lists:
        if 1 <= len(words) < min_duplicate_words:
            phrase = " ".join(words)
            short_phrase_freq[phrase] = short_phrase_freq.get(phrase, 0) + 1

    for i in range(n):
        if not token_sets[i]:
            continue
        for j in range(i + 1, n):
            if not token_sets[j]:
                continue
            same_author = (
                bool(raw_comments[i].author_handle)
                and raw_comments[i].author_handle == raw_comments[j].author_handle
            )
            sim = _jaccard(token_sets[i], token_sets[j])
            if sim >= duplicate_threshold and not same_author:
                max_sim[i] = max(max_sim[i], sim)
                max_sim[j] = max(max_sim[j], sim)
                cid = cluster_ids[i] or cluster_ids[j]
                if cid is None:
                    cid = next_cluster
                    next_cluster += 1
                cluster_ids[i] = cid
                cluster_ids[j] = cid

    records: list[CommentRecord] = []
    for idx, c in enumerate(raw_comments):
        txt = c.text.strip()
        lower = unicodedata.normalize("NFC", txt).lower()
        words = word_lists[idx]

        reason: str | None = None
        observable_label: ObservableCommentLabel = "no_indicator_observed"
        reason_codes: list[str] = []

        if URL_OR_CONTACT_RE.search(lower):
            reason = "contact_or_link_spam"
            observable_label = "contact_or_link"
            reason_codes.append("regex_url_zalo_phone_or_cta")
        elif len(words) == 0:
            reason = "emoji_or_empty_noise"
            observable_label = "noise_or_empty"
            reason_codes.append("zero_lexical_tokens")
        elif max_sim[idx] >= duplicate_threshold:
            reason = "duplicate_seeding_cluster"
            observable_label = "observable_duplicate"
            reason_codes.append(f"near_duplicate_jaccard={round(max_sim[idx], 3)}")
        elif any(tpl in lower for tpl in CANONICAL_TEMPLATE_PHRASES):
            reason = "canned_praise_template"
            observable_label = "template_phrase_match"
            reason_codes.append("canonical_template_substring")
        else:
            phrase = " ".join(words)
            if (
                1 <= len(words) < min_duplicate_words
                and (short_phrase_freq.get(phrase, 0) > 1 or phrase in SHORT_ORGANIC_PHRASES)
            ):
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
    "ObservableCommentLabel",
    "SHORT_ORGANIC_PHRASES",
    "detect_comment_indicators",
    "detect_seeding_comments",
]
