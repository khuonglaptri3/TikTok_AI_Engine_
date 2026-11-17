"""Verify the bounded documentation subtask without external dependencies.

Run from the repository root using an available Python 3 interpreter.
The output concerns documentation integrity, not product acceptance.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[5]
EVIDENCE = Path(__file__).resolve().parent
PLAN = ROOT / "docs/planning/TikTok_AI_Engine_Milestone.md"
RESOURCES = ROOT / "docs/planning/TikTok_AI_Engine_Resources_and_Deployment.md"
COMPANION = ROOT / "ReFactor_structure/04_IMPLEMENTATION_PLAN.md"
AGENTS = ROOT / "AGENTS.md"
NOTES = EVIDENCE / "plan-rewrite-notes.md"
ALLOCATION = EVIDENCE / "two-person-allocation.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append({"name": name, "result": "PASS" if condition else "FAIL", "detail": detail})

    content = PLAN.read_text(encoding="utf-8")
    pattern = r"^\| (M[0-6]\.(?:[123]|G)) \| ([KN]) \| ([KN]) \| (\d+) \| (\d+) \| (.*?) \|$"
    rows = re.findall(pattern, content, re.M)
    expected = {
        "M0.1", "M0.2", "M0.3", "M0.G", "M1.1", "M1.2", "M1.G",
        "M2.1", "M2.2", "M2.3", "M2.G", "M3.1", "M3.2", "M3.3", "M3.G",
        "M4.1", "M4.2", "M4.G", "M5.1", "M5.2", "M5.G", "M6.1", "M6.2", "M6.G",
    }
    check("exact_24_task_ids", len(rows) == 24 and {row[0] for row in rows} == expected, len(rows))
    check("reciprocal_owner_reviewer", all(owner != peer and {owner, peer} == {"K", "N"} for _, owner, peer, *_ in rows), "Every task includes both contributors")

    totals = {"K": sum(int(row[3]) for row in rows), "N": sum(int(row[4]) for row in rows)}
    core = {"K": sum(int(row[3]) for row in rows if int(row[0][1]) <= 2), "N": sum(int(row[4]) for row in rows if int(row[0][1]) <= 2)}
    future = {person: totals[person] - core[person] for person in totals}
    check("exact_equal_total", totals == {"K": 94, "N": 94}, totals)
    check("exact_equal_core_and_future", core == {"K": 40, "N": 40} and future == {"K": 54, "N": 54}, {"core": core, "future": future})
    check("days_and_share", sum(totals.values()) == 188 and all(points * 0.5 == 47 and points / sum(totals.values()) == 0.5 for points in totals.values()), {"points": 188, "person_days": 94, "each_person_days": 47, "share_each": 0.5})

    allocation = json.loads(ALLOCATION.read_text(encoding="utf-8"))
    by_id = {task["id"]: task for task in allocation["tasks"]}
    matching = len(by_id) == 24 and set(by_id) == expected
    for task_id, owner, peer, k_points, n_points, dependencies in rows:
        item = by_id.get(task_id, {})
        matching = matching and item.get("primary_owner") == owner and item.get("peer_reviewer") == peer
        matching = matching and item.get("points_by_contributor") == {"K": int(k_points), "N": int(n_points)}
        matching = matching and item.get("dependencies_and_parallel_boundary") == dependencies
        matching = matching and item.get("report_path") == f"docs/reports/milestones/{task_id}/README.md"
        matching = matching and item.get("owner_delivery_points") == item["points_by_contributor"][owner]
        matching = matching and item.get("peer_review_and_integration_points") == item["points_by_contributor"][peer]
        matching = matching and all(item.get("estimated_days_by_contributor", {}).get(p) == int(points) * 0.5 for p, points in (("K", k_points), ("N", n_points)))
    check("json_matches_every_plan_row", matching, "IDs, owners, reviewers, points, days, dependencies and report paths")
    check("json_totals_match", allocation["totals"]["points_by_contributor"] == totals and allocation["totals"]["core_points_by_contributor"] == core and allocation["totals"]["conditional_points_by_contributor"] == future and allocation["totals"]["estimated_days_by_contributor"] == {"K": 47, "N": 47}, allocation["totals"])

    missing_definitions = [task_id for task_id in sorted(expected) if f"**{task_id} — " not in content]
    missing_reports = [task_id for task_id in sorted(expected) if f"../reports/milestones/{task_id}/README.md" not in content]
    check("every_task_has_definition_and_report_path", not missing_definitions and not missing_reports, {"missing_definitions": missing_definitions, "missing_report_paths": missing_reports})
    gate_rows = re.findall(r"^\| G[0-6] \| M[0-6]\.G \| .*? \| (.*?) \|$", content, re.M)
    check("all_seven_gates_not_run", len(gate_rows) == 7 and set(gate_rows) == {"NOT_RUN"}, gate_rows)
    check("no_checked_completion_in_companion", "[x]" not in COMPANION.read_text(encoding="utf-8"), "All execution steps are prospective/unchecked")

    archives = json.loads((EVIDENCE / "prior-plan-preservation.json").read_text(encoding="utf-8"))
    preserved = []
    for record in archives["files"]:
        path = EVIDENCE / record["archive"]
        preserved.append({"archive": record["archive"], "hash_matches": sha256(path) == record["sha256"], "bytes_match": path.stat().st_size == record["bytes"]})
    check("four_original_sources_preserved", len(preserved) == 4 and all(r["hash_matches"] and r["bytes_match"] for r in preserved), preserved)

    previous_agents = (EVIDENCE / "prior-project-agents.md").read_text(encoding="utf-8")
    current_agents = AGENTS.read_text(encoding="utf-8")
    preserved_tail_marker = "- **Dual-Tier Data Preservation & Incremental Discipline:**"
    check("agents_only_opening_scope_changed", previous_agents.split(preserved_tail_marker, 1)[1] == current_agents.split(preserved_tail_marker, 1)[1], "All content from dual-tier preservation onward is unchanged")

    authored = [PLAN, RESOURCES, COMPANION, AGENTS, NOTES]
    broken_links = []
    checked_links = 0
    for path in authored:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[ \t]*$", "", text)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            local = unquote(target.split("#", 1)[0]).strip("<>")
            if not local:
                continue
            checked_links += 1
            if not (path.parent / local).exists():
                broken_links.append({"source": path.relative_to(ROOT).as_posix(), "target": target})
    check("authored_local_links", not broken_links, {"checked": checked_links, "broken": broken_links})
    task_root = EVIDENCE.parent
    check("canonical_task_bundle_shape", {p.name for p in task_root.iterdir()} == {"README.md", "evidence", "superpowers"} and {p.name for p in (task_root / "superpowers").iterdir()} == {"spec.md", "plan.md"}, "Task bundle already supplied by parent; no parallel planning tree")

    result = {"verified_on": "2026-11-17", "scope": "Documentation arithmetic, task traceability, local links, exact source archives and limited AGENTS edit. No product accuracy, human availability, provider, hosting or gate acceptance is inferred.", "checks": checks, "result": "PASS" if all(c["result"] == "PASS" for c in checks) else "FAIL", "authored_document_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in [PLAN, RESOURCES, COMPANION, AGENTS, ALLOCATION, NOTES]}}
    output = EVIDENCE / "plan-rewrite-verification.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": result["result"], "checks": len(checks), "failures": [c["name"] for c in checks if c["result"] != "PASS"], "totals": totals, "output": output.relative_to(ROOT).as_posix()}))
    raise SystemExit(0 if result["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
