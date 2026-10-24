"""Étape 11 : portail, guide des index, dossiers de lecture.

Le site ne s'ouvre pas sur un champ de recherche : il s'ouvre sur un portail,
comme une encyclopédie. Cette étape construit :

  index.html          le portail : voies d'entrée, domaines, dossiers, plan
  guide.html          la table de tous les index, avec leurs effectifs
  parcours.html       les dossiers de lecture
  parcours/<x>.html   un dossier : où lire un sujet, du plus dense au plus rare

Tout est calculé à partir du corpus : les dossiers sont les articles où
l'entrée est le plus souvent citée, avec l'ancre du paragraphe.
"""
from __future__ import annotations

import html
import importlib.util
import json
import os
import random
import re

from common import DATA, SITE, log, read_json, slugify

DOSSIERS = [
    ("oeuvres", "Atalanta fugiens",
     "Les cinquante emblèmes de Michael Maier, leurs figures et les lectures "
     "qu’en donne le corpus."),
    ("auteurs", "Flamel",
     "Nicolas Flamel : le Livre d’Abraham, les figures hiéroglyphiques, le "
     "testament, et ce que les traités en disent."),
    ("materiaux", "Antimoine",
     "Le loup des métaux : le Char triomphal, le régime de l’antimoine, les "
     "débats sur son usage."),
    ("techniques", "Distillation",
     "L’alambic, la cornue, le bain-marie : les opérations et les gestes."),
    ("themes", "Nigredo",
     "L’œuvre au noir, le corbeau, la putréfaction : le passage obligé."),
    ("materiel", "Athanor",
     "La tour du feu : fourneaux, températures et conduite du feu."),
]


def load_shell():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "06_build_site.py")
    spec = importlib.util.spec_from_file_location("build_site", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def asset_map() -> dict[str, str]:
    out = {}
    adir = os.path.join(SITE, "assets")
    if os.path.isdir(adir):
        for f in os.listdir(adir):
            out[f.lower()] = f
    return out


def local_of(src: str, assets: dict[str, str]) -> str:
    from urllib.parse import unquote
    name = unquote(src.split("?")[0].split("/")[-1])
    name = re.sub(r'[<>:"/\\|?*]+', "_", name)
    return assets.get(name.lower(), "")


def write_page(bs, path: str, title: str, body: str, root: str = "") -> None:
    os.makedirs(os.path.dirname(path) or SITE, exist_ok=True)
    out = bs.CSS.format(title=esc(title), root=root, extra="") + body + \
        bs.FOOT.format(root=root)
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)


def main() -> None:
    bs = load_shell()
    sel = read_json(os.path.join(DATA, "selection.json"))
    docs = {d["key"]: d for d in
            (json.loads(l) for l in
             open(os.path.join(DATA, "docs.jsonl"), encoding="utf-8"))}
    kept = [r for r in sel["kept"] if r["key"] in docs]
    kept.sort(key=lambda r: (r["section"], -r["chars"], r["key"]))
    slug, used = {}, set()
    for r in kept:
        base, i = bs.slugify(os.path.splitext(r["key"])[0], 70), 2
        s = base
        while s in used:
            s = f"{base}-{i}"
            i += 1
        used.add(s)
        slug[r["key"]] = s

    axes = read_json(os.path.join(SITE, "data", "axes.json"), {"cats": [], "entries": []})
    meta = read_json(os.path.join(SITE, "data", "search", "meta.json"), {})
    assets = asset_map()

    # ------------------------------------------------------------- domaines
    by_cat = {}
    for e in axes["entries"]:
        by_cat.setdefault(e["cat"], []).append(e)
    cat_labels = {c["id"]: c["label"] for c in axes["cats"]}
    cat_desc = {c["id"]: c["desc"] for c in axes["cats"]}

    cards = []
    for c in axes["cats"]:
        es = sorted(by_cat.get(c["id"], []), key=lambda e: -e["occ"])
        sample = " ".join(
            f'<a class="chip" href="axes/{c["id"]}/{e["slug"]}.html">{esc(e["label"])}'
            f'<span class="n">{e["occ"]}</span></a>' for e in es[:6])
        cards.append(
            f'<article class="card"><h3><a href="axes/{c["id"]}.html">'
            f'{esc(c["label"])}</a> <span class="count">{c["n"]}</span></h3>'
            f'<p class="dim">{esc(c["desc"])}</p>'
            f'<p class="chips">{sample}</p></article>')
    domains = '<div class="cardgrid">' + "".join(cards) + "</div>"

    # -------------------------------------------------------------- dossiers
    dossier_cards, dossier_pages = [], []
    rnd = random.Random(7)
    for cat_id, label, intro in DOSSIERS:
        e = next((x for x in by_cat.get(cat_id, [])
                  if x["slug"] == slugify(label, 60)), None)
        if not e:
            log("dossier ignoré (entrée absente) :", label)
            continue
        steps = sorted(e["docs"].items(), key=lambda kv: -kv[1])[:9]
        rows = []
        for k, (di, occ) in enumerate(steps, 1):
            di = int(di)
            r = kept[di]
            rows.append(
                f'<li><span class="step">{k}</span>'
                f'<a href="../articles/{slug[r["key"]]}.html">{esc(r["title"])}</a>'
                f' <span class="dim">· {occ} mentions · '
                f'{esc(bs.SECTIONS.get(r["section"], ("Autres",))[0])}</span></li>')
        write_page(
            bs, os.path.join(SITE, "parcours", f"{e['slug']}.html"), label,
            f'<nav class="crumb"><a href="../index.html">Accueil</a> › '
            f'<a href="../parcours.html">Dossiers</a></nav>'
            f'<h1>{esc(label)}</h1><p class="lead">{esc(intro)}</p>'
            f'<p class="dim">{e["n"]} articles, {e["occ"]} mentions. '
            f'Les étapes vont du plus dense au plus rare.</p>'
            f'<ol class="steps">{"".join(rows)}</ol>'
            f'<p><a class="btn" href="../axes/{cat_id}/{e["slug"]}.html">'
            f'la fiche complète</a> '
            f'<a class="btn ghost" href="../recherche.html?ax={cat_id}/{e["slug"]}">'
            f'filtrer le corpus</a></p>', root="../")
        dossier_pages.append((e["slug"], label, intro, len(steps)))
        dossier_cards.append(
            f'<article class="card"><h3><a href="parcours/{e["slug"]}.html">'
            f'{esc(label)}</a></h3><p class="dim">{esc(intro)}</p>'
            f'<p class="dim">{len(steps)} étapes · {e["n"]} articles</p></article>')

    write_page(
        bs, os.path.join(SITE, "parcours.html"), "Dossiers de lecture",
        '<h1>Dossiers de lecture</h1>'
        '<p class="lead">Un sujet, et les textes où le lire, du plus dense au '
        'plus rare. Chaque étape est un article du corpus.</p>'
        '<div class="cardgrid">' + "".join(dossier_cards) + "</div>")

    # ----------------------------------------------------------------- plan
    total = sum(r["chars"] for r in kept)
    sec_rows = []
    for sid in ["1", "2", "3", "4", "5", "6", "7", "8", "DC", "9"]:
        items = [r for r in kept if r["section"] == sid]
        if not items:
            continue
        label = bs.SECTIONS.get(sid, ("Autres", ""))[0]
        sec_rows.append(
            f'<li><a href="sections/{sid.lower()}.html">{esc(label)}</a></li>')

    # --------------------------------------------------------------- portail
    def count(path):
        p = os.path.join(SITE, path)
        if not os.path.exists(p):
            return 0
        with open(p, encoding="utf-8") as f:
            return f.read().count("<li")

    # quelques planches pour l'entrée de page
    plates = []
    for r in sorted(kept, key=lambda x: -len(docs[x["key"]]["images"])):
        for im in docs[r["key"]]["images"][:1]:
            loc = local_of(im["src"], assets)
            if loc:
                plates.append((loc, r, slug[r["key"]]))
                break
        if len(plates) >= 8:
            break
    plate_html = "".join(
        f'<a href="articles/{sl}.html"><img src="assets/{loc}" loading="lazy" '
        f'alt=""></a>' for loc, r, sl in plates)

    write_page(
        bs, os.path.join(SITE, "index.html"), "Hervé Delboy — alchimie",
        '<section class="portal">'
        '<h1>Hervé Delboy<span> — alchimie</span></h1>'
        '<p class="lead">Les pages de son site, réunies.</p>'
        '<form action="recherche.html" method="get" class="bigsearch">'
        '<input name="q" placeholder="un traité, un auteur, une notion…" '
        'autocomplete="off" aria-label="Rechercher">'
        '<button>Chercher</button></form>'
        '<p class="dim"><a href="recherche.html?mode=question">poser une '
        'question</a> · <a href="#" id="hasard">une page au hasard</a></p>'
        '</section>'

        '<a class="orig" href="original/accueil.html">'
        '<strong>Sa page d’accueil</strong>'
        '<span>telle qu’elle était, avec ses entrées</span></a>'

        f'<div class="plates">{plate_html}</div>'

        '<h2>Le plan</h2><ul class="list">' + "".join(sec_rows) + '</ul>'

        '<h2>Les textes</h2>'
        '<p><a href="textes.html">Les traités transcrits</a></p>'

        '<h2>Index</h2><ul class="list quiet">'
        '<li><a href="notions.html">Notions, substances, opérations</a></li>'
        '<li><a href="noms.html">Noms</a></li>'
        '<li><a href="mots.html">Concordance</a></li>'
        '<li><a href="symboles.html">Symboles</a></li>'
        '<li><a href="guide.html">Tous les index</a></li></ul>'

        '<h2>Planches</h2>'
        '<p><a href="illustrations.html">Les figures du corpus</a></p>'

        '<h2>Dossiers</h2><ul class="list quiet">' +
        "".join(f'<li><a href="parcours/{sl}.html">{esc(lab)}</a></li>'
                for sl, lab, intro, n in dossier_pages) + '</ul>' +

        '<script>document.getElementById("hasard").addEventListener("click",'
        ' function(e){e.preventDefault();'
        'fetch("data/search/meta.json").then(function(r){return r.json()})'
        '.then(function(m){var d=m.docs[Math.floor(Math.random()*m.docs.length)];'
        'location.href="articles/"+d.s+".html";});});</script>')

    # ----------------------------------------------------------------- guide
    idx = [
        ("plan.html", "Le plan"),
        ("index-general.html", "Les titres"),
        ("notions.html", "Les notions"),
        ("noms.html", "Les noms"),
        ("mots.html", "La concordance"),
        ("symboles.html", "Les symboles"),
        ("illustrations.html", "Les planches"),
        ("textes.html", "Les textes"),
        ("parcours.html", "Les dossiers"),
        ("axes.html", "Les domaines"),
    ]
    guide_rows = "".join(
        f'<li><a href="{h}">{esc(t)}</a></li>' for h, t in idx)
    write_page(
        bs, os.path.join(SITE, "guide.html"), "Index",
        '<h1>Index</h1><ul class="list guide">' + guide_rows + '</ul>')

    log(f"portail : {len(kept)} pages, {len(dossier_pages)} dossiers, "
        f"{len(axes['entries'])} entrées d'autorité")


if __name__ == "__main__":
    main()
