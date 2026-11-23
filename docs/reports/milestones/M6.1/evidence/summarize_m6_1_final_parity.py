"""Summarize M6.1 post-fix 5,000-doc parity results on finalized M2.2 human-verified qrels."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from pipelines.benchmark_retrieval.pilot_m2_2 import (
    _load_qrels,
    compute_pooled_query_metrics,
)


def main() -> None:
    repo = Path(__file__).resolve().parents[5]
    final_svd_path = repo / "artifacts/benchmarks/m6_1_v2_final_qrels_minilm_refresh.json"
    prior_path = repo / "artifacts/benchmarks/m6_1_v2_pilot.json"
    qrels_path = repo / "data/evaluation/v2_pilot/qrels_pooled_draft.jsonl"
    vids_5k_path = repo / "artifacts/indexes/dense-svd-v2/video_ids.json"
    out_path = repo / "docs/reports/milestones/M6.1/evidence/khuong_m6_1_qrels_and_parity_audit.json"

    final_svd = json.loads(final_svd_path.read_text(encoding="utf-8"))
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    qrels, qrels_meta = _load_qrels(qrels_path)
    eligible_5k = set(json.loads(vids_5k_path.read_text(encoding="utf-8")))

    svd_key = next(iter(final_svd["backends"].keys()))
    svd_bundle = final_svd["backends"][svd_key]

    summary_svd: dict[str, object] = {}
    for split_name in ("dev", "locked_test"):
        cfgs = svd_bundle["splits"][split_name]["configs"]
        cmps = svd_bundle["splits"][split_name]["paired_bootstrap_comparisons"]
        summary_svd[split_name] = {
            "configs": {
                cname: {
                    "evaluated_answerable_count": c["evaluated_answerable_count"],
                    "zero_relevant_pool_count": c["zero_relevant_pool_count"],
                    "mrr_at_10": c["mrr_at_10"],
                    "ndcg_at_10": c["ndcg_at_10"],
                    "pooled_recall_at_10": c["pooled_recall_at_10"],
                    "precision_at_10": c["precision_at_10"],
                    "mrr_at_10_all_answerable": c["mrr_at_10_all_answerable"],
                    "ndcg_at_10_all_answerable": c["ndcg_at_10_all_answerable"],
                    "unjudged_rate_at_10": c["unjudged_rate_at_10"],
                    "no_answer_abstained_count": c["no_answer_abstained_count"],
                    "fabricated_support_count": c["fabricated_support_count"],
                }
                for cname, c in cfgs.items()
            },
            "paired_bootstrap_comparisons": cmps,
        }

    # Offline finalized-qrels re-scoring of pure dense-minilm-v1 rankings (unaffected by BM25 restrict_to_df bug)
    minilm_bundle = prior["backends"]["dense-minilm-v1"]
    minilm_rescored: dict[str, object] = {}
    for split_name in ("dev", "locked_test"):
        split_out: dict[str, object] = {}
        for cname in ("dense", "dense_reranked"):
            pq_list = minilm_bundle["splits"][split_name]["configs"][cname]["per_query"]
            mrrs, ndcgs, recs, precs = [], [], [], []
            mrrs_all, ndcgs_all = [], []
            unjudged_slots = 0
            total_slots = 0
            for pq in pq_list:
                if pq.get("expect_no_answer"):
                    continue
                qid = pq["query_id"]
                r_ids = pq["retrieved_ids"][:10]
                q_judg = {v: lbl for v, lbl in qrels.get(qid, {}).items() if v in eligible_5k}
                rel_ids = {v for v, lbl in q_judg.items() if str(lbl) == "1"}
                total_slots += len(r_ids)
                unjudged_slots += sum(1 for v in r_ids if v not in q_judg)
                if not rel_ids:
                    mrrs_all.append(0.0)
                    ndcgs_all.append(0.0)
                    continue
                qm = compute_pooled_query_metrics(r_ids, rel_ids, k=10)
                mrrs.append(qm["mrr_at_10"])
                ndcgs.append(qm["ndcg_at_10"])
                recs.append(qm["pooled_recall_at_10"])
                precs.append(qm["precision_at_10"])
                mrrs_all.append(qm["mrr_at_10"])
                ndcgs_all.append(qm["ndcg_at_10"])
            split_out[cname] = {
                "evaluated_answerable_count": len(mrrs),
                "mrr_at_10": round(sum(mrrs) / max(len(mrrs), 1), 4),
                "ndcg_at_10": round(sum(ndcgs) / max(len(ndcgs), 1), 4),
                "pooled_recall_at_10": round(sum(recs) / max(len(recs), 1), 4),
                "precision_at_10": round(sum(precs) / max(len(precs), 1), 4),
                "mrr_at_10_all_answerable": round(sum(mrrs_all) / max(len(mrrs_all), 1), 4),
                "ndcg_at_10_all_answerable": round(sum(ndcgs_all) / max(len(ndcgs_all), 1), 4),
                "unjudged_rate_at_10": round(unjudged_slots / max(total_slots, 1), 4),
            }
        minilm_rescored[split_name] = split_out

    audit_payload = {
        "auditor": "K",
        "final_qrels_meta": qrels_meta,
        "prior_m6_1_qrels_sha256": prior["provenance"]["qrels_sha256"],
        "final_m2_2_qrels_sha256": final_svd["provenance"]["qrels_sha256"],
        "live_executed_5k_parity_svd_v2": summary_svd,
        "live_warm_latency_svd_v2": svd_bundle["latency_warm_requests"],
        "offline_rescored_pure_dense_minilm_v1": {
            "note": "fastembed optional package not installed on K's conda base host; pure dense/dense_reranked rankings in m6_1_v2_pilot.json searched LocalDenseIndex (5,000 docs) directly and are unaffected by the BM25 restrict_to_df omission, whereas hybrid_rrf (MiniLM) should be re-run on an environment with fastembed==0.9.1 installed.",
            "splits": minilm_rescored,
        },
    }
    out_path.write_text(json.dumps(audit_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary_svd["locked_test"]["configs"], indent=2))
    print("PAIRED:", json.dumps(summary_svd["locked_test"]["paired_bootstrap_comparisons"]["hybrid_rrf_reranked_minus_bm25_reranked"], indent=2))


if __name__ == "__main__":
    main()
