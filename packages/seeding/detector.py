from __future__ import annotations

import re
import unicodedata

from packages.data_contracts.multimodal import CommentRecord, RawCommentInput

URL_OR_CONTACT_RE = re.compile(
    r"(?:https?://|www\.|zalo|inbox\s+em|ib\s+nhận|tuyển\s+ctv|0\d{2}[\s.\-]?\d{3}[\s.\-]?\d{4})",
    flags=re.IGNORECASE,
)
WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)

SEEDING_TEMPLATE_PHRASES: tuple[str, ...] = (
    "quán ruột của mình mỗi tuần đều ghé",
    "đồ ăn chất lượng phục vụ 10 điểm không có nhưng",
    "mới đi hôm qua công nhận xuất sắc y như lời đồn",
    "lưu ngay địa chỉ cuối tuần lập kèo liền",
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
) -> list[CommentRecord]:
    """Detect spam links, bot emoji bursts, and near-duplicate coordinated seeding templates."""
    if not raw_comments:
        return []

    token_sets = [_shingles(c.text) for c in raw_comments]
    n = len(raw_comments)
    max_sim = [0.0] * n
    cluster_ids: list[int | None] = [None] * n
    next_cluster = 1

    for i in range(n):
        if not token_sets[i]:
            continue
        for j in range(i + 1, n):
            if not token_sets[j]:
                continue
            # Different users posting near-identical praise in the same comment thread
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
        words = WORD_RE.findall(lower)

        reason: str | None = None
        if URL_OR_CONTACT_RE.search(lower):
            reason = "contact_or_link_spam"
        elif len(words) == 0:
            reason = "emoji_or_empty_noise"
        elif max_sim[idx] >= duplicate_threshold:
            reason = "duplicate_seeding_cluster"
        elif any(tpl in lower for tpl in SEEDING_TEMPLATE_PHRASES):
            reason = "canned_praise_template"

        records.append(
            CommentRecord(
                comment_id=c.comment_id,
                video_id=video_id,
                author_handle=c.author_handle,
                text=txt,
                like_count=c.like_count,
                reply_count=c.reply_count,
                is_seeding=reason is not None,
                seeding_reason=reason,
                similarity_score=round(max_sim[idx], 4),
                cluster_id=cluster_ids[idx],
            )
        )
    return records
