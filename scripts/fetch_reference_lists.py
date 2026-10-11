#!/usr/bin/env python3
"""Index auxiliary reference-file lists without downloading attachments."""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib import request


from source_http import read_source


BASE_URL = "https://org.go.kr"
LIBRARY_URL = BASE_URL + "/cop/bbs/selectArticleList.do?bbsId=BBSMSTR_400000010000"
CHANGE_URL = BASE_URL + "/orgnzt/chnge/viewAdmnstMach.do"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_text(url: str) -> str:
    req = request.Request(url, headers={"User-Agent": "gov-org-history/0.1"})
    return read_source(req).decode("utf-8")


class LibraryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, Any]] = []
        self.total_count: int | None = None
        self._current_tag: str | None = None
        self._current_attrs: dict[str, str] = {}
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self._current: dict[str, Any] | None = None
        self._plain_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._current_tag = tag
        self._current_attrs = {k: v or "" for k, v in attrs}
        if tag == "a":
            self._anchor_href = ";".join(
                value
                for value in [
                    self._current_attrs.get("href", ""),
                    self._current_attrs.get("onclick", ""),
                ]
                if value
            )
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        text = html.unescape(data).strip()
        if not text:
            return
        self._plain_text.append(text)
        if self._anchor_href is not None:
            self._anchor_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            href = self._anchor_href
            text = " ".join(self._anchor_text).strip()
            detail = re.search(r"fn_egov_bbs_detail\('([^']+)','([^']+)'\)", href)
            file_down = re.search(r"fn_egov_file_down\('([^']+)'\)", href)
            if detail and text:
                ntt_id, bbs_id = detail.group(1), detail.group(2)
                self._current = {
                    "title": text,
                    "ntt_id": ntt_id,
                    "bbs_id": bbs_id,
                    "detail_url": f"{BASE_URL}/cop/bbs/selectArticleDetail.do?nttId={ntt_id}&bbsId={bbs_id}",
                    "attachment_id": "",
                    "download_url": "",
                }
                self.records.append(self._current)
            elif file_down and self._current is not None:
                file_id = file_down.group(1)
                self._current["attachment_id"] = file_id
                self._current["download_url"] = f"{BASE_URL}/cmm/fms/FileDown.do?atchFileId={file_id}&fileSn=0"
            self._anchor_href = None
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


class ChangeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, str]] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self._section = ""
        self._current_heading = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        if tag == "div" and "tab-content" in attr.get("class", ""):
            self._section = attr.get("id", "")
        if tag == "a":
            self._anchor_href = attr.get("href", "")
            self._anchor_text = []
        if tag == "h3":
            self._anchor_href = None
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        text = html.unescape(data).strip()
        if not text:
            return
        if self._anchor_href is not None:
            self._anchor_text.append(text)
        else:
            self._current_heading = text if text.startswith("구분명") or text == "파일다운로드받기" else self._current_heading

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            href = self._anchor_href
            text = " ".join(self._anchor_text).strip()
            file_id_match = re.search(r"viewFile\('([^']+)'\)", href)
            if file_id_match and text:
                file_id = file_id_match.group(1)
                self.records.append(
                    {
                        "title": text,
                        "file_id": file_id,
                        "section": self._section,
                        "group": self._current_heading,
                        "download_url": f"{BASE_URL}/main/attach.do?item={file_id}",
                    }
                )
            self._anchor_href = None
            self._anchor_text = []


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch_library(out_dir: Path, pages: int, fetched_at: str, write_html: bool) -> None:
    records: list[dict[str, Any]] = []
    page_sources = []
    total_count = None
    for page in range(1, pages + 1):
        url = LIBRARY_URL if page == 1 else f"{LIBRARY_URL}&pageIndex={page}"
        source = fetch_text(url)
        if write_html:
            html_path = out_dir / f"sources/org-go-kr/reference-library/page-{page:02d}.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(source, encoding="utf-8")
        parser_obj = LibraryParser()
        parser_obj.feed(source)
        parser_obj.close()
        if parser_obj.total_count is not None:
            total_count = parser_obj.total_count
        records.extend(parser_obj.records)
        page_sources.append({"page": page, "url": url, "records": len(parser_obj.records)})
        print(f"fetched library page={page} records={len(parser_obj.records)}")

    write_json(
        out_dir / "data/reference-files/library.json",
        {
            "source": {
                "page_url": LIBRARY_URL,
                "fetched_at": fetched_at,
                "pages": page_sources,
                "total_count_reported": total_count,
            },
            "count": len(records),
            "records": records,
        },
    )


def fetch_changes(out_dir: Path, fetched_at: str, write_html: bool) -> None:
    source = fetch_text(CHANGE_URL)
    if write_html:
        html_path = out_dir / "sources/org-go-kr/admin-machinery-changes/page.html"
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(source, encoding="utf-8")
    parser_obj = ChangeParser()
    parser_obj.feed(source)
    parser_obj.close()
    write_json(
        out_dir / "data/reference-files/admin-machinery-changes.json",
        {
            "source": {
                "page_url": CHANGE_URL,
                "fetched_at": fetched_at,
            },
            "count": len(parser_obj.records),
            "records": parser_obj.records,
        },
    )
    print(f"fetched admin-machinery changes records={len(parser_obj.records)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=".", help="Repository root for gov-org-history.")
    parser.add_argument("--library-pages", type=int, default=13)
    parser.add_argument("--write-html", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    fetched_at = now_iso()
    fetch_library(out_dir, args.library_pages, fetched_at, args.write_html)
    fetch_changes(out_dir, fetched_at, args.write_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
