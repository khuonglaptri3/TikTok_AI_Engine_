"""Assemble blinded K_draft & N_draft judgments, compute Cohen's kappa, and emit blinded_pool.csv + qrels."""
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

    # Optional manual adjudication overrides written after inspecting disagreements
    adj_overrides_path = EVIDENCE_DIR / "adjudication_overrides.json"
    adj_overrides: dict[str, dict[str, str]] = (
        json.loads(adj_overrides_path.read_text(encoding="utf-8"))
        if adj_overrides_path.is_file()
        else {}
    )

    csv_rows: list[dict[str, Any]] = []
    qrel_rows: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []

    k_all: list[str] = []
    n_all: list[str] = []

    for cand in candidates:
        sid = str(cand["slot_id"])
        kr = str(k_map[sid]["rel"]).strip().upper()
        nr = str(n_map[sid]["rel"]).strip().upper()
        kn = str(k_map[sid].get("note", "")).strip()
        nn = str(n_map[sid].get("note", "")).strip()
        k_all.append(kr)
        n_all.append(nr)

        if kr == nr:
            adj_rel = kr
            adj_note = kn or nn
        elif sid in adj_overrides:
            adj_rel = str(adj_overrides[sid]["adjudicated_rel"])
            adj_note = str(adj_overrides[sid]["adjudication_note"])
        else:
            # Conservative tie-break until explicit override: if either is U or 0 vs 1 without override, flag U
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
                "K_human_verified": False,
                "N_human_verified": False,
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
                "K_human_verified": False,
                "N_human_verified": False,
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

    # Also write no_answer_raw_audit.csv
    raw_no_ans = _load_jsonl(EVIDENCE_DIR / "no_answer_raw_candidates.jsonl")
    audited_no_ans: list[dict[str, Any]] = []
    for r in raw_no_ans:
        vid = str(r["video_id"])
        note = (
            "Partial single-ingredient overlap (fairground scorpion mukbang only; lacks fried crickets & Cambodian style)"
            if vid == "7445291514290375943"
            else "Non-relevant boilerplate/partial token match; requested dish/cuisine absent"
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
        "raw_agreement_count": len(candidates) - len(disagreements),
        "raw_agreement_rate": round((len(candidates) - len(disagreements)) / len(candidates), 4),
        "cohens_kappa_ternary": compute_cohens_kappa(k_all, n_all, ("0", "1", "U")),
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
        f"Assembled {len(candidates)} pairs: raw_agreement={agreement_summary['raw_agreement_rate']}, "
        f"kappa={agreement_summary['cohens_kappa_ternary']}, disagreements={len(disagreements)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
