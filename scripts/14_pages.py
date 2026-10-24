"""Étape 14 : notice, pages manquantes, pages écartées, symboles, 404 — même
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
<table class="data notice">
<tr><th>Auteur</th><td>Hervé Delboy</td></tr>
<tr><th>Contenu</th><td><a href="sommaire.html">248 pages</a> sur l'alchimie, dix sections dans l'ordre de son plan · 3 055 images · dix livres PDF</td></tr>
<tr><th>Adresses d'origine</th><td><code>perso.club-internet.fr/hdelboy</code>, 1999-2009 · <code>herve.delboy.perso.sfr.fr</code>, 2009-2016</td></tr>
<tr><th>Source</th><td>Wayback Machine (Internet Archive), captures de 2001 à 2016 ; Common Crawl, une page</td></tr>
<tr><th>Pages écartées</th><td><a href="hors-perimetre.html">87</a> : astrologie, musique, échecs, statistiques, pages personnelles</td></tr>
<tr><th>Pages manquantes</th><td><a href="lacunes.html">21</a>, à retrouver</td></tr>
<tr><th>Corpus</th><td><a href="corpus.html">textes alchimiques libres de droits</a>, de Zosime à Cyliani, avec leurs copies numérisées</td></tr>
<tr><th>Interventions</th><td>encodage des caractères · liens et images en local · barre de lecture</td></tr>
</table>
"""


def main_of(path: str) -> str:
    t = open(path, encoding="utf-8").read()
    return t[t.index("<main>") + 6:t.index("</main>")]


def write(name: str, title: str, body: str) -> None:
    open(os.path.join(SITE, name), "w", encoding="utf-8").write(lec.page(title, body, ""))


OUT = re.compile(r"<code>(troitzky[^<]*|rinck_2\.htm|havel_2\.htm|divers\.htm|page3\.htm|dp_ex_celebr\.htm|histoire\+des\+directions\+primaires\.html|article\+complet\+pour\+l&#x27;astrologue\.html)</code>")


def main() -> None:
    write("notice.html", "Notice — Hervé Delboy, alchimie", NOTICE)

    b = main_of(os.path.join(SITE, "lacunes.html"))
    b = re.sub(r"(</h2>)\s*<p class=\"dim\">.*?</p>", r"\1", b, flags=re.S)
    b = b.replace(' <span class="dim">(aucune capture exploitable (page d&#x27;erreur ou absente))</span>', "")
    # titres vides ou répétant le nom du fichier
    b = re.sub(r"<code>([^<]+?)\.html?</code> — (\1|index2|Untitled Document)\s*(?=<|$)", r"<code>\1.htm</code>", b)
    b = re.sub(r"<h2>([^<(]*?)\s*\(\d+\)</h2>", r"<h2>\1</h2>", b)
    # gobineau.html, relevée en 2015 par un blog (recherchestraditions.blogspot.com), retrouvée le 24 oct. 2026 (Captures) : site/original/gobineau.html
    # le lecteur garde la seule liste des pages à retrouver
    ul = re.search(r'(?:<h2>(?:Perdues|À retrouver)</h2>\s*)?(<ul class="list mono">.*?</ul>)', b, re.S).group(1)
    # liens vers les échecs, l'astrologie, la musique : rangés avec les pages écartées (décision du 24 oct. 2026)
    lis = re.findall(r"<li>.*?</li>", ul, re.S)
    moved = [x for x in lis if OUT.search(x)]
    ul = '<ul class="list mono">' + "".join(x for x in lis if not OUT.search(x)) + "</ul>"
    n = len(re.findall(r"<li>", ul))
    b = (f'<h1>Pages manquantes <span class="sub">à retrouver — aidez-nous</span></h1>'
         f'<p class="facts">{n} pages : liens du site d\'origine, captures vides (page d\'erreur de Club-Internet, code HTTP 200)</p>'
         '<p class="facts">Une copie, un cache, une sauvegarde de l\'une de ces pages : mauktenieb chez Gmail.</p>' + ul)
    write("lacunes.html", "Pages manquantes — Hervé Delboy, alchimie", b)

    b = main_of(os.path.join(SITE, "hors-perimetre.html")).strip()
    # gobineau.html, retrouvée et rangée dans la section Douze Clefs (24 oct. 2026)
    b = re.sub(r"<li><code>gobineau\.html</code>.*?</li>", "", b)
    ne = len(re.findall(r"<li>", re.search(r'<ul class="list mono">.*?</ul>', b, re.S).group(0)))
    b = re.sub(r'<p class="(?:lead|facts)">.*?</p>',
               f'<p class="facts">{ne} pages : astrologie (directions primaires, transits, statistiques), '
               'musique, échecs, logiciels de statistiques, pages personnelles</p>', b, count=1, flags=re.S)
    b = re.sub(r"<h1>[^<]*</h1>", "<h1>Pages écartées</h1>", b, count=1)
    old = re.search(r"<!--manquantes-->(.*?)<!--/manquantes-->", b, re.S)
    if old:
        moved = moved or re.findall(r"<li>.*?</li>", old.group(1), re.S)
        b = b.replace(old.group(0), "")
    if moved:
        b += ("<!--manquantes--><p class=\"facts\">" + str(len(moved)) + " pages manquantes hors alchimie : liens du site d'origine, "
              "captures vides</p><ul class=\"list mono\">" + "".join(sorted(moved)) + "</ul><!--/manquantes-->")
    write("hors-perimetre.html", "Pages écartées — Hervé Delboy, alchimie", b)

    b = main_of(os.path.join(SITE, "symboles.html")).strip()
    b = re.sub(r'<p class="(?:lead|facts)">.*?</p>',
               '<p class="facts">90 entrées · source : '
               '<a href="original/symboles-alchimiques.html">symboles alchimiques</a></p>',
               b, count=1, flags=re.S)
    write("symboles.html", "Symboles — Hervé Delboy, alchimie", b)

    write("404.html", "Page absente — Hervé Delboy, alchimie",
          '<h1>Page absente</h1><p class="facts"><a href="/alchimie-delboy/sommaire.html">Sommaire</a> · '
          '<a href="/alchimie-delboy/lacunes.html">pages manquantes</a></p>')
    p = os.path.join(SITE, "404.html")
    h = open(p, encoding="utf-8").read().replace("<head>", '<head><base href="/alchimie-delboy/">', 1)
    open(p, "w", encoding="utf-8").write(h)
    print("ok")


if __name__ == "__main__":
    main()
