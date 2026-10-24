"""Étape 5 : récupération des images référencées par les pages du périmètre."""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import time
from urllib.parse import unquote

from common import DATA, SITE, fetch, log

ASSETS = os.path.join(SITE, "assets")
os.makedirs(ASSETS, exist_ok=True)


def local_name(src: str) -> str:
    name = unquote(src.split("?")[0].split("/")[-1])
    name = re.sub(r'[<>:"/\\|?*]+', "_", name).strip() or "image"
    return name


def main() -> None:
    sel = json.load(open(os.path.join(DATA, "selection.json"), encoding="utf-8"))
    keep = {r["key"] for r in sel["kept"]}
    docs = [json.loads(l) for l in open(os.path.join(DATA, "docs.jsonl"),
                                        encoding="utf-8")]
    wanted = {}
    for d in docs:
        if d["key"] not in keep:
            continue
        for img in d["images"]:
            wanted.setdefault(img["src"].lower(), img["src"])

    urls = {u["key"].lower(): u for u in
            json.load(open(os.path.join(DATA, "urls.json"), encoding="utf-8"))}
    todo = []
    for low, src in sorted(wanted.items()):
        u = urls.get(low) or urls.get(local_name(low).lower())
        dest = os.path.join(ASSETS, local_name(src))
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        if u:
            todo.append((u, dest))
    log(f"{len(wanted)} images référencées, {len(todo)} à télécharger")

    def get(item):
        u, dest = item
        data = fetch(f"https://web.archive.org/web/{u['ts']}id_/{u['url']}",
                     tries=4, timeout=90)
        if not data:
            return u["key"], 0
        with open(dest, "wb") as f:
            f.write(data)
        return u["key"], len(data)

    ok = fail = total = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for i, (k, n) in enumerate(ex.map(get, todo), 1):
            if n:
                ok += 1
                total += n
            else:
                fail += 1
            if i % 100 == 0:
                log(f"  {i}/{len(todo)} ok={ok} echec={fail} "
                    f"{total//1024} Ko ({time.time()-t0:.0f}s)")
    log(f"Images : {ok} téléchargées, {fail} échecs, {total//1024} Ko")


if __name__ == "__main__":
    main()
