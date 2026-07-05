#!/usr/bin/env python3
"""Generate repository-level metadata and stats."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()

    snapshot_index = load_json(repo / "data/snapshots/index.json", {})
    institutions = load_json(repo / "data/institutions/current.json", {})
    reorgs = load_json(repo / "data/relations/reorganizations.json", {})
    library = load_json(repo / "data/reference-files/library.json", {})
    changes = load_json(repo / "data/reference-files/admin-machinery-changes.json", {})

    fetched_snapshots = snapshot_index.get("fetched_snapshots", [])
    available_dates = snapshot_index.get("available_dates", [])
    snapshot_node_counts = [item.get("node_count", 0) for item in fetched_snapshots]

    stats = {
        "available_snapshot_dates": len(available_dates),
        "fetched_snapshots": len(fetched_snapshots),
        "snapshot_nodes_min": min(snapshot_node_counts) if snapshot_node_counts else 0,
        "snapshot_nodes_max": max(snapshot_node_counts) if snapshot_node_counts else 0,
        "current_institutions": institutions.get("count", 0),
        "reorganization_edges": len(reorgs.get("edges", [])),
        "reference_library_records": library.get("count", 0),
        "admin_machinery_change_files": changes.get("count", 0),
    }
    write_json(repo / "stats.json", stats)

    metadata = {
        "name": "gov-org-history",
        "description": "Korean government organization chart snapshots, institution legal bases, and reorganization edges.",
        "generated_at": now_iso(),
        "sources": [
            "https://org.go.kr/oam/gvrnOrgChartView.ifrm?flag=gov",
            "https://org.go.kr/oam/selectGvrnOrgViewList.do",
            "https://org.go.kr/cop/bbs/getInstiChartList.do",
            "https://www.org.go.kr/cop/bbs/selectArticleList.do?bbsId=BBSMSTR_400000010000",
            "https://org.go.kr/orgnzt/chnge/viewAdmnstMach.do",
        ],
        "stats": stats,
    }
    write_json(repo / "metadata.json", metadata)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
