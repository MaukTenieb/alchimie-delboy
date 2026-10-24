"""Étape 2 : aspiration des pages HTML depuis Wayback (mode id_ = brut, sans barre d'outils).

Cache disque, reprise possible, parallélisme modéré pour rester courtois.
"""
from __future__ import annotations

import concurrent.futures as cf
import os
import sys
import time

from common import DATA, RAW, fetch, log, read_json, write_json

PAGES_DIR = os.path.join(RAW, "pages")
os.makedirs(PAGES_DIR, exist_ok=True)


def wayback_url(u: dict) -> str:
    return f"https://web.archive.org/web/{u['ts']}id_/{u['url']}"


def get(u: dict):
    out = os.path.join(PAGES_DIR, u["key"].replace("/", "_"))
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return u["key"], "cache"
    data = fetch(wayback_url(u), tries=5, timeout=90)
    if data and len(data) > 200 and b"<html" in data.lower()[:4000] or (data and len(data) > 200):
        with open(out, "wb") as f:
            f.write(data)
        return u["key"], len(data)
    return u["key"], None


def main() -> None:
    urls = read_json(os.path.join(DATA, "urls.json"))
    pages = [u for u in urls if u["kind"] == "page"]
    log(f"{len(pages)} pages à aspirer")
    ok = fail = 0
    todo = pages
    if len(sys.argv) > 1:
        todo = pages[: int(sys.argv[1])]
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for i, (key, res) in enumerate(ex.map(get, todo), 1):
            if res is None:
                fail += 1
                log("  ECHEC", key)
            else:
                ok += 1
            if i % 25 == 0:
                log(f"  {i}/{len(todo)} ok={ok} echec={fail} "
                    f"({time.time()-t0:.0f}s)")
    log(f"Terminé : {ok} ok, {fail} échecs")


if __name__ == "__main__":
    main()
