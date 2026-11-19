"""Assemble blinded K & N judgments, apply K's owner-confirmed full-transcript audit & Q1..Q6 rulings, and emit blinded_pool.csv + qrels."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
EVIDENCE_DIR = Path(__file__).resolve().parent
PILOT_DIR = ROOT / "data/evaluation/v2_pilot"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compute_cohens_kappa(labels_a: list[str], labels_b: list[str], categories: tuple[str, ...] = ("0", "1", "U")) -> float:
    n = len(labels_a)
    if n == 0 or n != len(labels_b):
        return 0.0
    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    pe = sum(
        (sum(1 for a in labels_a if a == cat) / n) * (sum(1 for b in labels_b if b == cat) / n)
        for cat in categories
    )
    if abs(1.0 - pe) < 1e-12:
        return 1.0
    return round((po - pe) / (1.0 - pe), 4)


def _load_k_full_audit_overrides() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    audit_path = EVIDENCE_DIR / "khuong_408_full_transcript_audit.jsonl"
    rulings_path = EVIDENCE_DIR / "khuong_q1_q6_adjudication.json"
    if not audit_path.is_file() or not rulings_path.is_file():
        return {}, {}
    audit_map = {str(r["slot_id"]): r for r in _load_jsonl(audit_path)}
    rulings_doc = json.loads(rulings_path.read_text(encoding="utf-8"))
    q_overrides: dict[str, str] = {}
    for cluster in rulings_doc.get("rulings", {}).values():
        for sid, lbl in cluster.get("overrides", {}).items():
            q_overrides[str(sid)] = str(lbl).strip().upper()
    return audit_map, q_overrides


def main() -> int:
    candidates = _load_jsonl(EVIDENCE_DIR / "blinded_candidates_only.jsonl")
    k_rows = _load_jsonl(EVIDENCE_DIR / "judgments_K_dev.jsonl") + _load_jsonl(EVIDENCE_DIR / "judgments_K_test.jsonl")
    n_rows = _load_jsonl(EVIDENCE_DIR / "judgments_N_dev.jsonl") + _load_jsonl(EVIDENCE_DIR / "judgments_N_test.jsonl")

    k_map = {str(r["slot_id"]): r for r in k_rows}
    n_map = {str(r["slot_id"]): r for r in n_rows}

    missing_k = [c["slot_id"] for c in candidates if c["slot_id"] not in k_map]
    missing_n = [c["slot_id"] for c in candidates if c["slot_id"] not in n_map]
    if missing_k or missing_n:
        raise ValueError(f"Missing judgments: K={len(missing_k)}, N={len(missing_n)}")

    adj_overrides_path = EVIDENCE_DIR / "adjudication_overrides.json"
    adj_overrides: dict[str, dict[str, str]] = (
        json.loads(adj_overrides_path.read_text(encoding="utf-8"))
        if adj_overrides_path.is_file()
        else {}
    )
    k_full_audit_map, k_q_overrides = _load_k_full_audit_overrides()
    has_k_full_signoff = bool(k_full_audit_map)
    n_signoff_path = EVIDENCE_DIR / "nguyen_signoff_receipt.json"
    n_signoff_doc: dict[str, Any] = (
        json.loads(n_signoff_path.read_text(encoding="utf-8"))
        if n_signoff_path.is_file()
        else {}
    )
    has_n_signoff = bool(n_signoff_doc.get("N_human_verified", False))

    csv_rows: list[dict[str, Any]] = []
    qrel_rows: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []

    k_initial_all: list[str] = []
    k_all: list[str] = []
    n_all: list[str] = []

    for cand in candidates:
        sid = str(cand["slot_id"])
        kr_initial = str(k_map[sid]["rel"]).strip().upper()
        nr = str(n_map[sid]["rel"]).strip().upper()
        kn_initial = str(k_map[sid].get("note", "")).strip()
        nn = str(n_map[sid].get("note", "")).strip()
        k_initial_all.append(kr_initial)

        if has_k_full_signoff:
            audit_rec = k_full_audit_map[sid]
            kr = k_q_overrides.get(sid, str(audit_rec["provisional_K_full_transcript_rel"]).strip().upper())
            kn = str(audit_rec.get("note", "")).strip() or kn_initial
            k_verified = True
        else:
            kr = kr_initial
            kn = kn_initial
            k_verified = False

        k_all.append(kr)
        n_all.append(nr)

        if kr == nr:
            adj_rel = kr
            adj_note = kn or nn
        elif has_k_full_signoff:
            adj_rel = kr
            adj_note = (
                f"[K full-transcript human-verified={kr}; "
                f"N adopted gemini-3.1-flash-lite 500c={nr} without manual review] {kn}"
            )
        elif sid in adj_overrides:
            adj_rel = str(adj_overrides[sid]["adjudicated_rel"])
            adj_note = str(adj_overrides[sid]["adjudication_note"])
        else:
            adj_rel = "U"
            adj_note = f"Pending adjudication: K={kr} ({kn}) vs N={nr} ({nn})"

        if kr != nr:
            disagreements.append(
                {
                    "slot_id": sid,
                    "query_id": cand["query_id"],
                    "split": cand["split"],
                    "phenomenon": cand["phenomenon"],
                    "query_nfc": cand["query_nfc"],
                    "filters": cand["filters"],
                    "video_id": cand["video_id"],
                    "city_norm": cand["city_norm"],
                    "video_format": cand["video_format"],
                    "caption": cand["caption"],
                    "transcript": cand["transcript"][:450],
                    "K_rel_draft": kr,
                    "K_note": kn,
                    "N_rel_draft": nr,
                    "N_note": nn,
                    "adjudicated_rel": adj_rel,
                    "adjudication_note": adj_note,
                }
            )

        csv_rows.append(
            {
                "slot_id": sid,
                "query_id": cand["query_id"],
                "split": cand["split"],
                "author": cand["author"],
                "phenomenon": cand["phenomenon"],
                "query_nfc": cand["query_nfc"],
                "filters_json": json.dumps(cand["filters"], ensure_ascii=False),
                "video_id": cand["video_id"],
                "city_norm": cand["city_norm"] or "",
                "video_format": cand["video_format"],
                "food_category": cand["food_category"],
                "poi_name": cand["poi_name"] or "",
                "caption": cand["caption"].replace("\n", " "),
                "transcript_excerpt": cand["transcript"][:320].replace("\n", " "),
                "K_rel_draft": kr,
                "N_rel_draft": nr,
                "adjudicated_rel": adj_rel,
                "evidence_note": adj_note,
                "K_human_verified": k_verified,
                "N_human_verified": has_n_signoff,
            }
        )
        qrel_rows.append(
            {
                "slot_id": sid,
                "query_id": cand["query_id"],
                "split": cand["split"],
                "video_id": cand["video_id"],
                "K_rel_draft": kr,
                "N_rel_draft": nr,
                "adjudicated_rel": adj_rel,
                "evidence_note": adj_note,
                "K_human_verified": k_verified,
                "N_human_verified": has_n_signoff,
            }
        )

    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    with (PILOT_DIR / "blinded_pool.csv").open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    with (PILOT_DIR / "qrels_pooled_draft.jsonl").open("w", encoding="utf-8") as fp:
        for r in qrel_rows:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")

    no_ans_special_notes = {
        "7445291514290375943": "Partial single-ingredient overlap (fairground dried scorpion mukbang only; lacks fried crickets & Cambodian style)",
        "7414434775777201438": "Japanese Omakase multi-course sashimi set mentioning pufferfish ('cá nóc') once in passing alongside whale/tuna/cod; not a fugu sashimi review",
        "7420417135618379015": "Japanese Omakase serving pufferfish milt ('tinh hoàn cá nóc Shirako'), not fugu sashimi",
        "7463049980094237960": "Nha Trang curried/grilled porcupine pufferfish ('cá nóc nhím um cà ri'), not Japanese fugu sashimi",
        "7307968717030296850": "Western restaurant review mentioning French whelk ('ốc bulot Pháp'), not escargot land-snail baking recipe",
    }
    raw_no_ans = _load_jsonl(EVIDENCE_DIR / "no_answer_raw_candidates.jsonl")
    audited_no_ans: list[dict[str, Any]] = []
    for r in raw_no_ans:
        vid = str(r["video_id"])
        note = no_ans_special_notes.get(
            vid,
            "Non-relevant boilerplate/partial token match; requested dish/cuisine absent",
        )
        audited_no_ans.append(
            {
                **r,
                "caption": str(r["caption"]).replace("\n", " "),
                "transcript_excerpt": str(r["transcript_excerpt"]).replace("\n", " "),
                "raw_candidate_rel": "0",
                "audit_note": note,
            }
        )
    with (PILOT_DIR / "no_answer_raw_audit.csv").open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(audited_no_ans[0].keys()))
        writer.writeheader()
        writer.writerows(audited_no_ans)

    agreement_summary = {
        "total_blinded_pairs": len(candidates),
        "provenance_stage": (
            "two_contributor_signed_off_K_full_transcript_and_N_disagreement_concurrence"
            if (has_k_full_signoff and has_n_signoff)
            else "initial_truncated_blinded_draft"
        ),
        "K_label_source": "human_full_transcript_and_Q1_Q6_adjudication" if has_k_full_signoff else "draft",
        "N_label_source": (
            "288_matched_precheck_plus_120_N_confirmed_concurrence_with_K_2026-11-19"
            if has_n_signoff
            else "draft"
        ),
        "initial_truncated_draft_agreement": {
            "raw_agreement_count": sum(1 for a, b in zip(k_initial_all, n_all) if a == b),
            "raw_agreement_rate": round(sum(1 for a, b in zip(k_initial_all, n_all) if a == b) / len(candidates), 4),
            "cohens_kappa_ternary": compute_cohens_kappa(k_initial_all, n_all, ("0", "1", "U")),
        },
        "pre_final_concurrence_agreement": (
            n_signoff_doc.get("scope", {}).get("pre_review_agreement_vs_K_full", {})
            if has_n_signoff
            else {}
        ),
        "raw_agreement_count": len(candidates) - len(disagreements),
        "raw_agreement_rate": round((len(candidates) - len(disagreements)) / len(candidates), 4),
        "cohens_kappa_ternary": compute_cohens_kappa(k_all, n_all, ("0", "1", "U")),
        "K_human_verified_all": has_k_full_signoff,
        "N_human_verified_all": has_n_signoff,
        "K_counts": {lbl: k_all.count(lbl) for lbl in ("1", "0", "U")},
        "N_counts": {lbl: n_all.count(lbl) for lbl in ("1", "0", "U")},
        "adjudicated_counts": {
            lbl: sum(1 for r in qrel_rows if r["adjudicated_rel"] == lbl) for lbl in ("1", "0", "U")
        },
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
    }
    (EVIDENCE_DIR / "pool_agreement_and_disagreements.json").write_text(
        json.dumps(agreement_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Assembled {len(candidates)} pairs: K_verified={has_k_full_signoff}, N_verified={has_n_signoff}, "
        f"raw_agreement={agreement_summary['raw_agreement_rate']}, "
        f"kappa={agreement_summary['cohens_kappa_ternary']}, disagreements={len(disagreements)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
