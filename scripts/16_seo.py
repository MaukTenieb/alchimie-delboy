"""Étape 16 : couche lue par les moteurs de recherche et de réponse.

- pages de l'auteur : <title> lisible, description, adresse canonique, Open Graph,
  données structurées (schema.org CreativeWork : auteur, section, révision,
  capture d'archive) ; le corps de la page reste intact ;
- pages de consultation : description, adresse canonique, Open Graph ;
  écran titre : WebSite et SearchAction ; sommaire : liste des 248 pages ;
- anciennes adresses (renvois) et 404 : noindex ;
- site/sitemap.xml et site/llms.txt.

Chaque bloc ajouté se trouve entre <!--seo--> et <!--/seo--> : une nouvelle
passe le remplace. À lancer depuis la racine du dépôt : python scripts/16_seo.py
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
BASE = "https://mauktenieb.github.io/alchimie-delboy/"
NAME = "Hervé Delboy — alchimie"
MONTHS = {m: i + 1 for i, m in enumerate(
    "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split())}
MONTHS.update({"fevrier": 2, "aout": 8, "decembre": 12})
AUTHOR = {"@type": "Person", "name": "Hervé Delboy"}
SITE_LD = {"@type": "WebSite", "@id": BASE + "#site", "name": NAME, "url": BASE, "inLanguage": "fr"}


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def iso(rev: str) -> str:
    m = re.match(r"(\d{1,2})(?:er)?\s+(\w+)\s+(\d{4})", rev or "")
    if not m or m.group(2).lower() not in MONTHS:
        return ""
    return f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"


def block(title: str, desc: str, url: str, kind: str, image: str = "", ld: dict | None = None,
          robots: str = "") -> str:
    out = [f'<meta name="description" content="{esc(desc)}">',
           f'<link rel="canonical" href="{esc(url)}">',
           f'<meta property="og:type" content="{kind}">',
           f'<meta property="og:title" content="{esc(title)}">',
           f'<meta property="og:description" content="{esc(desc)}">',
           f'<meta property="og:url" content="{esc(url)}">',
           f'<meta property="og:site_name" content="{esc(NAME)}">',
           '<meta property="og:locale" content="fr_FR">']
    if image:
        out.append(f'<meta property="og:image" content="{esc(image)}">')
    if robots:
        out.append(f'<meta name="robots" content="{robots}">')
    if ld:
        out.append('<script type="application/ld+json">' +
                   json.dumps({"@context": "https://schema.org", **ld}, ensure_ascii=False).replace("</", "<\\/") +
                   "</script>")
    return "<!--seo-->" + "".join(out) + "<!--/seo-->"


def put(path: str, seo: str, title: str | None = None) -> None:
    b = open(path, "rb").read().decode("utf-8", errors="surrogateescape")
    b = re.sub(r"<!--seo-->.*?<!--/seo-->", "", b, flags=re.S)
    if title is not None:
        b, n = re.subn(r"<title>.*?</title>", "<title>" + esc(title) + "</title>", b, count=1, flags=re.S | re.I)
        if not n:
            seo = "<title>" + esc(title) + "</title>" + seo
    head = b[:m0.start()] if (m0 := re.search(r"</head>", b, re.I)) else ""
    # une balise déjà posée par l'auteur reste la sienne : la nôtre s'efface
    for pat, ours in ((r'<meta[^>]+name=["\']?description', r'<meta name="description"[^>]*>'),
                      (r'rel=["\']?canonical', r'<link rel="canonical"[^>]*>'),
                      (r'property=["\']?og:title', r'<meta property="og:title"[^>]*>')):
        if re.search(pat, head, re.I):
            seo = re.sub(ours, "", seo, count=1)
    m = re.search(r"</head>", b, re.I)
    b = b[:m.start()] + seo + b[m.start():] if m else seo + b
    open(path, "wb").write(b.encode("utf-8", errors="surrogateescape"))


def main() -> None:
    nav = json.load(open(os.path.join(SITE, "data", "nav.json"), encoding="utf-8"))
    pages = json.load(open(os.path.join(SITE, "data", "pages.json"), encoding="utf-8"))
    secs = nav["sections"]
    today = datetime.date.today().isoformat()
    urls = []

    # pages de l'auteur
    for s, (title, sid, _p, _n) in nav["pages"].items():
        info = pages.get(s, {})
        sec = secs[sid][0]
        n_img = len(info.get("imgs", []))
        rev = info.get("rev", "")
        desc = (f"« {title} », page d'Hervé Delboy sur l'alchimie, section « {sec} » : texte intégral"
                + (f", {n_img} image{'s' if n_img > 1 else ''}" if n_img else "")
                + (f", révision du {rev}" if rev else "") + ".")
        url = f"{BASE}original/{s}.html"
        img = f"{BASE}assets/{info['imgs'][0]}" if info.get("imgs") else ""
        ld = {"@type": "CreativeWork", "name": title, "url": url, "author": AUTHOR, "inLanguage": "fr",
              "about": "Alchimie", "genre": sec, "isPartOf": SITE_LD}
        if iso(rev):
            ld["dateModified"] = iso(rev)
        if info.get("ts") and info.get("u"):
            ld["archivedAt"] = f"https://web.archive.org/web/{info['ts']}/{info['u']}"
        if img:
            ld["image"] = img
        put(os.path.join(SITE, "original", s + ".html"),
            block(title, desc, url, "article", img, ld), f"{title} — Hervé Delboy, alchimie")
        if s != "intro-alchimie":  # sa réplique double l'écran titre, qui porte l'adresse canonique
            urls.append((url, today))

    # écran titre
    desc = ("Le site d'Hervé Delboy sur l'alchimie, années 2000, remis en ligne : 248 pages en dix sections, "
            "dont les Douze Clefs de philosophie, le Mutus Liber, l'Atalanta fugiens, le dictionnaire des "
            "symboles alchimiques et les traités transcrits ; 3 055 planches, recherche en texte intégral, "
            "dix livres PDF.")
    ld = {"@graph": [
        {**SITE_LD, "description": desc, "author": AUTHOR,
         "potentialAction": {"@type": "SearchAction", "target": BASE + "recherche.html?q={q}",
                             "query-input": "required name=q"}},
        {"@type": "Person", "name": "Hervé Delboy",
         "sameAs": ["https://web.archive.org/web/2016/http://herve.delboy.perso.sfr.fr/"]}]}
    put(os.path.join(SITE, "index.html"),
        block(NAME + " · La clef du labyrinthe hermétique", desc, BASE, "website",
              BASE + "assets/" + (pages.get("intro-alchimie", {}).get("imgs") or [""])[0] if pages.get("intro-alchimie", {}).get("imgs") else "",
              ld), NAME + " · La clef du labyrinthe hermétique")
    urls.insert(0, (BASE, today))
    # la réplique d'intro-alchimie double l'écran titre
    put(os.path.join(SITE, "original", "intro-alchimie.html"),
        block("Introduction à l'alchimie — Hervé Delboy", desc, BASE, "website"))

    # pages de consultation
    cj = json.load(open(os.path.join(ROOT, "corpus", "corpus.json"), encoding="utf-8"))
    NC = len(cj)
    NL = sum(len(t.get("copies") or []) for t in cj)
    con = {
        "sommaire.html": ("Sommaire — " + NAME,
                          "Les 248 pages d'Hervé Delboy sur l'alchimie dans l'ordre de son plan, en dix sections : "
                          "date de révision, caractères, images, capture d'archive, livre PDF de chaque section."),
        "recherche.html": ("Recherche — " + NAME,
                           "Recherche en texte intégral dans les 18 427 passages des pages d'Hervé Delboy sur "
                           "l'alchimie : expression exacte, préfixe, exclusion, section, titre."),
        "symboles.html": ("Symboles alchimiques — " + NAME,
                          "Dictionnaire des symboles alchimiques et spagyriques d'Hervé Delboy : 90 entrées, de "
                          "l'acide à la vitriolisation, avec leurs hiéroglyphes."),
        "notice.html": ("Notice — " + NAME,
                        "Notice du site d'Hervé Delboy sur l'alchimie : auteur, contenu, adresses d'origine "
                        "(perso.club-internet.fr/hdelboy, herve.delboy.perso.sfr.fr), source, pages manquantes."),
        "lacunes.html": ("Pages manquantes — " + NAME,
                         "Pages manquantes du site d'Hervé Delboy sur l'alchimie, à retrouver : 21 "
                         "noms de fichiers. Une copie ou un cache : mauktenieb chez Gmail."),
        "corpus.html": ("Corpus alchimique libre de droits — " + NAME,
                        f"Corpus de {NC} textes alchimiques libres de droits, de Zosime à Cyliani : éditions "
                        f"anciennes et {NL} copies numérisées gratuites, d'après Calvet, Poisson, Pereira et Bonardel."),
        "hors-perimetre.html": ("Pages écartées — " + NAME,
                                "Pages du site d'Hervé Delboy hors alchimie : astrologie, musique, échecs, "
                                "logiciels de statistiques, pages personnelles."),
    }
    for sid, (label, pdf, size) in secs.items():
        n = sum(1 for v in nav["pages"].values() if v[1] == sid)
        con[f"sections/{sid}.html"] = (f"{label} — {NAME}",
                                       f"{label} : {n} page{'s' if n > 1 else ''} d'Hervé Delboy sur l'alchimie"
                                       + (f", livre PDF de la section ({size})" if pdf else "") + ".")
    for rel, (title, desc) in con.items():
        ld = None
        if rel == "sommaire.html":
            seq = list(nav["pages"])
            ld = {"@type": "CollectionPage", "name": title, "url": BASE + rel, "isPartOf": SITE_LD,
                  "mainEntity": {"@type": "ItemList", "numberOfItems": len(seq), "itemListElement": [
                      {"@type": "ListItem", "position": i + 1, "url": f"{BASE}original/{s}.html",
                       "name": nav["pages"][s][0]} for i, s in enumerate(seq)]}}
        put(os.path.join(SITE, rel), block(title, desc, BASE + rel, "website", "", ld))
        urls.append((BASE + rel, today))

    # renvois et 404 : hors index
    stubs = [os.path.join("articles", f) for f in os.listdir(os.path.join(SITE, "articles"))]
    stubs += [f for f in ("portail.html", "plan.html", "guide.html", "index-general.html", "mots.html", "noms.html",
                          "axes.html", "notions.html", "parcours.html", "method.html", "liseuse.html", "textes.html",
                          "illustrations.html") if os.path.exists(os.path.join(SITE, f))]
    for rel in stubs:
        p = os.path.join(SITE, rel)
        b = open(p, encoding="utf-8").read()
        b = re.sub(r"<!--seo-->.*?<!--/seo-->", "", b, flags=re.S)
        b = b.replace("<head>", '<head><!--seo--><meta name="robots" content="noindex,follow"><!--/seo-->', 1)
        open(p, "w", encoding="utf-8").write(b)
    p = os.path.join(SITE, "404.html")
    b = re.sub(r"<!--seo-->.*?<!--/seo-->", "", open(p, encoding="utf-8").read(), flags=re.S)
    open(p, "w", encoding="utf-8").write(b.replace("<head>", '<head><!--seo--><meta name="robots" content="noindex"><!--/seo-->', 1))

    # plan du site
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u, d in urls:
            f.write(f"<url><loc>{esc(u)}</loc><lastmod>{d}</lastmod></url>\n")
        f.write("</urlset>\n")

    # llms.txt
    lines = [f"# {NAME}", "",
             "> Le site d'Hervé Delboy sur l'alchimie, années 2000, remis en ligne depuis les captures de la "
             "Wayback Machine : 248 pages en dix sections, dans l'ordre de son plan. Textes et images : © Hervé Delboy.",
             "", f"- [Écran titre : La clef du labyrinthe hermétique]({BASE})",
             f"- [Sommaire]({BASE}sommaire.html)", f"- [Recherche]({BASE}recherche.html)",
             f"- [Dictionnaire des symboles alchimiques]({BASE}symboles.html)", f"- [Notice]({BASE}notice.html)",
             f"- [Corpus alchimique libre de droits : {NC} textes, {NL} copies numérisées]({BASE}corpus.html)", ""]
    for sid, (label, pdf, size) in secs.items():
        lines.append(f"## {label}")
        lines.append("")
        if pdf:
            lines.append(f"- [Livre PDF de la section, {size}]({BASE}{pdf})")
        for s, v in nav["pages"].items():
            if v[1] == sid:
                lines.append(f"- [{v[0]}]({BASE}original/{s}.html)")
        lines.append("")
    open(os.path.join(SITE, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines))
    print(len(urls), "adresses dans le plan du site ;", len(stubs), "renvois en noindex")


if __name__ == "__main__":
    main()
