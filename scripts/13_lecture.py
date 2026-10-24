"""Étape 13 : le site se lit comme l'original.

- Les pages de l'auteur (site/original/) gardent leur markup ; elles perdent
  la feuille de style générale (style.css), qui changeait leur typographie,
  et reçoivent une barre d'une ligne (barre.css) : Accueil, Sommaire,
  Recherche, Notice.
- Les anciennes « versions lisibles » (site/articles/) renvoient vers la page
  de l'auteur.
- sommaire.html et sections/<id>.html : tableaux, dans l'ordre du plan.
- Les pages de la couche retirée (portail, index, mots, noms, axes, dossiers,
  méthode, liseuse) renvoient vers le sommaire.

À lancer depuis la racine du dépôt : python scripts/13_lecture.py
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess

from lxml import html as LH
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
ORIG = os.path.join(SITE, "original")
ASSETS = os.path.join(SITE, "assets")
MIN_PX = 120          # une image plus petite est un pictogramme de navigation

MONTHS = "janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre"
REV = re.compile(r"(?:revu|révisé|revisé|mis à jour|mise à jour)(?: le)?\s+(\d{1,2}(?:er)?\s+(?:" + MONTHS + r")\s+\d{4})", re.I)

RIGHTS = """<footer class="foot"><p>© Hervé Delboy et ayants droit.
Site d'origine : perso.club-internet.fr/hdelboy, puis herve.delboy.perso.sfr.fr
(disparu). Reproduction à des fins de consultation, de recherche et de
conservation ; aucune exploitation commerciale. Tous droits réservés aux
auteurs et à leurs ayants droit. <a href="{r}notice.html">Notice</a></p></footer>"""


def bar(r: str) -> str:
    return (f'<div class="replica-note"><a href="{r}index.html">Hervé Delboy — alchimie</a>'
            f' · <a href="{r}sommaire.html">Sommaire</a>'
            f' · <a href="{r}recherche.html">Recherche</a>'
            f' · <a href="{r}notice.html">Notice</a></div>')


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def page(title: str, body: str, r: str) -> str:
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{r}style.css"><link rel="stylesheet" href="{r}barre.css"><script src="{r}barre.js" defer></script>
</head><body class="ui">
{bar(r)}
<main>
{body}
</main>
{RIGHTS.format(r=r)}
</body></html>
"""


def stub(target: str, title: str) -> str:
    t = esc(target)
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            f'<title>{esc(title)}</title><link rel="canonical" href="{t}">'
            f'<meta http-equiv="refresh" content="0; url={t}">'
            f'<script>location.replace("{t}")</script></head>'
            f'<body><a href="{t}">{esc(title)}</a></body></html>\n')


_dims: dict[str, tuple[int, int]] = {}


def dims(name: str) -> tuple[int, int]:
    if name not in _dims:
        try:
            with Image.open(os.path.join(ASSETS, name)) as im:
                _dims[name] = im.size
        except Exception:
            _dims[name] = (0, 0)
    return _dims[name]


def read_original(slug: str) -> dict:
    raw = open(os.path.join(ORIG, slug + ".html"), "rb").read()
    doc = LH.fromstring(raw)
    for n in doc.xpath('//div[@class="replica-note"]|//script|//style'):
        n.getparent().remove(n)
    body = doc.find("body")
    text = re.sub(r"\s+", " ", (body if body is not None else doc).text_content()).strip()
    m = REV.search(text[:3000])
    imgs = []
    for src in doc.xpath("//img/@src"):
        name = src.split("/")[-1]
        w, h = dims(name)
        if w >= MIN_PX and h >= MIN_PX:
            imgs.append(name)
    return {"rev": m.group(1) if m else "", "chars": len(text), "imgs": imgs}


def fix_original(path: str, r: str) -> None:
    b = open(path, "rb").read()
    b = re.sub(rb'<link rel="stylesheet" href="[^"]*style\.css">',
               f'<link rel="stylesheet" href="{r}barre.css"><script src="{r}barre.js" defer></script>'.encode(), b, count=1)
    b, n = re.subn(rb'<div class="replica-note">.*?</div>', bar(r).encode(), b,
                   count=1, flags=re.S)
    if not n:
        raise SystemExit("barre absente : " + path)
    open(path, "wb").write(b)


def pdf_size(rel: str) -> int:
    p = os.path.join(SITE, rel)
    if os.path.exists(p):
        return os.path.getsize(p)
    out = subprocess.run(["git", "-C", ROOT, "ls-tree", "-l", "HEAD", "site/" + rel],
                         capture_output=True, text=True).stdout.split()
    return int(out[3]) if len(out) > 3 else 0


def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def fmt_ts(ts: str) -> str:
    return f"{ts[6:8]}/{ts[4:6]}/{ts[0:4]}" if len(ts) >= 8 else ""


def table(rows: list[dict], r: str, with_section: bool = False) -> str:
    head = ("<tr><th>n°</th><th>Page</th>" + ("<th>Section</th>" if with_section else "")
            + "<th>Révision</th><th class=\"n\">Caractères</th>"
            "<th class=\"n\">Images</th><th>Capture</th></tr>")
    out = []
    for i, d in enumerate(rows, 1):
        wb = f"https://web.archive.org/web/{d['ts']}/{d['u']}" if d.get("u") else ""
        cap = f'<a href="{esc(wb)}">{fmt_ts(d["ts"])}</a>' if wb else ""
        out.append(
            f"<tr><td class=\"n\">{i}</td>"
            f"<td><a href=\"{r}original/{d['s']}.html\">{esc(d['title'])}</a></td>"
            + (f"<td>{esc(d['lab'])}</td>" if with_section else "")
            + f"<td>{esc(d['rev'])}</td><td class=\"n\">{fmt_int(d['chars'])}</td>"
            f"<td class=\"n\">{len(d['imgs'])}</td><td>{cap}</td></tr>")
    return f'<table class="data">{head}{"".join(out)}</table>'


def main() -> None:
    meta = json.load(open(os.path.join(SITE, "data", "search", "meta.json"), encoding="utf-8"))
    docs = {d["s"]: d for d in meta["docs"]}
    plan = re.findall(r'href="sections/([^".]+)\.html"', open(os.path.join(SITE, "plan.html"), encoding="utf-8").read())
    order = list(dict.fromkeys(plan)) or ["1", "2", "3", "4", "5", "6", "7", "8", "dc", "9"]
    sec_label = {k.lower(): v for k, v in meta["sections"].items()}
    sec_docs = {}
    for sid in order:
        t = open(os.path.join(SITE, "sections", sid + ".html"), encoding="utf-8").read()
        sec_docs[sid] = list(dict.fromkeys(re.findall(r'href="\.\./(?:articles|original)/([^"#]+)\.html"', t)))

    rows = {}
    for s, d in docs.items():
        info = read_original(s)
        title = re.sub(r"[\s\-–—:,;.]+$", "", d["t"]).strip() or s
        rows[s] = {"s": s, "title": title, "lab": d["lab"], "u": d.get("u", ""),
                   "ts": d.get("ts", ""), **info}

    # pages de l'auteur
    for fn in os.listdir(ORIG):
        if fn.endswith(".html"):
            fix_original(os.path.join(ORIG, fn), "../")
    fix_original(os.path.join(SITE, "index.html"), "")

    # anciennes versions lisibles
    adir = os.path.join(SITE, "articles")
    for fn in os.listdir(adir):
        s = fn[:-5]
        if s in docs:
            open(os.path.join(adir, fn), "w", encoding="utf-8").write(
                stub(f"../original/{s}.html", rows[s]["title"]))

    # sommaire
    total_c = sum(x["chars"] for x in rows.values())
    total_i = sum(len(x["imgs"]) for x in rows.values())
    tss = sorted(x["ts"] for x in rows.values() if x["ts"])
    body = ['<h1>Sommaire</h1>',
            f'<p class="facts">{len(rows)} pages · {fmt_int(total_c)} caractères · '
            f'{fmt_int(total_i)} images · {len(order)} sections · captures de la '
            f'Wayback Machine, {tss[0][:4]}–{tss[-1][:4]} · ordre et sections : '
            f'<a href="original/plan-alchimie.html">plan de l\'auteur</a></p>',
            '<ol class="toc">' + "".join(
                f'<li><a href="#s{sid}">{esc(sec_label[sid])}</a> '
                f'<span class="n">{len(sec_docs[sid])}</span></li>' for sid in order) + '</ol>']
    for sid in order:
        sr = [rows[s] for s in sec_docs[sid]]
        pdf = f"pdf/section-{sid}.pdf"
        size = pdf_size(pdf)
        body.append(f'<h2 id="s{sid}">{esc(sec_label[sid])}</h2>'
                    f'<p class="facts">{len(sr)} pages · {fmt_int(sum(x["chars"] for x in sr))} caractères'
                    + (f' · <a href="{pdf}">PDF, {size/1e6:.1f} Mo</a>' if size else "")
                    + f' · <a href="sections/{sid}.html">section seule</a></p>')
        body.append(table(sr, ""))
    open(os.path.join(SITE, "sommaire.html"), "w", encoding="utf-8").write(
        page("Sommaire — Hervé Delboy, alchimie", "\n".join(body), ""))

    for sid in order:
        sr = [rows[s] for s in sec_docs[sid]]
        pdf = f"pdf/section-{sid}.pdf"
        size = pdf_size(pdf)
        b = (f'<p class="crumb"><a href="../sommaire.html">Sommaire</a></p>'
             f'<h1>{esc(sec_label[sid])}</h1>'
             f'<p class="facts">{len(sr)} pages · {fmt_int(sum(x["chars"] for x in sr))} caractères'
             + (f' · <a href="../{pdf}">PDF, {size/1e6:.1f} Mo</a>' if size else "") + '</p>'
             + table(sr, "../"))
        open(os.path.join(SITE, "sections", sid + ".html"), "w", encoding="utf-8").write(
            page(f"{sec_label[sid]} — Hervé Delboy, alchimie", b, "../"))

    # couche retirée
    for fn in ("portail.html", "plan.html", "guide.html", "index-general.html", "mots.html",
               "noms.html", "axes.html", "notions.html", "parcours.html", "method.html",
               "liseuse.html", "textes.html", "illustrations.html"):
        p = os.path.join(SITE, fn)
        if os.path.exists(p):
            open(p, "w", encoding="utf-8").write(stub("sommaire.html", "Sommaire"))
    for d in ("mots", "noms", "axes", "parcours"):
        p = os.path.join(SITE, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    seq = [s for sid in order for s in sec_docs[sid]]
    secof = {s: sid for sid in order for s in sec_docs[sid]}
    nav = {"pages": {s: [rows[s]["title"], secof[s], seq[i - 1] if i else None,
                         seq[i + 1] if i + 1 < len(seq) else None] for i, s in enumerate(seq)},
           "sections": {sid: [sec_label[sid], f"pdf/section-{sid}.pdf" if pdf_size(f"pdf/section-{sid}.pdf") else "",
                              f"{pdf_size(f'pdf/section-{sid}.pdf')/1e6:.1f} Mo".replace(".", ",")] for sid in order}}
    json.dump(nav, open(os.path.join(SITE, "data", "nav.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({s: {k: v for k, v in x.items() if k != "s"} for s, x in rows.items()},
              open(os.path.join(SITE, "data", "pages.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print(len(rows), "pages ;", total_i, "images ;", sum(1 for x in rows.values() if x["rev"]), "dates de révision")


if __name__ == "__main__":
    main()
