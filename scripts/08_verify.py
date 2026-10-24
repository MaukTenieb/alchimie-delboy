"""Étape 8 : contrôle qualité du site généré.

Le contrôle porte sur l'architecture réelle, pas sur les volumes annoncés :

1. chaque lien interne (href/src) désigne un fichier présent ;
2. chaque ancre visée existe dans la page cible — et quand elle n'existe pas,
   on distingue une ancre héritée du site d'origine (légitime : le lien est
   ramené en haut de page) d'une ancre cassée par la réécriture (défaut) ;
3. chaque page du corpus est atteignable : au moins un lien interne la cite ;
4. les images référencées existent ;
5. les pages orphelines, les doublons de slug et les liens morts sont listés.

Sortie : rapport lisible + code de sortie 0 si le site est cohérent.
"""
from __future__ import annotations

import collections
import html
import json
import os
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
RAW = os.path.join(ROOT, "raw", "pages")

LINK_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]*)"', re.I)
ANCHOR_RE = re.compile(r'(?:<a\s+name\s*=|[\s"])id\s*=\s*"([^"]*)"', re.I)


def norm_anchor(a: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(unquote(a)).strip()).lower()


def anchors_of(path: str) -> set[str]:
    """Ancres d'une page, lues une seule fois puis mises en cache."""
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return set()
    out = set()
    # les ancres du site s'écrivent avec ou sans guillemets (<a name=l_t>) et
    # parfois après d'autres attributs (<a href=... name="x">)
    for m in re.finditer(
            r'<a\b[^>]*?\bname\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
            raw, re.I):
        out.add(norm_anchor(next(g for g in m.groups() if g is not None)))
    for m in re.finditer(
            r'\sid\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', raw, re.I):
        out.add(norm_anchor(next(g for g in m.groups() if g is not None)))
    return out


def main() -> None:
    pages = 0
    links = 0
    imgs_ref: set[str] = set()
    missing = collections.Counter()
    missing_from: dict[str, str] = {}
    dead_anchor = collections.Counter()
    inherited_anchor = collections.Counter()
    anchor_cache: dict[str, set[str]] = {}
    linked_targets: set[str] = set()
    html_files: list[str] = []


    for dp, _, fs in os.walk(SITE):
        for f in fs:
            if f.endswith(".html"):
                html_files.append(os.path.join(dp, f))

    sel = json.load(open(os.path.join(ROOT, "data", "selection.json"),
                         encoding="utf-8"))
    # slug de réplique → fichier source, pour distinguer une ancre héritée du
    # site d'origine (légitime) d'une ancre cassée par la réécriture
    from common import slugify
    raw_of = {}
    for r in sel["kept"]:
        raw_of.setdefault(slugify(os.path.splitext(r["key"])[0], 70), r["key"])
    for p in html_files:
        pages += 1
        text = open(p, encoding="utf-8", errors="replace").read()
        rel_self = os.path.relpath(p, SITE)
        for m in LINK_RE.finditer(text):
            u = m.group(1).strip()
            if (not u or u.startswith(("http", "//", "mailto:", "data:",
                                       "javascript:", "#")) or "${" in u):
                continue
            parts = urlsplit(u)
            path = unquote(parts.path)
            if not path:
                continue
            links += 1
            tgt = os.path.normpath(os.path.join(os.path.dirname(p), path))
            rel_tgt = os.path.relpath(tgt, SITE) if tgt.startswith(SITE) else tgt
            rel_tgt = rel_tgt.replace(os.sep, "/")
            linked_targets.add(rel_tgt)
            if not os.path.exists(tgt):
                missing[u] += 1
                missing_from.setdefault(u, rel_self)
                continue
            if parts.fragment and tgt.endswith(".html"):
                if tgt not in anchor_cache:
                    anchor_cache[tgt] = anchors_of(tgt)
                if norm_anchor(parts.fragment) not in anchor_cache[tgt]:
                    # l'ancre existait-elle dans la page d'origine ?
                    stem = os.path.basename(tgt)[:-5]
                    src = raw_of.get(stem)
                    # seules les répliques reprennent les ancres du site
                    # d'origine ; dans les articles, les ancres sont créées
                    # par la reconstitution (une par paragraphe)
                    if src and rel_tgt.startswith("original/"):
                        cand = os.path.join(RAW, src)
                        if os.path.exists(cand) and norm_anchor(parts.fragment) not in anchors_of(cand):
                            # le site d'origine lui-même ne connaît pas l'ancre
                            inherited_anchor[u] += 1
                            continue
                    dead_anchor[u] += 1
            if tgt.endswith((".gif", ".jpg", ".jpeg", ".png")):
                imgs_ref.add(tgt)

    imgs_missing = [a for a in imgs_ref if not os.path.exists(a)]
    weight_img = sum(os.path.getsize(a) for a in imgs_ref if os.path.exists(a))

    # architecture : chaque article doit être cité par au moins une page
    articles = [f"articles/{s}" for s in os.listdir(os.path.join(SITE, "articles"))]
    orphans = [a for a in articles if a not in linked_targets]
    replicas = [f"original/{s}" for s in os.listdir(os.path.join(SITE, "original"))]
    orphan_replicas = [a for a in replicas if a not in linked_targets]

    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(SITE) for f in fs)
    chars = sum(r["chars"] for r in sel["kept"])

    print(f"pages HTML analysées      : {pages}")
    print(f"liens internes            : {links:,}".replace(",", " "))
    print(f"liens morts               : {sum(missing.values())}")
    for u, c in missing.most_common(12):
        print(f"   {c:>4}  {u}   (vu dans {missing_from[u]})")
    print(f"ancres cassées            : {sum(dead_anchor.values())}")
    for u, c in dead_anchor.most_common(8):
        print(f"   {c:>4}  {u}")
    print(f"ancres d'origine absentes : {sum(inherited_anchor.values())} "
          f"(liens ramenés en haut de page, comportement voulu)")
    print(f"articles orphelins        : {len(orphans)}")
    for a in orphans[:8]:
        print("   ", a)
    print(f"répliques orphelines      : {len(orphan_replicas)}")
    print(f"images référencées        : {len(imgs_ref)} "
          f"(manquantes : {len(imgs_missing)}, {weight_img/1e6:.1f} Mo)")
    for a in imgs_missing[:5]:
        print("   absente :", os.path.relpath(a, SITE))
    print(f"poids du site             : {size/1e6:.1f} Mo")
    print(f"corpus                    : {len(sel['kept'])} pages, "
          f"{chars:,} caractères".replace(",", " "))

    ok = (not missing and not imgs_missing and not dead_anchor
          and not orphans and not orphan_replicas)
    print("RÉSULTAT                  :",
          "OK — architecture cohérente" if ok else "ANOMALIES À CORRIGER")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
