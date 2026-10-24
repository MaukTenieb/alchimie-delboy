"""Étape 1 : inventaire complet du site depuis les index d'archives.

Sources : API CDX d'Internet Archive (deux hôtes successifs du site :
perso.club-internet.fr/hdelboy puis herve.delboy.perso.sfr.fr).
Produit data/urls.json : pour chaque URL unique, la meilleure capture 200.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict
from urllib.parse import urlsplit, unquote, urlunparse

from common import DATA, RAW, log, write_json, session

CDX_HOST = "http://web.archive.org/cdx/search/cdx"
TARGETS = [
    ("perso.club-internet.fr", "/hdelboy"),
    ("herve.delboy.perso.sfr.fr", "/"),
]


def cdx(host: str, prefix: str) -> list[tuple]:
    cache = os.path.join(RAW, f"cdx_{host.replace('.', '_')}.txt")
    if not os.path.exists(cache) or os.path.getsize(cache) < 1000:
        params = {
            "url": host + prefix,
            "matchType": "prefix",
            "output": "text",
            "fl": "timestamp,original,statuscode,mimetype,length",
            "filter": "statuscode:200",
            "collapse": "digest",
        }
        log("CDX", host + prefix)
        r = session.get(CDX_HOST, params=params, timeout=300)
        r.raise_for_status()
        open(cache, "wb").write(r.content)
    rows = []
    with open(cache, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split(" ")
            if len(parts) == 5 and parts[0].isdigit():
                rows.append(tuple(parts))
    return rows


def main() -> None:
    best: dict[str, dict] = {}
    for host, prefix in TARGETS:
        rows = cdx(host, prefix)
        log(f"  {len(rows)} captures 200 pour {host}")
        for ts, original, status, mime, length in rows:
            p = urlsplit(original)
            if p.netloc.split(":")[0] != host:
                continue
            path = unquote(p.path)
            # on ignore les artefacts de robots / captures de formulaires
            if re.search(r"(\.well-known|/\+|%20|gotosite)", path, re.I):
                continue
            name = path.rsplit("/", 1)[-1]
            if not name:
                name = "index.html"
            key = name.lower()
            ext = os.path.splitext(key)[1]
            kind = "page" if ext in ("", ".html", ".htm") else (
                "image" if ext in (".gif", ".jpg", ".jpeg", ".png", ".bmp") else
                "other")
            cand = {
                "key": key,
                "path": path,
                "host": host,
                "url": urlunparse(("http", host, path, "", p.query, "")),
                "ts": ts,
                "mime": mime,
                "size": int(length or 0),
                "kind": kind,
            }
            prev = best.get(key)
            # on garde la capture la plus lourde (page la plus complète),
            # puis la plus ancienne en cas d'égalité
            if prev is None or (cand["size"], -int(ts)) > (prev["size"], -int(prev["ts"])):
                best[key] = cand

    urls = sorted(best.values(), key=lambda d: d["key"])
    write_json(os.path.join(DATA, "urls.json"), urls)
    pages = [u for u in urls if u["kind"] == "page"]
    imgs = [u for u in urls if u["kind"] == "image"]
    log(f"URL uniques : {len(urls)} | pages : {len(pages)} | images : {len(imgs)}")
    hosts = defaultdict(int)
    for u in urls:
        hosts[u["host"]] += 1
    log(dict(hosts))


if __name__ == "__main__":
    main()
