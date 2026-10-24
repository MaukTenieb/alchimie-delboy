"""Utilitaires partagés du pipeline Delboy alchimie."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, unquote

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, "cache")
SITE = os.path.join(ROOT, "site")
for d in (RAW, DATA, CACHE, SITE):
    os.makedirs(d, exist_ok=True)

# UA descriptif : archive.org bloque les UA de navigateurs utilisés par des robots
# (HTTP 429 « suspected abusive bot traffic »).
UA = "delboy-alchimie-archive/1.0 (reconstitution documentaire; contact: local)"

HOSTS = {
    "herve.delboy.perso.sfr.fr": "sfr",
    "perso.club-internet.fr": "club",
}

session = requests.Session()
session.headers.update({"User-Agent": UA})


try:  # console Windows : éviter les crashs sur les noms de fichiers non-ASCII
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# --------------------------------------------------------------- renommages
# Le site a été refondu plusieurs fois. Des pages citées par les captures
# anciennes (2001-2004, hôte Club-Internet) ont changé de nom lors des refontes
# suivantes (hôte SFR) : l'ancienne adresse n'a jamais été archivée avec son
# contenu, mais le texte est bien présent dans le corpus sous son nouveau nom.
# La correspondance est établie sur trois indices concordants : le plan
# alchimique de l'auteur ne cite que le nouveau nom, les captures de 2009-2013
# ne citent que le nouveau nom, et le titre du lien entrant correspond.
RENAMES = {
    "portanus.htm": "pontanus.html",          # graphie fautive de Pontanus
    "toyson_d_or.htm": "toyson.html",          # « la Toison d'or »
    "toyson_d'or.htm": "toyson.html",
    "zodiaque_alch.htm": "zodiaque_alchimique.html",
    "origines.htm": "origine_alchimie.htm",
    "plan_alchimie.html": "plan_alchimie.htm",
}


def resolve_rename(key: str, known: set[str] | None = None) -> str:
    """Nouveau nom d'une page renommée, si la cible existe."""
    tgt = RENAMES.get(key.lower())
    if tgt and (known is None or tgt in known):
        return tgt
    return ""


def log(*a):
    print(*a, flush=True)


def write_json(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def read_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cache_path(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return os.path.join(CACHE, h[:2], h)


def fetch(url: str, *, tries: int = 4, timeout: int = 60, binary: bool = False):
    """GET avec cache disque et backoff. Retourne bytes ou None."""
    cp = cache_path(url)
    if os.path.exists(cp):
        with open(cp, "rb") as f:
            return f.read()
    delay = 2.0
    for attempt in range(1, tries + 1):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200:
                os.makedirs(os.path.dirname(cp), exist_ok=True)
                with open(cp, "wb") as f:
                    f.write(r.content)
                return r.content
            if r.status_code in (404, 403, 410, 451):
                return None
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
                continue
            return None
        except Exception:
            time.sleep(delay)
            delay *= 2
    return None


CHARSET_RE = re.compile(rb'charset\s*=\s*["\']?([\w\-]+)', re.I)

# cp1252 : positions 0x80-0x9F qui diffèrent de latin-1 (œ, ’, —, €…).
# Les octets non définis (0x81, 0x8D, 0x8F, 0x90, 0x9D) sont laissés tels quels.
CP1252 = {
    0x80: "\u20ac", 0x82: "\u201a", 0x83: "\u0192", 0x84: "\u201e",
    0x85: "\u2026", 0x86: "\u2020", 0x87: "\u2021", 0x88: "\u02c6",
    0x89: "\u2030", 0x8A: "\u0160", 0x8B: "\u2039", 0x8C: "\u0152",
    0x8E: "\u017d", 0x91: "\u2018", 0x92: "\u2019", 0x93: "\u201c",
    0x94: "\u201d", 0x95: "\u2022", 0x96: "\u2013", 0x97: "\u2014",
    0x98: "\u02dc", 0x99: "\u2122", 0x9A: "\u0161", 0x9B: "\u203a",
    0x9C: "\u0153", 0x9E: "\u017e", 0x9F: "\u0178",
}


def _cp1252(data: bytes) -> str:
    return "".join(CP1252.get(ord(c), c) for c in data.decode("latin-1"))


def decode_html(data: bytes, fallback: str = "cp1252") -> str:
    """Décode une page du site.

    Les pages déclarent ISO-8859-1 mais utilisent en réalité cp1252 (œ, ’,
    « », –), comme la plupart des pages françaises de cette époque : décoder
    en latin-1 produirait des caractères de contrôle à la place de œ et ’.
    """
    if not data:
        return ""
    m = CHARSET_RE.search(data[:4096])
    enc = fallback
    if m:
        enc = m.group(1).decode("ascii", "ignore").lower()
    if enc in ("utf-8", "utf8"):
        try:
            return data.decode("utf-8")
        except Exception:
            return _cp1252(data)
    return _cp1252(data)


def title_key(href: str) -> str:
    """Identifiant logique d'une page du site (sans hôte, sans ancre, sans :80)."""
    if not href:
        return ""
    href = href.strip()
    if href.startswith("file:///"):
        href = href.split("new_web/", 1)[-1]
        href = href.split("/")[-1]
        return href.lower()
    p = urlsplit(href)
    path = p.path
    if not path:
        return ""
    name = unquote(path.rsplit("/", 1)[-1])
    return name.lower()


def norm_text(s: str) -> str:
    s = s.replace("\r", " ").replace("\n", " ")
    # caractères de contrôle hérités des copier-coller de l'époque
    s = "".join(c for c in s if c >= " " or c == "\t")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def slugify(s: str, maxlen: int = 80) -> str:
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:maxlen].rstrip("-") or "page")


# ---------------------------------------------------------------- HTML parsing

class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []
        self.parent = parent
        self.text = ""

    def find_all(self, tag):
        out = []
        stack = [self]
        while stack:
            n = stack.pop()
            if isinstance(n, str):
                continue
            if n.tag == tag:
                out.append(n)
            stack.extend(reversed(n.children))
        return out

    def get(self, k, default=""):
        return self.attrs.get(k, default)


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
DROP = {"script", "style"}


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag in DROP:
            self.skip += 1
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)

    def handle_endtag(self, tag):
        if tag in DROP and self.skip:
            self.skip -= 1
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if not self.skip:
            self.cur.children.append(data)


def parse_html(html: str) -> Node:
    tb = TreeBuilder()
    try:
        tb.feed(html)
        tb.close()
    except Exception:
        pass
    return tb.root


def node_text(node: Node) -> str:
    if isinstance(node, str):
        return node
    out = []
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, str):
            out.append(n)
            continue
        if n.tag in DROP:
            continue
        if n.tag in ("br", "p", "div", "tr", "li", "h1", "h2", "h3", "h4", "table", "blockquote"):
            out.append(" ")
        stack.extend(reversed(n.children))
    return norm_text("".join(out))


def iter_strings(node: Node):
    """Parcourt les nœuds texte dans l'ordre du document."""
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, str):
            yield n
            continue
        if n.tag in DROP:
            continue
        # les enfants sont empilés à l'envers pour préserver l'ordre
        stack.extend(reversed(n.children))
