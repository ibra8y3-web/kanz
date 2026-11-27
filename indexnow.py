#!/usr/bin/env python3
"""Submit new/updated Kanz catalog URLs to IndexNow.

IndexNow notifies Bing, Yandex, Naver, Seznam, Yep and the Internet Archive
about added/updated/deleted pages within seconds. Google does not take part.

Usage:
  python crawler/indexnow.py            # submit pages changed in the last commit
  python crawler/indexnow.py --all      # submit every URL in docs/sitemap.xml
  python crawler/indexnow.py --dry-run  # print what would be sent, send nothing
"""
import argparse
import json
import subprocess
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

HOST = "ibra8y3-web.github.io"
BASE = "https://ibra8y3-web.github.io/kanz/"
ENDPOINT = "https://api.indexnow.org/indexnow"
CHUNK = 10000  # protocol maximum per POST

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
KEY_NAME = "0503cdb4f756605d6d3f28c2b0b03b44.txt"


def load_key():
    return (DOCS / KEY_NAME).read_text(encoding="utf-8").strip()


def sitemap_urls():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(DOCS / "sitemap.xml").getroot()
    return [loc.text.strip() for loc in root.findall(".//s:loc", ns) if loc.text]


def changed_urls():
    """Pages whose HTML changed in the latest commit, mapped to their URLs."""
    out = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", "docs"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        return []
    urls = []
    for line in out.stdout.splitlines():
        rel = line.strip()
        if not rel.startswith("docs/") or not rel.endswith(".html"):
            continue
        p = rel[len("docs/"):]
        if p == "index.html":
            urls.append(BASE)
        elif p.endswith("/index.html"):
            urls.append(BASE + p[: -len("index.html")])
        else:
            urls.append(BASE + p)
    return urls


def submit(urls, key, dry):
    key_loc = BASE + KEY_NAME
    total = 0
    for i in range(0, len(urls), CHUNK):
        batch = urls[i : i + CHUNK]
        payload = json.dumps(
            {"host": HOST, "key": key, "keyLocation": key_loc, "urlList": batch}
        ).encode("utf-8")
        if dry:
            print(f"DRY RUN: would POST {len(batch)} urls, first: {batch[0]}")
            total += len(batch)
            continue
        req = urllib.request.Request(
            ENDPOINT, data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                print(f"submitted {len(batch)} urls -> HTTP {r.status}")
                total += len(batch)
        except urllib.error.HTTPError as e:
            print(f"batch failed: HTTP {e.code} {e.read()[:200]!r}", file=sys.stderr)
            sys.exit(1)
    print(f"total submitted: {total}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="submit the whole sitemap")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    key = load_key()
    if args.all:
        urls = sitemap_urls()
    else:
        urls = changed_urls()
        if not urls:
            print("no changed pages, nothing to submit")
            return
        if len(urls) > 9000:
            print(f"{len(urls)} changed urls, submitting full sitemap instead")
            urls = sitemap_urls()
    submit(urls, key, args.dry_run)


if __name__ == "__main__":
    main()
