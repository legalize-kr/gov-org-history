#!/usr/bin/env python3
"""Fetch government organization snapshots from org.go.kr.

The public page at /oam/gvrnOrgChartView.ifrm uses JSON POST endpoints.
This script preserves both the source JSON and a normalized snapshot format.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request


from source_http import read_source


BASE_URL = "https://org.go.kr"
REFERER = "https://org.go.kr/oam/gvrnOrgChartView.ifrm?flag=gov"
PAGE_NAME = "대국민서비스 기구도 조회"
DATE_ENDPOINT = "/oam/selectEfYdList.do"
SNAPSHOT_ENDPOINT = "/oam/selectGvrnOrgViewList.do"


REORGAN_TYPE_MAP = {
    "신설": "created",
    "승격": "promoted",
    "개편": "reorganized",
    "통합": "merged",
    "분리": "split",
    "폐지": "abolished",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def yyyymmdd_to_iso(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value)
    if value == "99991231":
        return None
    if len(value) != 8 or not value.isdigit():
        return value
    return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        BASE_URL + path,
        data=body,
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=UTF-8",
            "Referer": REFERER,
            "User-Agent": "gov-org-history/0.1",
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    return json.loads(read_source(req).decode("utf-8"))


def law_go_kr_url(law_name: str | None) -> str | None:
    if not law_name:
        return None
    return "https://www.law.go.kr/법령/" + law_name


def normalize_node(row: dict[str, Any]) -> dict[str, Any]:
    org_id = str(row.get("orgCode") or "")
    parent_id = str(row.get("upOrgCode") or "") or None
    if parent_id == org_id:
        parent_id = None

    root_id = row.get("rootOrgCode")
    root_id = str(root_id) if root_id not in (None, "") else None

    reorgan_code = row.get("reorganCode") or ""
    related_ref = row.get("relgoagCode") or ""

    law_name = row.get("lsNm") or None
    legal_basis = []
    if law_name:
        legal_basis.append(
            {
                "basis_type": "snapshot_law",
                "law_id": row.get("lsId") or None,
                "law_name": law_name,
                "effective_date": yyyymmdd_to_iso(row.get("lsiEfYd")),
                "law_go_kr_url": law_go_kr_url(law_name),
                "source_field": "lsNm",
            }
        )

    return {
        "id": org_id,
        "name": row.get("orgNm") or "",
        "full_name": row.get("orgFullNm") or "",
        "abbreviation": row.get("orgAbrv") or "",
        "english_name": row.get("engNm") or "",
        "english_abbreviation": row.get("engAbrv") or "",
        "parent_id": parent_id,
        "root_id": root_id,
        "valid_from": yyyymmdd_to_iso(row.get("efYd")),
        "valid_to": yyyymmdd_to_iso(row.get("edYd")),
        "display": {
            "rank_no": row.get("rankNo") or "",
            "level": row.get("orgLevel") or "",
            "template": row.get("orgTmplType") or "",
            "shown_in_chart": row.get("indictAt") or "",
        },
        "classification": {
            "large": row.get("orgTypeLclas") or "",
            "medium": row.get("orgTypeMlsfc") or "",
            "small": row.get("orgTypeSclas") or "",
            "chief_grade_code": row.get("clssCode") or "",
            "independent": row.get("indpInsttYn") or "",
        },
        "legal_basis": legal_basis,
        "reorganization": {
            "source_value": reorgan_code,
            "type": REORGAN_TYPE_MAP.get(reorgan_code, "none" if not reorgan_code else "other"),
            "related_ref": str(related_ref) if related_ref not in (None, "") else "",
        },
        "source_fields": {
            "gvrnNo": row.get("gvrnNo"),
            "orgEsntlCode": row.get("orgEsntlCode"),
            "lsiSeq": row.get("lsiSeq"),
            "lsId": row.get("lsId"),
            "lsNm": row.get("lsNm"),
            "lsiEfYd": row.get("lsiEfYd"),
            "efGubun": row.get("efGubun"),
            "orgCode": row.get("orgCode"),
            "upOrgCode": row.get("upOrgCode"),
            "rootOrgCode": row.get("rootOrgCode"),
            "efYd": row.get("efYd"),
            "edYd": row.get("edYd"),
            "reorganCode": row.get("reorganCode"),
            "relgoagCode": row.get("relgoagCode"),
        },
    }


def make_snapshot(date_code: str, date_label: str | None, source: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    rows = source.get("data") or []
    date_iso = yyyymmdd_to_iso(date_code)
    nodes = [normalize_node(row) for row in rows]
    return {
        "snapshot_id": f"gvrn-{date_iso}",
        "effective_date": date_iso,
        "source": {
            "site": "정부조직관리정보시스템",
            "page_url": REFERER,
            "endpoint": BASE_URL + SNAPSHOT_ENDPOINT,
            "date_endpoint": BASE_URL + DATE_ENDPOINT,
            "request_payload": {"pageName": PAGE_NAME, "efYd": date_code},
            "source_date_code": date_code,
            "source_date_label": date_label,
            "fetched_at": fetched_at,
        },
        "node_count": len(nodes),
        "nodes": nodes,
    }


def reorg_edges_for_snapshot(snapshot: dict[str, Any], snapshot_path: str) -> list[dict[str, Any]]:
    edges = []
    for node in snapshot["nodes"]:
        reorg = node.get("reorganization") or {}
        source_value = reorg.get("source_value") or ""
        if not source_value:
            continue
        edges.append(
            {
                "effective_date": snapshot["effective_date"],
                "type": reorg.get("type") or "other",
                "source_value": source_value,
                "source_ref": reorg.get("related_ref") or "",
                "target_org_id": node["id"],
                "target_name": node["name"],
                "evidence": {
                    "field": "reorganCode",
                    "related_field": "relgoagCode",
                    "snapshot": snapshot_path,
                },
            }
        )
    return edges


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_date_index(out_dir: Path, fetched_at: str) -> list[dict[str, Any]]:
    source = post_json(DATE_ENDPOINT, {})
    raw = {
        "source": {
            "endpoint": BASE_URL + DATE_ENDPOINT,
            "request_payload": {},
            "fetched_at": fetched_at,
        },
        "response": source,
    }
    write_json(out_dir / "sources/org-go-kr/efyd-list.json", raw)

    dates = source.get("data") or []
    normalized = []
    for item in dates:
        cd = str(item.get("cd") or "")
        normalized.append(
            {
                "date_code": cd,
                "effective_date": yyyymmdd_to_iso(cd),
                "label": item.get("nm") or "",
                "source": item,
            }
        )

    existing = load_json(out_dir / "data/snapshots/index.json", {})
    fetched = existing.get("fetched_snapshots", [])
    write_json(
        out_dir / "data/snapshots/index.json",
        {
            "source": {
                "endpoint": BASE_URL + DATE_ENDPOINT,
                "fetched_at": fetched_at,
            },
            "available_dates": normalized,
            "fetched_snapshots": fetched,
        },
    )
    return normalized


def update_snapshot_index(out_dir: Path, fetched_records: list[dict[str, Any]]) -> None:
    index_path = out_dir / "data/snapshots/index.json"
    index = load_json(index_path, {"available_dates": [], "fetched_snapshots": []})
    by_date = {item["effective_date"]: item for item in index.get("fetched_snapshots", [])}
    for item in fetched_records:
        by_date[item["effective_date"]] = item
    index["fetched_snapshots"] = [by_date[key] for key in sorted(by_date)]
    write_json(index_path, index)


def update_reorganizations(out_dir: Path, all_edges: list[dict[str, Any]], fetched_at: str) -> None:
    path = out_dir / "data/relations/reorganizations.json"
    existing = load_json(path, {"edges": []})
    by_key = {
        (
            item.get("effective_date"),
            item.get("target_org_id"),
            item.get("source_value"),
            item.get("source_ref"),
        ): item
        for item in existing.get("edges", [])
    }
    for item in all_edges:
        by_key[
            (
                item.get("effective_date"),
                item.get("target_org_id"),
                item.get("source_value"),
                item.get("source_ref"),
            )
        ] = item

    write_json(
        path,
        {
            "generated_at": fetched_at,
            "description": "Edges derived from org.go.kr reorganCode and relgoagCode fields.",
            "edges": [by_key[key] for key in sorted(by_key)],
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=".", help="Repository root for gov-org-history.")
    parser.add_argument("--date", help="YYYYMMDD date code. Defaults to the first available date.")
    parser.add_argument("--all", action="store_true", help="Fetch all available government-organization snapshots.")
    parser.add_argument("--limit", type=int, help="Limit the number of snapshots when used with --all.")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    fetched_at = now_iso()
    dates = fetch_date_index(out_dir, fetched_at)
    if not dates:
        print("No effective dates returned.", file=sys.stderr)
        return 1

    if args.all:
        selected = dates[: args.limit] if args.limit else dates
    else:
        date_code = args.date or dates[0]["date_code"]
        selected = [item for item in dates if item["date_code"] == date_code]
        if not selected:
            selected = [{"date_code": date_code, "effective_date": yyyymmdd_to_iso(date_code), "label": None}]

    fetched_records: list[dict[str, Any]] = []
    all_edges: list[dict[str, Any]] = []

    for item in selected:
        date_code = item["date_code"]
        source = post_json(SNAPSHOT_ENDPOINT, {"pageName": PAGE_NAME, "efYd": date_code})
        date_iso = yyyymmdd_to_iso(date_code)
        raw_path = out_dir / f"sources/org-go-kr/gvrn-org/{date_iso}.json"
        write_json(
            raw_path,
            {
                "source": {
                    "endpoint": BASE_URL + SNAPSHOT_ENDPOINT,
                    "request_payload": {"pageName": PAGE_NAME, "efYd": date_code},
                    "fetched_at": fetched_at,
                },
                "response": source,
            },
        )

        snapshot = make_snapshot(date_code, item.get("label"), source, fetched_at)
        snapshot_rel_path = f"data/snapshots/{date_iso}/snapshot.json"
        write_json(out_dir / snapshot_rel_path, snapshot)
        fetched_records.append(
            {
                "effective_date": date_iso,
                "date_code": date_code,
                "label": item.get("label"),
                "path": snapshot_rel_path,
                "node_count": snapshot["node_count"],
            }
        )
        all_edges.extend(reorg_edges_for_snapshot(snapshot, snapshot_rel_path))
        print(f"fetched {date_code} nodes={snapshot['node_count']}")

    update_snapshot_index(out_dir, fetched_records)
    update_reorganizations(out_dir, all_edges, fetched_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
