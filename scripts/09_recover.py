"""Étape 9 : récupération des pages perdues.

Pourquoi ces pages manquaient : Club-Internet servait sa page d'erreur 404
avec un code HTTP 200. L'archive a donc conservé des captures « valides » en
apparence, mais vides de contenu — et le dédoublonnage par empreinte (CDX
collapse=digest) les avait fait disparaître de l'inventaire initial.

On travaille ici sur l'index CDX **complet** (raw/cdxall_*.txt, toutes les
captures, tous les statuts), on écarte les captures dont le corps est la page
d'erreur de l'hébergeur, puis on tente, dans l'ordre :
  1. toutes les captures Wayback de l'URL exacte ;
  2. les variantes d'URL présentes dans l'index (.htm/.html, casse, encodage) ;
  3. l'index Common Crawl (campagnes 2013 → 2024) ;
  4. archive.today (archive.ph / .is / .fo / .li), sous réserve du CAPTCHA.

Résultat : raw/pages/<clé> pour les pages retrouvées, data/recovered.json
(provenance) et data/recovery_failed.json (raison de l'échec).
"""
from __future__ import annotations

import collections
import json
import os
import re
import time
from urllib.parse import unquote, urlsplit

import sys

from common import DATA, RAW, decode_html, log, read_json, session, write_json

PAGES_DIR = os.path.join(RAW, "pages")
session.headers.update({"User-Agent": "delboy-alchimie-archive/1.0"})

ERROR_MARKS = ("erreurs/erreur404", "erreur 404", "la page n'existe plus",
               "page cannot be found", "page not found", "404 not found",
               "wayback machine</title>")
# taille des pages d'erreur Club-Internet (2002) : 6955-6980 octets
ERR_BAND = range(6900, 7000)

CC_CRAWLS = ["CC-MAIN-2016-30", "CC-MAIN-2013-48"]
_cc_fail = 0
_at_fail = 0


def load_cdx() -> dict[str, list[tuple]]:
    idx = collections.defaultdict(list)
    for f in ("cdxall_herve_delboy_perso_sfr_fr.txt",
              "cdxall_perso_club-internet_fr_hdelboy.txt"):
        path = os.path.join(RAW, f)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split(" ")
            if len(p) != 5 or not p[0].isdigit():
                continue
            ts, url, status, mime, length = p
            path_ = unquote(urlsplit(url).path)
            key = path_.rsplit("/", 1)[-1].lower() or "index.html"
            try:
                size = int(length)
            except ValueError:
                size = 0
            idx[key].append((ts, status, size, url))
    return idx


def is_error(raw: bytes) -> bool:
    if not raw or len(raw) < 250:
        return True
    # capture d'image servie à la place d'une page HTML
    if raw[:6] in (b"GIF87a", b"GIF89a") or raw[:4] == b"\x89PNG" or raw[:4] == b"%PDF":
        return True
    text = decode_html(raw).lower()
    if any(m in text for m in ERROR_MARKS):
        return True
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return len(re.sub(r"\s+", " ", body).strip()) < 100


def get(url: str, ts: str) -> bytes | None:
    try:
        r = session.get(f"https://web.archive.org/web/{ts}id_/{url}", timeout=60)
        if r.status_code == 200 and not is_error(r.content):
            return r.content
    except Exception:
        pass
    return None


def variants_of(key: str, idx: dict) -> list[str]:
    stem = os.path.splitext(key)[0]
    cand = {stem + ".htm", stem + ".html", stem.upper() + os.path.splitext(key)[1],
            key.replace("+", "%20"), key.replace("%20", "+")}
    return [k for k in cand if k != key and k in idx]


def via_wayback(key: str, idx: dict) -> tuple[bytes | None, str]:
    keys = [key, *variants_of(key, idx)]
    for k in keys:
        caps = [c for c in idx.get(k, [])
                if c[1] == "200" and c[2] > 500]
        # les pages d'erreur Club-Internet ont une taille très typique : on ne
        # les essaie qu'en dernier recours
        caps.sort(key=lambda c: (c[2] in ERR_BAND, -c[2]))
        for ts, status, size, url in caps[:5]:
            data = get(url, ts)
            if data:
                return data, f"wayback {ts} {url}"
            time.sleep(0.2)
    return None, ""


def via_commoncrawl(key: str) -> tuple[bytes | None, str]:
    global _cc_fail
    if _cc_fail >= 4:
        return None, "commoncrawl : index indisponible"
    for crawl in CC_CRAWLS:
        for u in (f"herve.delboy.perso.sfr.fr/{key}",
                  f"perso.club-internet.fr/hdelboy/{key}"):
            try:
                r = session.get(f"https://index.commoncrawl.org/{crawl}-index",
                                params={"url": u, "output": "json"}, timeout=25)
                if r.status_code in (502, 503, 504):
                    _cc_fail += 1
                    continue
                if r.status_code != 200 or not r.text.strip():
                    continue
                rec = json.loads(r.text.strip().splitlines()[0])
                rr = session.get(f"https://data.commoncrawl.org/{rec['filename']}",
                                 headers={"Range": f"bytes={rec['offset']}-"
                                          f"{int(rec['offset'])+int(rec['length'])-1}"},
                                 timeout=60)
                if rr.status_code not in (200, 206):
                    continue
                blob = rr.content
                cut = blob.find(b"\r\n\r\n")
                body = blob[cut + 4:] if cut > 0 else blob
                if not is_error(body):
                    return body, f"commoncrawl {crawl} {rec.get('url')}"
            except Exception:
                continue
    return None, ""


def via_archive_today(key: str) -> tuple[bytes | None, str]:
    global _at_fail
    if _at_fail >= 2:
        return None, "archive.today : 429 (limitation / CAPTCHA)"
    for host in ("archive.ph", "archive.is", "archive.li"):
        try:
            r = session.get(f"https://{host}/newest/http://herve.delboy.perso.sfr.fr/{key}",
                            timeout=25, allow_redirects=True)
            if r.status_code == 429:
                _at_fail += 1
                return None, "archive.today : 429 (limitation / CAPTCHA)"
            if r.status_code == 200 and not is_error(r.content) \
                    and "captcha" not in r.text.lower()[:8000]:
                return r.content, f"archive.today {r.url}"
        except Exception:
            pass
        time.sleep(1.0)
    return None, "archive.today : rien d'exploitable"


def main() -> None:
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    idx = load_cdx()
    log(f"index local : {sum(len(v) for v in idx.values())} captures, "
        f"{len(idx)} URL")

    sel = read_json(os.path.join(DATA, "selection.json"))
    lost = [o["key"] for o in sel["out"]
            if o.get("raison", "").startswith("capture")]
    log(f"{len(lost)} pages à tenter")

    recovered, failed = {}, {}
    already = read_json(os.path.join(DATA, "recovered.json"), {}) or {}
    for i, key in enumerate(lost, 1):
        if key in already:
            continue
        data, src = (None, "")
        if phase in ("all", "wayback"):
            data, src = via_wayback(key, idx)
        if not data and phase in ("all", "cc"):
            data, src = via_commoncrawl(key)
        if not data and phase in ("all", "at"):
            data, src = via_archive_today(key)
            if "429" in src:
                failed[key] = src
                log(f"  [{i}/{len(lost)}] bloqué    {key} — {src}")
                continue
        if data:
            with open(os.path.join(PAGES_DIR, key), "wb") as f:
                f.write(data)
            recovered[key] = {"source": src, "bytes": len(data)}
            log(f"  [{i}/{len(lost)}] RÉCUPÉRÉ  {key} ({len(data)} o) — {src}")
        else:
            failed[key] = "aucune capture de contenu (page d'erreur de l'hébergeur)"
            log(f"  [{i}/{len(lost)}] perdu     {key}")
        time.sleep(0.25)

    prev = read_json(os.path.join(DATA, "recovered.json"), {}) or {}
    prev.update(recovered)
    write_json(os.path.join(DATA, "recovered.json"), prev)
    prevf = read_json(os.path.join(DATA, "recovery_failed.json"), {}) or {}
    prevf.update(failed)
    write_json(os.path.join(DATA, "recovery_failed.json"), prevf)
    log(f"Récupérées : {len(recovered)} | restées perdues : {len(failed)}")


if __name__ == "__main__":
    main()
