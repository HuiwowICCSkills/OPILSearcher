#!/usr/bin/env python3
"""Oxford Public International Law (OPIL) adapter for OPILSearcher."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from skillkit import HTTP, RetrievalError, clean, pdf_pages, result, snippet

PROG = "opil_search.py"
DESCRIPTION = "Search the Oxford Public International Law platform (MPIL and ORIL products)."
CACHE_DEFAULT = ".opil-cache"
FETCH_TIMEOUT_DEFAULT = 300

SEARCH_URL = "https://opil.ouplaw.com/search"
CONTENT_SELECTOR = "#mainContent"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/155.0.0.0 Safari/537.36"
)

PRODUCTS: dict[str, dict[str, Any]] = {
    "mpil": {
        "name": "Max Planck Encyclopedia of Public International Law (MPIL)",
        "facets": {
            "prd": "MPEIPRO",
            "pc_4": "8d0b332e-2099-487f-b6ce-253d8c6ce8a0",
        },
        "extra_params": {"access": "all", "level": "all"},
        "expected_product": "Max Planck Encyclopedias of International Law [MPIL]",
        "home": "https://opil.ouplaw.com/home/MPIL",
    },
    "oril": {
        "name": "Oxford Reports on International Law (ORIL)",
        "facets": {"pc_17": "bdcb8d33-0914-4cd9-bd2b-c84ac21665f7"},
        "extra_params": {},
        "expected_product": "Oxford Reports on International Law [ORIL]",
        "home": "https://opil.ouplaw.com/home/ORIL",
    },
    "oril-icl": {
        "name": "Oxford Reports on International Law: International Criminal Law (ORIL-ICL)",
        "facets": {"pc_32": "68306099-6983-4cb7-a931-60f851434432"},
        "extra_params": {},
        "expected_product": "Oxford Reports on International Law [ORIL]",
        "home": "https://opil.ouplaw.com/home/ORIL",
    },
}


def _headers() -> dict[str, str]:
    return {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def make_http(args: argparse.Namespace) -> HTTP:
    return HTTP(
        args.cache,
        offline=args.offline,
        ttl=args.cache_ttl,
        timeout=args.timeout,
        cookie_jar=Path(args.cache) / "opil.cookies.txt",
        user_agent=UA,
        min_interval=2.0,
    )


def _warm(http: HTTP, product: str) -> None:
    """Complete the publisher's redirect handshake before a facet search."""
    warmed = getattr(http, "_opil_warmed", set())
    if product in warmed:
        return
    for url in ("https://opil.ouplaw.com/", PRODUCTS[product]["home"]):
        try:
            http.get(url, headers=_headers())
        except RetrievalError:
            continue
    warmed.add(product)
    http._opil_warmed = warmed  # type: ignore[attr-defined]


def add_search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--product",
        choices=sorted(PRODUCTS),
        default="mpil",
        help="OPIL product profile: mpil, oril, or oril-icl",
    )
    parser.add_argument("--limit", type=int, default=10, help="1..50 (default 10)")
    parser.add_argument("--offset", type=int, default=0, help=">= 0 (default 0)")
    parser.add_argument(
        "--year-from",
        dest="year_from",
        help="Publication-date lower bound, four-digit year (e.g. 2010)",
    )
    parser.add_argument(
        "--year-to",
        dest="year_to",
        help="Publication-date upper bound, four-digit year (e.g. 2020)",
    )


def add_fetch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--text-out", help="Write extracted page text here")
    parser.add_argument("--max-mb", type=int, default=50, help="Maximum response size in MiB")


def search(query: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("A non-empty query is required")
    if not 1 <= args.limit <= 50:
        raise ValueError("limit must be 1..50")
    if args.offset < 0:
        raise ValueError("offset must be >= 0")

    product = args.product
    cfg = PRODUCTS[product]
    _warm(http, product)
    page_size = 50 if args.limit > 20 else 20
    page = args.offset // page_size + 1
    within = args.offset % page_size
    params: dict[str, Any] = {
        "sfam": "",
        "q": query,
        "pageSize": page_size,
        "sort": "relevance",
        "page": page,
    }
    if getattr(args, "year_from", None):
        params["fromDate"] = str(args.year_from)
    if getattr(args, "year_to", None):
        params["toDate"] = str(args.year_to)
    params.update(cfg["facets"])
    params.update(cfg["extra_params"])

    try:
        soup, meta = http.soup(SEARCH_URL, params, headers=_headers())
    except RetrievalError:
        if not http.forget_session_cookies():
            raise
        http._opil_warmed = set()  # type: ignore[attr-defined]
        _warm(http, product)
        soup, meta = http.soup(SEARCH_URL, params, headers=_headers())

    text = soup.get_text(" ", strip=True)
    total_match = re.search(
        r"You are looking at\s+[\d,]+\s*[\u2013\u2014-]\s*[\d,]+\s+of\s+([\d,]+)\s+results",
        text,
    )
    blocks = soup.select("div.contentItem")
    if not blocks and not total_match:
        raise RetrievalError(
            "OPIL search page carried neither results nor a result count; "
            "access challenge or schema change, not zero results"
        )
    total = int(total_match.group(1).replace(",", "")) if total_match else None

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block in blocks:
        heading = block.select_one("h2.itemTitle a[href]")
        if not heading:
            raise RetrievalError("OPIL result block has no title link; schema change")
        target = urljoin(meta["source_url"], heading["href"])
        if target in seen:
            continue
        seen.add(target)
        fields: dict[str, str] = {}
        for definition in block.select("dl.metadata"):
            labels = definition.select("dt")
            values = definition.select("dd")
            for label, value in zip(labels, values):
                fields.setdefault(clean(label.get_text()), clean(value.get_text()))
        author = block.select_one("div.itemAuthor")
        excerpt = block.select_one("div.component-content-summary, div.excerpt")
        classes = block.get("class") or []
        if "hasAccess" in classes:
            access = "entry page readable in this session"
        elif "locked" in classes:
            access = "no full-text entitlement in this session; the entry page may hold only the headnote"
        else:
            access = "access not stated by the result row"
        core = fields.get("Core Issue(s)", "")
        rows.append(
            result(
                heading.get_text(" ", strip=True),
                target,
                "opil-" + product + "-search",
                snippet((excerpt.get_text(" ", strip=True) if excerpt else "") or core),
                author=clean(author.get_text()) if author else "",
                product=fields.get("Product", ""),
                module=fields.get("Module", ""),
                content_type=fields.get("Content type", ""),
                date=fields.get("Date", ""),
                jurisdiction=fields.get("Jurisdiction", ""),
                subject_terms=fields.get("Subject(s)", ""),
                core_issues=core,
                access=access,
                content_scope=(
                    "search record with title, citation metadata, jurisdiction, subject terms "
                    "and the editorial core issue(s); not the report text"
                ),
            )
        )

    products = sorted({row["product"] for row in rows if row.get("product")})
    expected = cfg["expected_product"]
    mismatched = (
        [p for p in products if expected.lower() not in p.lower()]
        if product == "mpil"
        else []
    )
    if expected and products and (
        mismatched or not any(expected.lower() in p.lower() for p in products)
    ):
        raise RetrievalError(
            "Product filter not applied: expected "
            + expected
            + "; the page returned "
            + "; ".join(products)
        )

    window = min(args.limit, max(page_size - within, 0))
    selected = rows[within : within + window]
    consumed = args.offset + len(selected)
    if total is not None:
        next_offset = consumed if selected and consumed < total else None
    else:
        next_offset = consumed if selected and len(rows) == page_size else None
    status = "ok" if selected or total == 0 else "no-results-in-queried-index"
    if total == 0:
        status = "no-results-in-queried-index"
    return {
        "status": status,
        "query": query,
        "product": product,
        "date_range": {
            "from": getattr(args, "year_from", None) or None,
            "to": getattr(args, "year_to", None) or None,
        },
        "total": total,
        "results": selected,
        "pagination": {
            "offset": args.offset,
            "limit": args.limit,
            "next_offset": next_offset,
            "page": page,
            "page_size": page_size,
        },
        "products_observed": products,
        "scope": (
            "OPIL product search limited to "
            + cfg["name"]
            + "; rows are retrieval metadata, not report text"
        ),
        "evidence": http.evidence,
        "retrieved_at": meta.get("retrieved_at"),
    }


def fetch(locator: str, args: argparse.Namespace, http: HTTP) -> dict[str, Any]:
    parsed = urlparse(locator)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {
        "opil.ouplaw.com",
    }:
        raise ValueError("fetch expects an https://opil.ouplaw.com/ URL")
    max_bytes = args.max_mb * 1024 * 1024
    if max_bytes < 1:
        raise ValueError("max-mb must be positive")

    _warm(http, "mpil")
    body, meta = http.get(locator, headers=_headers())
    if len(body) > max_bytes:
        raise RetrievalError(f"Response exceeds --max-mb ({args.max_mb} MiB)")
    if body.startswith(b"%PDF"):
        pages = pdf_pages(body)
        text = "\n\n".join(
            f"@@PAGE {page['page']}@@\n{page['text']}" for page in pages
        )
        if args.text_out:
            Path(args.text_out).write_text(text, encoding="utf-8")
        return {
            "status": "ok",
            "url": meta["source_url"],
            "content_type": meta["content_type"],
            "pages": len(pages),
            "needs_ocr": not any(page["text"].strip() for page in pages),
            "page_text": pages,
            "text_out": str(Path(args.text_out).resolve()) if args.text_out else None,
            "sha256": meta["sha256"],
            "retrieved_at": meta["retrieved_at"],
        }
    if "json" in meta["content_type"].lower():
        return {
            "status": "ok",
            "url": meta["source_url"],
            "data": json.loads(body),
            "sha256": meta["sha256"],
            "retrieved_at": meta["retrieved_at"],
        }

    soup = __import__("bs4").BeautifulSoup(body, "html.parser")
    container = soup.select_one(CONTENT_SELECTOR) or soup.select_one("main") or soup.body or soup
    for node in container.select("script, style, nav, header, footer, input, select, button, textarea, noscript"):
        node.decompose()
    text = container.get_text("\n", strip=True)
    if len(text) < 100:
        raise RetrievalError("Insufficient entry-page text; page may be a shell or access page")
    links = []
    seen = set()
    for anchor in container.select("a[href]"):
        href = urljoin(meta["source_url"], anchor["href"])
        if href in seen:
            continue
        seen.add(href)
        links.append({"text": clean(anchor.get_text(" ", strip=True)), "url": href})
    if args.text_out:
        Path(args.text_out).write_text(text, encoding="utf-8")
    return {
        "status": "ok",
        "url": meta["source_url"],
        "text": text,
        "text_characters": len(text),
        "document_links": links,
        "content_scope": (
            "OPIL entry page text from #mainContent; may be an encyclopedia entry body, "
            "a report headnote, or full decision text depending on the product and entitlement"
        ),
        "text_out": str(Path(args.text_out).resolve()) if args.text_out else None,
        "sha256": meta["sha256"],
        "retrieved_at": meta["retrieved_at"],
    }


def doctor(args: argparse.Namespace) -> dict[str, Any]:
    checks = [
        {"check": "python", "ok": True, "detail": "Python runtime available"},
        {"check": "requests", "ok": True, "detail": "requests importable"},
        {"check": "beautifulsoup4", "ok": True, "detail": "bs4 importable"},
    ]
    if args.no_probe:
        return {"ok": True, "status": "ok (probes skipped)", "checks": checks}
    http = HTTP(
        args.cache,
        offline=args.offline,
        ttl=args.cache_ttl,
        timeout=args.timeout,
        cookie_jar=Path(args.cache) / "opil.cookies.txt",
        user_agent=UA,
        min_interval=2.0,
    )
    probes = []
    for product in ("mpil", "oril", "oril-icl"):
        try:
            _warm(http, product)
            params = {
                "sfam": "",
                "q": "command responsibility",
                "pageSize": 20,
                "sort": "relevance",
                "page": 1,
            }
            params.update(PRODUCTS[product]["facets"])
            params.update(PRODUCTS[product]["extra_params"])
            soup, meta = http.soup(SEARCH_URL, params, headers=_headers())
            blocks = soup.select("div.contentItem")
            probes.append(
                {
                    "check": "search:" + product,
                    "ok": bool(blocks),
                    "http_status": meta["http_status"],
                    "bytes": meta["bytes"],
                    "result_blocks": len(blocks),
                }
            )
        except Exception as exc:
            probes.append(
                {
                    "check": "search:" + product,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    checks.extend(probes)
    ok = any(item.get("ok") for item in probes)
    return {
        "ok": ok,
        "status": "ok" if ok else "error",
        "checks": checks,
        "catalog": {"products": sorted(PRODUCTS)},
    }
