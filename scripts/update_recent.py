#!/usr/bin/env python3
"""Update gov-org-history only when recent source data changed.

The regular fetch scripts include fetched_at/generated_at fields. This wrapper
generates a fresh copy in a temporary directory, compares data while ignoring
those volatile fields, and copies changed outputs back only when meaningful
content changed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


VOLATILE_KEYS = {"fetched_at", "generated_at"}


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: strip_volatile(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [strip_volatile(v) for v in value]
    return value


def json_equal(left: Path, right: Path) -> bool:
    if not left.exists() or not right.exists():
        return left.exists() == right.exists()
    return strip_volatile(load_json(left)) == strip_volatile(load_json(right))


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def copy_file(src_root: Path, dst_root: Path, rel_path: str) -> None:
    src = src_root / rel_path
    dst = dst_root / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def sync_dir(src_root: Path, dst_root: Path, rel_path: str) -> None:
    src = src_root / rel_path
    dst = dst_root / rel_path
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst)


def snapshot_candidates(fresh_index: dict[str, Any], current_index: dict[str, Any], lookback_days: int) -> list[dict[str, Any]]:
    cutoff = date.today() - timedelta(days=lookback_days)
    fresh_records = fresh_index.get("fetched_snapshots", [])
    existing_dates = {item.get("effective_date") for item in current_index.get("fetched_snapshots", [])}
    parsed_dates = [parse_date(item.get("effective_date", "")) for item in fresh_records]
    latest = max((item for item in parsed_dates if item is not None), default=None)

    candidates = []
    for record in fresh_records:
        effective_date = record.get("effective_date")
        parsed = parse_date(effective_date)
        is_new = effective_date not in existing_dates
        is_recent = parsed is not None and parsed >= cutoff
        is_latest = latest is not None and parsed == latest
        if is_new or is_recent or is_latest:
            candidates.append(record)
    return candidates


def build_fresh_tree(repo: Path, tmp: Path) -> None:
    scripts = repo / "scripts"
    run([sys.executable, str(scripts / "fetch_gvrn_org.py"), "--out", str(tmp), "--all"], repo)
    run([sys.executable, str(scripts / "fetch_institution_list.py"), "--out", str(tmp), "--write-html"], repo)
    run([sys.executable, str(scripts / "fetch_reference_lists.py"), "--out", str(tmp), "--write-html"], repo)
    run([sys.executable, str(scripts / "generate_metadata.py"), str(tmp)], repo)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=".", help="Repository root for gov-org-history.")
    parser.add_argument("--lookback-days", type=int, default=31)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(args.out).resolve()
    changed: list[str] = []

    with tempfile.TemporaryDirectory(prefix="gov-org-history-update-") as tmp_name:
        tmp = Path(tmp_name)
        build_fresh_tree(repo, tmp)

        fresh_index_path = tmp / "data/snapshots/index.json"
        current_index_path = repo / "data/snapshots/index.json"
        fresh_index = load_json(fresh_index_path, {})
        current_index = load_json(current_index_path, {})

        if not json_equal(fresh_index_path, current_index_path):
            changed.append("data/snapshots/index.json")

        if not json_equal(tmp / "sources/org-go-kr/efyd-list.json", repo / "sources/org-go-kr/efyd-list.json"):
            changed.append("sources/org-go-kr/efyd-list.json")

        changed_snapshots = []
        for record in snapshot_candidates(fresh_index, current_index, args.lookback_days):
            rel_path = record.get("path")
            if rel_path and not json_equal(tmp / rel_path, repo / rel_path):
                changed_snapshots.append(rel_path)
                date_part = record.get("effective_date")
                if date_part:
                    raw_rel = f"sources/org-go-kr/gvrn-org/{date_part}.json"
                    changed_snapshots.append(raw_rel)

        changed.extend(changed_snapshots)

        if changed_snapshots and not json_equal(
            tmp / "data/relations/reorganizations.json",
            repo / "data/relations/reorganizations.json",
        ):
            changed.append("data/relations/reorganizations.json")

        if not json_equal(tmp / "data/institutions/current.json", repo / "data/institutions/current.json"):
            changed.append("data/institutions/current.json")
            changed.append("sources/org-go-kr/institution-list")

        reference_pairs = [
            ("data/reference-files/library.json", "sources/org-go-kr/reference-library"),
            ("data/reference-files/admin-machinery-changes.json", "sources/org-go-kr/admin-machinery-changes"),
        ]
        for data_rel, source_rel in reference_pairs:
            if not json_equal(tmp / data_rel, repo / data_rel):
                changed.append(data_rel)
                changed.append(source_rel)

        if changed:
            changed.extend(["metadata.json", "stats.json"])

        unique_changed = []
        for rel_path in changed:
            if rel_path not in unique_changed:
                unique_changed.append(rel_path)

        if not unique_changed:
            print(f"No recent government-organization changes in the last {args.lookback_days} days.")
            return 0

        print("Detected government-organization updates:")
        for rel_path in unique_changed:
            print(f"- {rel_path}")

        if args.dry_run:
            return 0

        for rel_path in unique_changed:
            src = tmp / rel_path
            if src.is_dir():
                sync_dir(tmp, repo, rel_path)
            else:
                copy_file(tmp, repo, rel_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
