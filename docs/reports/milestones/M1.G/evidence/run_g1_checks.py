"""Asserting G1 corpus gate verification probe across M0.G, M1.1, M1.2, and Gold snapshots."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from packages.analytics import load_verified_corpus

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dir_hashes(folder: Path) -> dict[str, str]:
    return {
        p.name: _sha256(p)
        for p in sorted(folder.iterdir())
        if p.is_file()
    }


def main() -> int:
    t0 = time.perf_counter()
    snap_v1 = ROOT / "data/corpus/20261117_recovered_v1"
    snap_v2 = ROOT / "data/corpus/20261118_taxonomy_fix_v1"
    data_card = ROOT / "docs/data-cards/tiktok_fnb_corpus_v1.md"

    before_v1 = _dir_hashes(snap_v1)
    before_v2 = _dir_hashes(snap_v2)

    # 1. Verify G0 PASS and M1.1/M1.2 COMPLETE in reports & index
    g0_receipt = json.loads(
        (ROOT / "docs/reports/milestones/M0.G/evidence/owner-gate-decision-receipt.json").read_text(encoding="utf-8")
    )
    assert g0_receipt["gate_id"] == "G0" and g0_receipt["decision"] == "PASS", g0_receipt
    assert g0_receipt["task_status"] == "COMPLETE", g0_receipt

    index_text = (ROOT / "docs/reports/milestones/README.md").read_text(encoding="utf-8")
    for required_row in ("| M0.G |", "| M1.1 |", "| M1.2 |"):
        matching = [line for line in index_text.splitlines() if line.startswith(required_row)]
        assert len(matching) == 1 and "| COMPLETE |" in matching[0], matching

    # 2. Load and verify both immutable Gold snapshots via load_verified_corpus
    m_v1, c_v1, v_v1 = load_verified_corpus(snap_v1)
    m_v2, c_v2, v_v2 = load_verified_corpus(snap_v2)

    assert m_v1.snapshot_id == "20261117_recovered_v1"
    assert m_v2.snapshot_id == "20261118_taxonomy_fix_v1"
    assert m_v2.parent_snapshot_id == "20261117_recovered_v1"
    assert m_v2.parent_manifest_sha256 == before_v1["manifest.json"]
    assert before_v1["manifest.json"] == "10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4"
    assert before_v2["manifest.json"] == "49f23739f9e2ea8f1f66fe1b299fe636c19965c99fcadf2bdd6eef7dc18c27de"

    # 3. Shape, key uniqueness, join integrity, and finite safe-ratio checks
    for label, c_df, v_df in (("v1", c_v1, v_v1), ("v2", c_v2, v_v2)):
        assert c_df.shape == (264, 15), (label, c_df.shape)
        assert v_df.shape == (70996, 49), (label, v_df.shape)
        assert c_df["author_id"].notna().all() and c_df["author_id"].is_unique
        assert v_df["video_id"].notna().all() and v_df["video_id"].is_unique
        assert set(v_df["author_id"].astype(str)).issubset(set(c_df["author_id"].astype(str)))
        for col in ("engagement_rate", "viral_multiplier", "word_per_second"):
            vals = v_df[col].to_numpy(dtype=float)
            assert np.isfinite(vals).all(), (label, col)
            assert (vals >= 0.0).all(), (label, col)

    assert set(v_v1["video_id"].astype(str)) == set(v_v2["video_id"].astype(str))

    # 4. Reproduce audited M1.1 -> M1.2 taxonomy & geography deltas
    def _has_tag(series, target: str) -> int:
        return int(series.apply(lambda items: target in list(items) if items is not None else False).sum())

    deltas = {
        "city_norm_nonnull": {
            "v1": int(v_v1["city_norm"].notna().sum()),
            "v2": int(v_v2["city_norm"].notna().sum()),
        },
        "district_norm_nonnull": {
            "v1": int(v_v1["district_norm"].notna().sum()),
            "v2": int(v_v2["district_norm"].notna().sum()),
        },
        "region_known": {
            "v1": int((v_v1["region"] != "unknown").sum()),
            "v2": int((v_v2["region"] != "unknown").sum()),
        },
        "dish_oc_count": {
            "v1": _has_tag(v_v1["dishes"], "ốc"),
            "v2": _has_tag(v_v2["dishes"], "ốc"),
        },
        "occasion_an_vat_xe_chieu_count": {
            "v1": _has_tag(v_v1["occasions"], "an_vat_xe_chieu"),
            "v2": _has_tag(v_v2["occasions"], "an_vat_xe_chieu"),
        },
    }
    for key, pair in deltas.items():
        pair["delta"] = pair["v2"] - pair["v1"]

    assert deltas["city_norm_nonnull"] == {"v1": 17014, "v2": 23478, "delta": 6464}, deltas
    assert deltas["district_norm_nonnull"] == {"v1": 4670, "v2": 13151, "delta": 8481}, deltas
    assert deltas["region_known"] == {"v1": 15931, "v2": 22986, "delta": 7055}, deltas
    assert deltas["dish_oc_count"] == {"v1": 5391, "v2": 1606, "delta": -3785}, deltas
    assert deltas["occasion_an_vat_xe_chieu_count"] == {"v1": 59765, "v2": 1365, "delta": -58400}, deltas

    # 5. Qualified data card & source rights boundary assertions
    card_text = data_card.read_text(encoding="utf-8")
    for phrase in (
        "20261117_recovered_v1",
        "20261118_taxonomy_fix_v1",
        "Public Corpus Redistribution BLOCKED",
        "Machine Labels Are Not Ground Truth",
        "POIs Do Not Prove Physical Attendance",
    ):
        assert phrase in card_text, f"Missing required data-card qualification: {phrase}"

    # 6. Verify 0 byte changes on both snapshots after checks + secret scan
    after_v1 = _dir_hashes(snap_v1)
    after_v2 = _dir_hashes(snap_v2)
    assert before_v1 == after_v1, "Snapshot 20261117_recovered_v1 mutated!"
    assert before_v2 == after_v2, "Snapshot 20261118_taxonomy_fix_v1 mutated!"

    secret_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_secrets.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert secret_proc.returncode == 0, secret_proc.stdout + secret_proc.stderr

    receipt = {
        "gate_id": "G1",
        "task_id": "M1.G",
        "checked_at": datetime.now(UTC).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
        "prerequisite_g0": "PASS",
        "upstream_tasks": {"M1.1": "COMPLETE", "M1.2": "COMPLETE"},
        "snapshots": {
            "20261117_recovered_v1": {
                "hashes": after_v1,
                "creators_shape": [264, 15],
                "videos_shape": [70996, 49],
                "bytes_unchanged": True,
            },
            "20261118_taxonomy_fix_v1": {
                "hashes": after_v2,
                "parent_snapshot_id": m_v2.parent_snapshot_id,
                "parent_manifest_sha256": m_v2.parent_manifest_sha256,
                "creators_shape": [264, 15],
                "videos_shape": [70996, 49],
                "bytes_unchanged": True,
            },
        },
        "verified_deltas": deltas,
        "data_card_path": "docs/data-cards/tiktok_fnb_corpus_v1.md",
        "data_card_sha256": _sha256(data_card),
        "public_corpus_redistribution": "BLOCKED (upstream reuse/redistribution terms unresolved)",
        "local_demonstration_scope": "ELIGIBLE",
        "secret_scan_exit_code": secret_proc.returncode,
        "technical_recommendation": "PASS (local-only corpus scope; public redistribution BLOCKED)",
        "formal_gate_status": "NOT_RUN (awaiting reciprocal peer review by Nguyễn Việt Nguyên, N)",
    }
    out_file = OUT / "g1_verification_receipt.json"
    out_file.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS: G1 verification probe succeeded in {receipt['elapsed_seconds']}s -> {out_file.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
