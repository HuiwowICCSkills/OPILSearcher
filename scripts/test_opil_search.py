"""Offline tests for OPILSearcher."""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import opil_adapter as adapter  # noqa: E402


def meta(url="https://opil.ouplaw.com/search"):
    return {
        "source_url": url,
        "http_status": 200,
        "content_type": "text/html",
        "bytes": 100,
        "retrieved_at": "2026-11-09T00:00:00Z",
        "sha256": "0" * 64,
    }


class FakeHttp:
    def __init__(self, html):
        self.html = html
        self.evidence = []

    def get(self, url, params=None, headers=None):
        return b"<html></html>", meta(url)

    def soup(self, url, params=None, headers=None):
        return BeautifulSoup(self.html, "html.parser"), meta()


def args(**kwargs):
    base = dict(product="mpil", limit=1, offset=0, cache=".cache", offline=False, cache_ttl=0, timeout=30)
    base.update(kwargs)
    return argparse.Namespace(**base)


class OpilTests(unittest.TestCase):
    def test_search_parses_product_and_core_issues(self):
        html = """
        <html><body>
        <div>You are looking at 1–1 of 1 results</div>
        <div class="contentItem hasAccess">
          <h2 class="itemTitle"><a href="/display/entry">Command Responsibility</a></h2>
          <div class="itemAuthor">Author A</div>
          <div class="component-content-summary">Summary text</div>
          <dl class="metadata"><dt>Product</dt><dd>Max Planck Encyclopedias of International Law [MPIL]</dd>
          <dt>Core Issue(s)</dt><dd>Who is liable?</dd></dl>
        </div>
        </body></html>
        """
        out = adapter.search("command responsibility", args(), FakeHttp(html))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["products_observed"], ["Max Planck Encyclopedias of International Law [MPIL]"])
        self.assertEqual(out["results"][0]["core_issues"], "Who is liable?")

    def test_search_rejects_wrong_product(self):
        html = """
        <html><body><div>You are looking at 1–1 of 1 results</div>
        <div class="contentItem"><h2 class="itemTitle"><a href="/x">X</a></h2>
        <dl class="metadata"><dt>Product</dt><dd>Oxford Scholarly Authorities on International Law [OSAIL]</dd></dl>
        </div></body></html>
        """
        with self.assertRaisesRegex(Exception, "Product filter not applied"):
            adapter.search("x", args(), FakeHttp(html))


if __name__ == "__main__":
    unittest.main()
