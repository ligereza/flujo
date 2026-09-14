#!/usr/bin/env python3
"""Source acquisition with explicit discovery, capture, and provenance.

The research loop used to treat a search result as if it were already a
readable source.  That is not true for PDFs, dynamic pages, blocked requests,
or search snippets.  This module keeps those stages separate and preserves the
state of each URL so a later model cannot turn an incomplete crawl into a
confident report.

Backends are deliberately optional.  Firecrawl is used when its API key is
available, Crawl4AI when it is installed locally, and the bounded stdlib
extractor remains an explicit fallback.  Every fallback is recorded in the
capture record; it is never represented as a successful Firecrawl crawl.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
from html.parser import HTMLParser
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import urllib.error
import urllib.request


DEFAULT_MAX_BYTES = 25 * 1024 * 1024
DEFAULT_TIMEOUT = 45
FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"


def canonical_url(value: str) -> str:
    """Normalize a public URL without changing its meaningful query fields."""
    parts = urlsplit(str(value or "").strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path,
                       query, ""))


def source_id_for(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode("utf-8")).hexdigest()


def is_official_fondart_url(url: str) -> bool:
    host = (urlsplit(canonical_url(url)).hostname or "").lower()
    return host == "fondosdecultura.cl" or host.endswith(".fondosdecultura.cl")


def is_pdf_url(url: str, content_type: str = "") -> bool:
    return ("pdf" in (content_type or "").lower()
            or urlsplit(url).path.lower().endswith(".pdf"))


class _TextAndLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden = 0
        self.parts: list[str] = []
        self.links: list[str] = []
        self.link_records: list[dict[str, str]] = []
        self._anchor_href = ""
        self._anchor_parts: list[str] = []

    def _close_anchor(self) -> None:
        if self._anchor_href:
            self.link_records.append({
                "href": self._anchor_href,
                "title": re.sub(r"\s+", " ", " ".join(self._anchor_parts)).strip(),
            })
        self._anchor_href = ""
        self._anchor_parts = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._hidden += 1
        if tag.lower() == "a":
            self._close_anchor()
            href = dict(attrs).get("href")
            if href:
                self._anchor_href = href
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._hidden:
            self._hidden -= 1
        if tag.lower() == "a":
            self._close_anchor()

    def handle_data(self, data: str) -> None:
        if not self._hidden and data.strip():
            self.parts.append(data.strip())
            if self._anchor_href:
                self._anchor_parts.append(data.strip())

    def close(self) -> None:
        super().close()
        self._close_anchor()


def _html_payload(raw: bytes, base_url: str) -> tuple[str, list[str], list[dict[str, str]]]:
    parser = _TextAndLinks()
    parser.feed(raw.decode("utf-8", "replace"))
    parser.close()
    links: list[str] = []
    link_records: list[dict[str, str]] = []
    for record in parser.link_records:
        from urllib.parse import urljoin
        normalized = canonical_url(urljoin(base_url, html.unescape(record["href"])))
        if normalized and normalized not in links:
            links.append(normalized)
            link_records.append({"url": normalized, "title": record["title"]})
    return (re.sub(r"\s+", " ", " ".join(parser.parts)).strip(),
            links, link_records)


def extract_pdf_text(raw: bytes, *, timeout: int = 90) -> tuple[str, str]:
    """Return extractable PDF text and a machine-readable extraction error."""
    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(raw)
            path = handle.name
        result = subprocess.run(
            ["pdftotext", "-layout", path, "-"], capture_output=True,
            text=True, timeout=timeout,
        )
        text = (result.stdout or "").strip()
        if text:
            return text, ""
        return "", "pdf_text_empty"
    except FileNotFoundError:
        try:
            text = _pypdf_extract(raw)
        except ImportError:
            return "", "pdf_text_backend_unavailable"
        except Exception as exc:  # malformed PDFs retain a precise failure
            return "", "pypdf_extract_error:%s" % type(exc).__name__
        return (text, "") if text else ("", "pdf_text_empty")
    except subprocess.TimeoutExpired:
        return "", "pdftotext_timeout"
    except OSError as exc:
        return "", "pdf_extract_error:%s" % type(exc).__name__
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


def _pypdf_extract(raw: bytes) -> str:
    """Extract PDF text through the optional cross-platform Python backend."""
    from pypdf import PdfReader  # type: ignore[import-not-found]
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def extract_pdf_tables(raw: bytes) -> tuple[list[dict[str, Any]], str]:
    """Extract table cells with their source page through an optional backend.

    Flat PDF text is sufficient for reading but can interleave visual columns.
    Table rows are therefore a separate capture artifact, never an inferred
    replacement for the PDF text or its source hash.
    """
    try:
        import pdfplumber  # type: ignore[import-not-found]
    except ImportError:
        return [], "pdfplumber_unavailable"
    try:
        tables: list[dict[str, Any]] = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                for rows in page.extract_tables():
                    normalized = [
                        [str(cell or "").strip() for cell in row]
                        for row in rows if isinstance(row, list)
                    ]
                    if normalized:
                        tables.append({"page": page_number, "rows": normalized})
        return tables, ""
    except Exception as exc:  # source capture remains usable through text
        return [], "pdfplumber_error:%s" % type(exc).__name__


def _urllib_capture(url: str, *, timeout: int, max_bytes: int,
                    opener: Callable[..., Any] = urllib.request.urlopen) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "FLUJO-research-source/1.0"})
    with opener(request, timeout=timeout) as response:
        content_type = str(response.headers.get("Content-Type") or "")
        final_url = canonical_url(response.geturl() or url)
        raw = response.read(max_bytes + 1)
        status = int(getattr(response, "status", 200) or 200)
    if len(raw) > max_bytes:
        raise ValueError("source_too_large")
    if is_pdf_url(final_url, content_type):
        text, error = extract_pdf_text(raw)
        tables, table_error = extract_pdf_tables(raw)
        links: list[str] = []
        link_records: list[dict[str, str]] = []
    else:
        text, links, link_records = _html_payload(raw, final_url)
        error = "" if text else "html_text_empty"
        tables, table_error = [], ""
    return {
        "url": final_url, "status": "captured" if text else "failed",
        "backend": "urllib", "http_status": status,
        "content_type": content_type, "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "text": text, "links": links, "link_records": link_records,
        "tables": tables, "error": error,
        "metadata": {"bytes": len(raw), "pdf_table_backend": "pdfplumber" if tables else "",
                     "pdf_table_error": table_error},
    }


def _firecrawl_capture(url: str, *, api_key: str, timeout: int,
                       request_json: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    response = request_json(
        FIRECRAWL_SCRAPE_URL,
        {"url": url, "formats": ["markdown", "links"]},
        {"Authorization": "Bearer " + api_key,
         "Content-Type": "application/json"}, timeout,
    )
    document = response.get("data", response)
    if not isinstance(document, dict):
        raise ValueError("firecrawl_invalid_response")
    text = str(document.get("markdown") or document.get("content") or "").strip()
    metadata = document.get("metadata") or {}
    final_url = canonical_url(str(metadata.get("sourceURL") or
                                    metadata.get("url") or url))
    links = []
    for item in document.get("links") or []:
        value = item.get("url") if isinstance(item, dict) else item
        normalized = canonical_url(str(value or ""))
        if normalized and normalized not in links:
            links.append(normalized)
    return {
        "url": final_url, "status": "captured" if text else "failed",
        "backend": "firecrawl", "http_status": int(metadata.get("statusCode") or 200),
        "content_type": str(metadata.get("contentType") or "text/markdown"),
        "raw_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text, "links": links,
        "link_records": [],
        "error": "" if text else "firecrawl_text_empty", "metadata": metadata,
    }


async def _crawl4ai_async(url: str) -> dict[str, Any]:
    from crawl4ai import AsyncWebCrawler  # type: ignore[import-not-found]
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
    markdown = getattr(result, "markdown", "")
    if not isinstance(markdown, str):
        markdown = getattr(markdown, "raw_markdown", "")
    links_obj = getattr(result, "links", {}) or {}
    values = links_obj.values() if isinstance(links_obj, dict) else links_obj
    links: list[str] = []
    for item in values or []:
        value = item.get("href") if isinstance(item, dict) else item
        normalized = canonical_url(str(value or ""))
        if normalized and normalized not in links:
            links.append(normalized)
    final_url = canonical_url(str(getattr(result, "url", "") or url))
    text = str(markdown or "").strip()
    return {
        "url": final_url, "status": "captured" if text else "failed",
        "backend": "crawl4ai", "http_status": 200,
        "content_type": "text/markdown",
        "raw_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text, "links": links,
        "link_records": [],
        "error": "" if text else "crawl4ai_text_empty", "metadata": {},
    }


def _request_json(url: str, body: dict[str, Any], headers: dict[str, str],
                  timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def available_backends(env: dict[str, str] | None = None) -> dict[str, bool]:
    env = os.environ if env is None else env
    return {
        "firecrawl": bool(env.get("FIRECRAWL_API_KEY")),
        "crawl4ai": importlib.util.find_spec("crawl4ai") is not None,
        "urllib": True,
    }


def capture_url(url: str, *, backend: str = "auto", timeout: int = DEFAULT_TIMEOUT,
                max_bytes: int = DEFAULT_MAX_BYTES, env: dict[str, str] | None = None,
                opener: Callable[..., Any] = urllib.request.urlopen,
                request_json: Callable[..., dict[str, Any]] = _request_json,
                crawl4ai_runner: Callable[[str], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Capture one public URL with transparent backend fallback evidence."""
    normalized = canonical_url(url)
    if not normalized:
        return {"url": str(url or ""), "status": "failed", "backend": "none",
                "error": "invalid_public_url", "attempts": [], "text": "", "links": []}
    env = os.environ if env is None else env
    availability = available_backends(env)
    if backend not in {"auto", "firecrawl", "crawl4ai", "urllib"}:
        return {"url": normalized, "status": "failed", "backend": "none",
                "error": "unknown_backend", "attempts": [], "text": "", "links": []}
    order = ([backend] if backend != "auto" else
             [name for name in ("firecrawl", "crawl4ai", "urllib") if availability[name]])
    attempts: list[dict[str, str]] = []
    for name in order:
        try:
            if name == "firecrawl":
                result = _firecrawl_capture(
                    normalized, api_key=str(env.get("FIRECRAWL_API_KEY") or ""),
                    timeout=timeout, request_json=request_json)
            elif name == "crawl4ai":
                result = (crawl4ai_runner(normalized) if crawl4ai_runner else
                          asyncio.run(_crawl4ai_async(normalized)))
            else:
                result = _urllib_capture(normalized, timeout=timeout,
                                         max_bytes=max_bytes, opener=opener)
            attempts.append({"backend": name, "status": str(result.get("status"))})
            result["attempts"] = attempts
            if result.get("status") == "captured":
                return result
            attempts[-1]["error"] = str(result.get("error") or "empty_capture")
        except Exception as exc:  # backend error becomes source evidence
            attempts.append({"backend": name, "status": "failed",
                             "error": "%s:%s" % (type(exc).__name__, str(exc)[:160])})
    return {"url": normalized, "status": "failed", "backend": "none",
            "error": attempts[-1].get("error", "capture_failed") if attempts else
            "backend_unavailable", "attempts": attempts, "text": "", "links": []}


def discover_urls(query: str, search: Callable[..., dict[str, Any]], *,
                  max_results: int = 10) -> list[dict[str, Any]]:
    """Persistable search candidates; discovery is not yet a source capture."""
    response = search(query, max_results=max_results)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rank, item in enumerate(response.get("results") or [], 1):
        url = canonical_url(str(item.get("url") or ""))
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append({"query": query, "rank": rank, "url": url,
                     "title": str(item.get("title") or ""),
                     "snippet": str(item.get("content") or ""),
                     "search_backend": str(response.get("motor") or "")})
    return rows


class SourceCorpusStore:
    """Small SQLite provenance store for any URL-based research project."""
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts = self.root / "captures"
        self.artifacts.mkdir(exist_ok=True)
        self.db_path = self.root / "sources.sqlite"
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS source_discoveries (
                    query TEXT NOT NULL, canonical_url TEXT NOT NULL,
                    rank INTEGER NOT NULL, title TEXT NOT NULL, snippet TEXT NOT NULL,
                    search_backend TEXT NOT NULL, discovered_at TEXT NOT NULL,
                    PRIMARY KEY (query, canonical_url)
                );
                CREATE TABLE IF NOT EXISTS source_captures (
                    capture_id TEXT PRIMARY KEY, canonical_url TEXT NOT NULL,
                    source_id TEXT NOT NULL, requested_backend TEXT NOT NULL,
                    used_backend TEXT NOT NULL, status TEXT NOT NULL,
                    http_status INTEGER, content_type TEXT NOT NULL,
                    raw_sha256 TEXT NOT NULL, text_sha256 TEXT NOT NULL,
                    text_path TEXT, retrieved_at TEXT NOT NULL, error TEXT NOT NULL,
                    attempts_json TEXT NOT NULL, metadata_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_source_captures_url
                    ON source_captures(canonical_url, retrieved_at);
            """)

    def record_discovery(self, rows: list[dict[str, Any]]) -> int:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._connect() as conn:
            for row in rows:
                conn.execute("""
                    INSERT OR REPLACE INTO source_discoveries
                    (query, canonical_url, rank, title, snippet, search_backend, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row["query"], row["url"], int(row["rank"]), row["title"],
                      row["snippet"], row["search_backend"], now))
        return len(rows)

    def record_capture(self, result: dict[str, Any], *, requested_backend: str = "auto") -> dict[str, Any]:
        url = canonical_url(str(result.get("url") or ""))
        text = str(result.get("text") or "")
        raw_hash = str(result.get("raw_sha256") or "")
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        capture_id = hashlib.sha256((url + "\n" + raw_hash + "\n" + text_hash).encode("utf-8")).hexdigest()
        path = ""
        if text:
            path = str(self.artifacts / (capture_id + ".txt"))
            Path(path).write_text(text, encoding="utf-8")
        metadata = dict(result.get("metadata") or {})
        metadata["links"] = list(result.get("links") or [])
        metadata["link_records"] = list(result.get("link_records") or [])
        tables = result.get("tables") if isinstance(result.get("tables"), list) else []
        if tables:
            table_bytes = json.dumps(tables, ensure_ascii=False, sort_keys=True).encode("utf-8")
            table_path = self.artifacts / (capture_id + ".tables.json")
            table_path.write_bytes(table_bytes)
            metadata["table_path"] = str(table_path)
            metadata["table_sha256"] = hashlib.sha256(table_bytes).hexdigest()
            metadata["table_count"] = len(tables)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO source_captures
                (capture_id, canonical_url, source_id, requested_backend, used_backend,
                 status, http_status, content_type, raw_sha256, text_sha256, text_path,
                 retrieved_at, error, attempts_json, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (capture_id, url, source_id_for(url), requested_backend,
                  str(result.get("backend") or "none"), str(result.get("status") or "failed"),
                  result.get("http_status"), str(result.get("content_type") or ""), raw_hash,
                  text_hash, path or None, now, str(result.get("error") or ""),
                  json.dumps(result.get("attempts") or [], ensure_ascii=False),
                  json.dumps(metadata, ensure_ascii=False)))
        return {"capture_id": capture_id, "source_id": source_id_for(url),
                "text_path": path, "status": result.get("status"), "url": url}

    def summary(self) -> dict[str, int]:
        with self._connect() as conn:
            discovered = conn.execute("SELECT COUNT(*) FROM source_discoveries").fetchone()[0]
            captured = conn.execute("SELECT COUNT(*) FROM source_captures WHERE status='captured'").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM source_captures WHERE status!='captured'").fetchone()[0]
        return {"discovered": int(discovered), "captured": int(captured), "failed": int(failed)}


def import_crawl4ai_export(path: str | Path, store: SourceCorpusStore) -> dict[str, int]:
    """Import a prior Crawl4AI batch without pretending it was recrawled now.

    The recovered Fondart batch already has a useful, literal contract:
    ``batch_id``, capture timestamp, browser, interpretation boundary, and
    result-level Markdown/error.  Reusing that evidence avoids a second crawl
    and keeps the original capture separate from a later normalization pass.
    """
    source_path = Path(path).expanduser()
    raw = source_path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("invalid_crawl4ai_export")
    export_hash = hashlib.sha256(raw).hexdigest()
    captured = failed = 0
    for item in data["results"]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("markdown") or "")
        success = bool(item.get("success")) and bool(text)
        receipt = store.record_capture({
            "url": str(item.get("url") or ""),
            "status": "captured" if success else "failed",
            "backend": "crawl4ai_import",
            "http_status": 200 if success else None,
            "content_type": "text/markdown",
            "raw_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "text": text,
            "links": [],
            "error": "" if success else str(item.get("error_message") or "crawl4ai_result_failed"),
            "metadata": {
                "imported_from": str(source_path), "export_sha256": export_hash,
                "batch_id": data.get("batch_id"), "captured_at_utc": data.get("captured_at_utc"),
                "crawler": data.get("crawler"), "browser": data.get("browser"),
                "interpretation": data.get("interpretation"),
            },
        }, requested_backend="crawl4ai_import")
        if receipt["status"] == "captured":
            captured += 1
        else:
            failed += 1
    return {"captured": captured, "failed": failed}
