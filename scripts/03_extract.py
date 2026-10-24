"""Étape 3 : extraction structurée (titre, métadonnées, titres internes,
paragraphes, liens du site, images, ancres) vers data/docs.jsonl.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urljoin, unquote

from common import (DATA, RAW, decode_html, iter_strings, log,
                    node_text, norm_text, parse_html, title_key)

PAGES_DIR = os.path.join(RAW, "pages")
BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5",
         "h6", "blockquote", "table", "center", "pre", "dt", "dd"}


def blocks(node, out, depth=0):
    """Découpe récursive en blocs de texte, en gardant les titres."""
    if depth > 60:
        return
    for child in node.children:
        if isinstance(child, str):
            t = norm_text(child)
            if t:
                out.append(("txt", t))
            continue
        if child.tag in ("script", "style"):
            continue
        if child.tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            t = node_text(child)
            if t:
                out.append((child.tag, t))
            continue
        if child.tag == "title":
            continue
        blocks(child, out, depth + 1)


def main() -> None:
    meta = json.load(open(os.path.join(DATA, "urls.json"), encoding="utf-8"))
    by_key = {m["key"]: m for m in meta}
    docs = []
    for fn in sorted(os.listdir(PAGES_DIR)):
        key = fn
        raw = open(os.path.join(PAGES_DIR, fn), "rb").read()
        html = decode_html(raw)
        if "<" not in html[:5000]:
            log("  non-HTML ignoré:", key)
            continue
        root = parse_html(html)
        title = ""
        metas = {}
        anchors = []
        for n in root.find_all("title"):
            title = node_text(n)
            break
        for n in root.find_all("meta"):
            name = (n.get("name") or n.get("http-equiv") or "").lower()
            content = n.get("content")
            if name and content:
                metas[name] = norm_text(content)
        for n in root.find_all("a"):
            if n.get("name"):
                anchors.append(unquote(n.get("name")))
        bodies = root.find_all("body")
        body = bodies[0] if bodies else root
        bl = []
        blocks(body, bl)
        # fusion des blocs texte consécutifs courts
        paras = []
        for kind, t in bl:
            if kind == "txt" and len(t) < 40 and paras and paras[-1][0] == "txt":
                paras[-1] = ("txt", paras[-1][1] + " " + t)
            else:
                paras.append((kind, t))

        links, images = [], []
        for n in body.find_all("a"):
            href = n.get("href", "")
            if not href or href.lower().startswith(("mailto:", "javascript:")):
                continue
            txt = node_text(n)
            if href.lower().startswith("file:///"):
                href = href.split("new_web/", 1)[-1]
            k = title_key(href)
            if k:
                links.append({"key": k, "href": href, "text": txt[:200]})
        for n in body.find_all("img"):
            src = n.get("src", "")
            if src and not src.lower().startswith(("http://perso.estat", "http://www.", "https://")):
                images.append({"src": src.split("/")[-1], "alt": n.get("alt", "")})

        text = "\n".join(t for kind, t in paras if kind == "txt")
        head = [t for kind, t in paras if kind.startswith("h")]
        # titres purement techniques (« philalethe_6 », « chevreul_hoefer_3 ») :
        # on reprend le premier titre interne, sinon le début du texte
        clean = norm_text(title)
        stem = os.path.splitext(key)[0]
        if not clean or "_" in clean or clean.lower() in (stem, key):
            alt = next((t for k, t in paras if k.startswith("h") and len(t) >= 8), "")
            clean = alt or (paras[0][1] if paras else "") or stem
            clean = re.split(r"\s+revu le\s+|\s+mis à jour\s+", clean)[0]
            clean = clean[:95].rsplit(" ", 1)[0].rstrip(" ,;:")
        doc = {
            "key": key,
            "title": clean,
            "metas": metas,
            "anchors": anchors,
            "headings": head[:200],
            "paras": paras,
            "text": text,
            "chars": len(text),
            "links": links,
            "images": images,
            "host": by_key.get(key, {}).get("host", ""),
            "url": by_key.get(key, {}).get("url", ""),
            "ts": by_key.get(key, {}).get("ts", ""),
        }
        docs.append(doc)

    docs.sort(key=lambda d: d["key"])
    with open(os.path.join(DATA, "docs.jsonl"), "w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    total = sum(d["chars"] for d in docs)
    log(f"{len(docs)} documents, {total:,} caractères de texte".replace(",", " "))
    log(f"moyenne {total//max(1,len(docs))} car./page")


if __name__ == "__main__":
    main()
