"""Étape 7 : index du moteur de recherche.

Le corpus fait 25 millions de caractères : un index unique de 40 Mo rendrait
la recherche inutilisable au premier chargement. L'index est donc éclaté en
fragments chargés à la demande :

  data/search/meta.json      métadonnées (articles, sections, df de chaque terme)
  data/search/post/<x>.json  listes d'occurrences des termes commençant par <x>
  data/search/pass/<n>.json  textes des passages, répartis en 12 seaux

Une requête ne charge que les fragments des premières lettres de ses termes,
puis les seaux des passages cités par les meilleurs résultats.

Chaque passage retient l'indice de son premier paragraphe : la recherche peut
donc pointer directement l'ancre #pN de l'article, au lieu de renvoyer au
début de la page.

Vocabulaire : termes en minuscules, sans accents, tronqués à 7 lettres (les
flexions françaises se rejoignent : « philosophique »/« philosophiques »).
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict

from common import DATA, SITE, log, read_json, slugify, write_json

TRUNC = 7
# tous les termes sont indexés, y compris ceux qui n'apparaissent qu'une fois :
# ce sont souvent des noms propres ou des formes rares, et les écarter ferait
# perdre en exhaustivité plus qu'on ne gagne en poids.
MIN_DF = 1
CHUNK = 1100
BUCKETS = 12

STOP = set("""le la les un une des du de d au aux a et ou mais donc or ni car
que qui quoi dont ce cet cette ces celui celle ceux celles son sa ses leur
leurs il elle ils elles nous vous je tu on se sy en y ne pas plus moins tres
etre avoir fait faire comme tout tous toute toutes autre autres meme aussi
bien peut peu sans sous sur dans par pour avec contre entre chez vers est sont
ete etait etaient fut furent ont avait avaient ainsi alors quand depuis
pendant apres avant encore non oui si deux trois quatre cinq premier premiere
second seconde partie chapitre plan page suite fin debut lors donc selon
cest setait nest quun quune jusqu lorsqu puis ici cela ceci chaque plusieurs
certains certaines
""".split())

TEXT_SECTIONS = {"1", "8", "DC"}


def norm_word(w: str) -> str:
    w = w.lower().replace("œ", "oe").replace("æ", "ae")
    w = unicodedata.normalize("NFD", w)
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", w)


def norm_tokens(text: str) -> list[str]:
    text = text.lower().replace("œ", "oe").replace("æ", "ae")
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    out = []
    for w in text.split():
        if len(w) < 3 or w in STOP or w.isdigit():
            continue
        out.append(w[:TRUNC])
    return out


def shard_of(term: str) -> str:
    c = term[0]
    return c if c.isalnum() else "_"


def buckets_of(doc_id: int) -> int:
    return doc_id % BUCKETS


def main() -> None:
    sel = read_json(os.path.join(DATA, "selection.json"))
    docs = {d["key"]: d for d in
            (json.loads(l) for l in
             open(os.path.join(DATA, "docs.jsonl"), encoding="utf-8"))}
    kept = [r for r in sel["kept"] if r["key"] in docs]
    kept.sort(key=lambda r: (r["section"], -r["chars"], r["key"]))

    # mêmes identifiants de page que 06_build_site.py
    slug, used = {}, set()
    for r in kept:
        base = slugify(os.path.splitext(r["key"])[0], 70)
        s, i = base, 2
        while s in used:
            s = f"{base}-{i}"
            i += 1
        used.add(s)
        slug[r["key"]] = s

    meta_docs, passages, postings = [], [], defaultdict(list)
    dl: list[int] = []          # nombre de tokens de chaque passage
    for i, r in enumerate(kept):
        d = docs[r["key"]]
        meta_docs.append({
            "s": slug[r["key"]], "t": d["title"], "k": r["key"],
            "sec": r["section"], "lab": r["label"], "c": r["chars"],
            "u": d["url"], "ts": d["ts"],
            "img": len(d["images"]),
            "type": "texte" if r["section"] in TEXT_SECTIONS else "etude",
        })

        heading, buf, blen, start = "", [], 0, 0
        pid = 0

        def flush():
            nonlocal buf, blen
            text = " ".join(buf).strip()
            if len(text) >= 120:
                k = len(passages)
                passages.append({"d": i, "p": start, "h": heading[:110],
                                 "t": text})
                toks = norm_tokens(text)
                dl.append(len(toks))
                for t, tf in Counter(toks).items():
                    postings[t].append(k)
                    postings[t].append(tf)
            buf, blen = [], 0

        for pi, (kind, text) in enumerate(d["paras"]):
            if kind.startswith("h"):
                if blen > CHUNK * 0.45:
                    flush()
                heading = text
                continue
            if len(text) < 3:
                continue
            if not buf:
                start = pi
            buf.append(text)
            blen += len(text)
            if blen >= CHUNK:
                flush()
                start = pi + 1
        flush()

    total_tokens = sum(sum(v[1::2]) for v in postings.values())
    avgdl = total_tokens / max(1, len(passages))
    # répartition par section des mots assez fréquents, pour la fiche du mot
    sec_ids = sorted({r["section"] for r in kept})
    sec_pos = {s: i for i, s in enumerate(sec_ids)}
    sec_hist = {}
    for t, v in postings.items():
        if len(v) // 2 < 50:
            continue
        hist = [0] * len(sec_ids)
        last = -1
        for j in range(0, len(v), 2):
            d = passages[v[j]]["d"]
            if d != last:            # passages triés par document
                hist[sec_pos[kept[d]["section"]]] += 1
                last = d
        sec_hist[t] = hist
    df = {t: len(v) // 2 for t, v in postings.items()}
    keep_terms = {t for t, n in df.items() if n >= MIN_DF}
    log(f"vocabulaire : {len(df)} formes, dont "
        f"{sum(1 for n in df.values() if n == 1)} vues une seule fois")

    out = os.path.join(SITE, "data", "search")
    os.makedirs(os.path.join(out, "post"), exist_ok=True)
    os.makedirs(os.path.join(out, "pass"), exist_ok=True)
    for sub in ("post", "pass"):
        for f in os.listdir(os.path.join(out, sub)):
            os.remove(os.path.join(out, sub, f))

    shards = defaultdict(dict)
    for t in keep_terms:
        shards[shard_of(t)][t] = postings[t]
    for sh, terms in shards.items():
        write_json(os.path.join(out, "post", f"{sh}.json"), terms)

    buckets = defaultdict(list)
    for k, p in enumerate(passages):
        buckets[k % BUCKETS].append(p)
    for b, items in buckets.items():
        write_json(os.path.join(out, "pass", f"{b}.json"), items)

    sections = {}
    for r in kept:
        sections.setdefault(r["section"], r["label"])
    meta = {
        "docs": meta_docs,
        "sections": sections,
        "n": len(passages),
        "avgdl": round(avgdl, 2),
        "df": {t: df[t] for t in sorted(keep_terms)},
        "dl": dl,
        "pdoc": [p["d"] for p in passages],
        "secs": sec_ids,
        "hist": sec_hist,
        "buckets": BUCKETS,
        "built_from": len(kept),
    }
    write_json(os.path.join(out, "meta.json"), meta)

    sizes = []
    for dp, _, fs in os.walk(out):
        for f in fs:
            p = os.path.join(dp, f)
            sizes.append((os.path.getsize(p), os.path.relpath(p, out)))
    total = sum(s for s, _ in sizes)
    log(f"{len(passages)} passages, {len(keep_terms)} termes indexés, "
        f"{len(shards)} fragments de vocabulaire, {len(buckets)} seaux")
    log(f"moyenne {avgdl:.0f} tokens par passage — index total "
        f"{total/1e6:.1f} Mo (compressé ~{total/3.4/1e6:.1f} Mo)")
    biggest = sorted(sizes, reverse=True)[:5]
    for s, n in biggest:
        log(f"   {n:<22} {s/1e6:6.1f} Mo")


if __name__ == "__main__":
    main()
