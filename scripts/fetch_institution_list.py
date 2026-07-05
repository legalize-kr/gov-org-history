#!/usr/bin/env python3
"""Fetch the institution-chart list from org.go.kr."""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib import parse, request


BASE_URL = "https://org.go.kr"
LIST_URL = BASE_URL + "/cop/bbs/getInstiChartList.do"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_text(url: str) -> str:
    req = request.Request(url, headers={"User-Agent": "gov-org-history/0.1"})
    with request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8")


def extract_js_arg(href: str, function_name: str) -> str | None:
    match = re.search(function_name + r"\('([^']+)'\)", href)
    return match.group(1) if match else None


def extract_open_detail(href: str) -> tuple[str, str, str] | None:
    match = re.search(r"openDetail\('([^']*)','([^']*)','([^']*)'\)", href)
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)


def parse_law_url(url: str) -> dict[str, str]:
    parsed = parse.urlsplit(url)
    parts = [parse.unquote(part) for part in parsed.path.split("/") if part]
    law_name = ""
    article = ""
    if "법령" in parts:
        idx = parts.index("법령")
        if len(parts) > idx + 1:
            law_name = parts[idx + 1]
        if len(parts) > idx + 2:
            article = parts[idx + 2]
    return {"url": url, "law_name": law_name, "article": article}


class InstitutionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, Any]] = []
        self.total_count: int | None = None
        self._current_tag: str | None = None
        self._current_attrs: dict[str, str] = {}
        self._anchor_href: str | None = None
        self._anchor_class: str = ""
        self._anchor_text: list[str] = []
        self._last_category = ""
        self._current: dict[str, Any] | None = None
        self._plain_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        self._current_tag = tag
        self._current_attrs = attr
        if tag == "a":
            self._anchor_href = attr.get("href", "")
            self._anchor_class = attr.get("class", "")
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        text = html.unescape(data).strip()
        if not text:
            return
        self._plain_text.append(text)
        if self._current_tag == "span" and "category" in self._current_attrs.get("class", ""):
            self._last_category = text
        if self._anchor_href is not None:
            self._anchor_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            href = self._anchor_href
            text = " ".join(self._anchor_text).strip()
            detail = extract_open_detail(href)
            if detail and "subject" in self._anchor_class:
                code_num, org_code, chart_id = detail
                self._current = {
                    "name": text,
                    "category": self._last_category,
                    "code_num": code_num,
                    "org_code": org_code,
                    "chart_id": chart_id,
                    "detail_url": (
                        f"{BASE_URL}/cop/bbs/getInstiChartDetail.do?"
                        f"codeNum={parse.quote(code_num)}&orgCode={org_code}&chartId={chart_id}"
                    ),
                    "installation_basis": [],
                    "related_laws": [],
                }
                self.records.append(self._current)
            elif self._current is not None and text in {"설치근거", "관련법령"}:
                link = extract_js_arg(href, "openLink")
                if link:
                    target = self._current["installation_basis"] if text == "설치근거" else self._current["related_laws"]
                    target.append({"label": text, **parse_law_url(link)})
            self._anchor_href = None
            self._anchor_class = ""
            self._anchor_text = []
        if tag == self._current_tag:
            self._current_tag = None
            self._current_attrs = {}

    def close(self) -> None:
        super().close()
        joined = " ".join(self._plain_text)
        match = re.search(r"총\s+(\d+)\s+건", joined)
        if match:
            self.total_count = int(match.group(1))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=".", help="Repository root for gov-org-history.")
    parser.add_argument("--pages", type=int, default=7, help="Number of list pages to scan.")
    parser.add_argument("--write-html", action="store_true", help="Preserve fetched HTML source pages.")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    fetched_at = now_iso()
    records: list[dict[str, Any]] = []
    total_count = None
    page_sources = []

    for page in range(1, args.pages + 1):
        url = LIST_URL if page == 1 else f"{LIST_URL}?pageIndex={page}"
        source = fetch_text(url)
        if args.write_html:
            (out_dir / "sources/org-go-kr/institution-list").mkdir(parents=True, exist_ok=True)
            (out_dir / f"sources/org-go-kr/institution-list/page-{page:02d}.html").write_text(source, encoding="utf-8")

        parser_obj = InstitutionParser()
        parser_obj.feed(source)
        parser_obj.close()
        if parser_obj.total_count is not None:
            total_count = parser_obj.total_count
        records.extend(parser_obj.records)
        page_sources.append({"page": page, "url": url, "records": len(parser_obj.records)})
        print(f"fetched institution page={page} records={len(parser_obj.records)}")

    deduped = {}
    for record in records:
        deduped[(record["org_code"], record["chart_id"])] = record

    result = {
        "source": {
            "site": "정부조직관리정보시스템",
            "page_url": LIST_URL,
            "fetched_at": fetched_at,
            "pages": page_sources,
            "total_count_reported": total_count,
        },
        "count": len(deduped),
        "organizations": [deduped[key] for key in sorted(deduped, key=lambda item: (item[1], item[0]))],
    }
    write_json(out_dir / "data/institutions/current.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
