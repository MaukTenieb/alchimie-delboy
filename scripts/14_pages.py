"""Étape 14 : notice, pages perdues, pages écartées, symboles, 404 — même
gabarit que le sommaire, textes réduits aux faits. À lancer depuis la racine."""
from __future__ import annotations

import importlib.util
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
spec = importlib.util.spec_from_file_location("lec", os.path.join(ROOT, "scripts", "13_lecture.py"))
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)

NOTICE = """<h1>Notice</h1>
<p class="facts">247 pages · dix sections · 3 002 images · dix livres PDF</p>
<table class="data">
<tr><th>Adresse d'origine</th><th>Captures, Wayback Machine</th></tr>
<tr><td><code>http://perso.club-internet.fr/hdelboy/</code></td><td>novembre 1999 – septembre 2009</td></tr>
<tr><td><code>http://herve.delboy.perso.sfr.fr/</code></td><td>août 2009 – novembre 2016</td></tr>
</table>
<table class="data">
<tr><th>Pages</th><th class="n">Nombre</th></tr>
<tr><td><a href="sommaire.html">Pages d'alchimie</a></td><td class="n">247</td></tr>
<tr><td><a href="hors-perimetre.html">Pages écartées</a> : astrologie, musique, échecs, statistiques, pages personnelles</td><td class="n">88</td></tr>
<tr><td><a href="lacunes.html">Pages citées, archivées vides</a></td><td class="n">45</td></tr>
</table>
<p class="facts">Interventions : encodage des caractères · liens et images rendus locaux · barre de lecture</p>
"""


def main_of(path: str) -> str:
    t = open(path, encoding="utf-8").read()
    return t[t.index("<main>") + 6:t.index("</main>")]


def write(name: str, title: str, body: str) -> None:
    open(os.path.join(SITE, name), "w", encoding="utf-8").write(lec.page(title, body, ""))


def main() -> None:
    write("notice.html", "Notice — Hervé Delboy, alchimie", NOTICE)

    b = main_of(os.path.join(SITE, "hors-perimetre.html"))
    b = re.sub(r'<p class="(?:lead|facts)">.*?</p>',
               '<p class="facts">88 pages : astrologie (directions primaires, transits, statistiques), '
               'musique, échecs, logiciels de statistiques, pages personnelles</p>', b, count=1, flags=re.S)
    b = re.sub(r"<h1>[^<]*</h1>", "<h1>Pages écartées</h1>", b, count=1)
    write("hors-perimetre.html", "Pages écartées — Hervé Delboy, alchimie", b)

    b = main_of(os.path.join(SITE, "lacunes.html"))
    b = re.sub(r"(</h2>)\s*<p class=\"dim\">.*?</p>", r"\1", b, flags=re.S)
    b = b.replace(' <span class="dim">(aucune capture exploitable (page d&#x27;erreur ou absente))</span>', "")
    n = [len(re.findall(r"<li>", part.split("</ul>")[0])) for part in b.split("<h2")[1:]]
    b = re.sub(r"<h2>([^<(]*?)\s*\(\d+\)</h2>", r"<h2>\1</h2>", b)
    b = re.sub(r'<p class="(?:lead|facts)">.*?</p>',
               f'<p class="facts">45 pages citées, archivées vides : page d\'erreur de Club-Internet, servie avec le code HTTP 200 · '
               f'retrouvées : {n[0]} · anciennes adresses : {n[1]} · perdues : {n[2]}</p>', b, count=1, flags=re.S)
    b = re.sub(r"<h1>[^<]*</h1>", "<h1>Pages perdues</h1>", b, count=1)
    b = b.replace("<h2>Anciennes adresses d'une page présente</h2>", "<h2>Anciennes adresses</h2>")
    b = b.replace("</code> — Club-Internet : Erreur 404", "</code>").replace("</code> — <br>", "</code><br>")
    b = re.sub(r"retrouvée via wayback (\d{4})(\d\d)(\d\d)(\d{6}) (\S+) \(\d+ octets\)",
               r'Wayback Machine, <a href="https://web.archive.org/web/\1\2\3\4/\5">\3/\2/\1</a>', b)
    b = re.sub(r"retrouvée via commoncrawl CC-MAIN-(\d{4})-\d+ \S+ \(\d+ octets\)", r"Common Crawl, \1", b)
    b = re.sub(r' <span class="dim">\(<code>[^<]*</code>, même page\)</span>', "", b)
    b = b.replace('href="articles/', 'href="original/')
    write("lacunes.html", "Pages perdues — Hervé Delboy, alchimie", b)

    b = main_of(os.path.join(SITE, "symboles.html"))
    b = re.sub(r'<p class="(?:lead|facts)">.*?</p>',
               '<p class="facts">90 entrées · source : '
               '<a href="original/symboles-alchimiques.html">symboles alchimiques</a></p>',
               b, count=1, flags=re.S)
    write("symboles.html", "Symboles — Hervé Delboy, alchimie", b)

    write("404.html", "Page absente — Hervé Delboy, alchimie",
          '<h1>Page absente</h1><p class="facts"><a href="/alchimie-delboy/sommaire.html">Sommaire</a> · '
          '<a href="/alchimie-delboy/lacunes.html">pages perdues</a></p>')
    p = os.path.join(SITE, "404.html")
    h = open(p, encoding="utf-8").read().replace("<head>", '<head><base href="/alchimie-delboy/">', 1)
    open(p, "w", encoding="utf-8").write(h)
    print("ok")


if __name__ == "__main__":
    main()
