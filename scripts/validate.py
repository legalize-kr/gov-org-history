#!/usr/bin/env python3
"""Validate gov-org-history repository structure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_snapshot(path: Path, errors: list[str]) -> None:
    snapshot = load_json(path)
    nodes = snapshot.get("nodes", [])
    ids = [node.get("id") for node in nodes]
    id_set = set(ids)
    if len(ids) != len(id_set):
        fail(errors, f"{path}: duplicate node id")
    if snapshot.get("node_count") != len(nodes):
        fail(errors, f"{path}: node_count mismatch")

    for node in nodes:
        node_id = node.get("id")
        if not node_id:
            fail(errors, f"{path}: node without id")
        if not node.get("name"):
            fail(errors, f"{path}: node {node_id} without name")
        parent_id = node.get("parent_id")
        if parent_id and parent_id not in id_set:
            fail(errors, f"{path}: node {node_id} missing parent {parent_id}")
        if not node.get("legal_basis"):
            fail(errors, f"{path}: node {node_id} without legal_basis")


def validate_institutions(repo: Path, errors: list[str]) -> None:
    path = repo / "data/institutions/current.json"
    if not path.exists():
        fail(errors, f"{path}: missing")
        return
    data = load_json(path)
    records = data.get("organizations", [])
    if data.get("count") != len(records):
        fail(errors, f"{path}: count mismatch")
    seen = set()
    for record in records:
        key = (record.get("org_code"), record.get("chart_id"))
        if key in seen:
            fail(errors, f"{path}: duplicate institution {key}")
        seen.add(key)
        if not record.get("installation_basis"):
            fail(errors, f"{path}: {record.get('name')} missing installation_basis")
        if not record.get("related_laws"):
            fail(errors, f"{path}: {record.get('name')} missing related_laws")


def validate_reorganizations(repo: Path, errors: list[str]) -> None:
    path = repo / "data/relations/reorganizations.json"
    if not path.exists():
        fail(errors, f"{path}: missing")
        return
    data = load_json(path)
    for edge in data.get("edges", []):
        if not edge.get("effective_date"):
            fail(errors, f"{path}: edge without effective_date")
        if not edge.get("target_org_id"):
            fail(errors, f"{path}: edge without target_org_id")
        if not edge.get("source_value"):
            fail(errors, f"{path}: edge without source_value")


def validate_reference_files(repo: Path, errors: list[str]) -> None:
    for rel_path in [
        "data/reference-files/library.json",
        "data/reference-files/admin-machinery-changes.json",
    ]:
        path = repo / rel_path
        if not path.exists():
            fail(errors, f"{path}: missing")
            continue
        data = load_json(path)
        if data.get("count") != len(data.get("records", [])):
            fail(errors, f"{path}: count mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    errors: list[str] = []

    if not (repo / "README.md").exists():
        fail(errors, "README.md missing")

    snapshot_paths = sorted((repo / "data/snapshots").glob("*/snapshot.json"))
    if not snapshot_paths:
        fail(errors, "no snapshot files")
    for path in snapshot_paths:
        validate_snapshot(path, errors)

    validate_institutions(repo, errors)
    validate_reorganizations(repo, errors)
    validate_reference_files(repo, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"validated snapshots={len(snapshot_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
