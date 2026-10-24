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
<h2>Provenance</h2>
<table class="data">
<tr><th>Adresse d'origine</th><th>Captures</th></tr>
<tr><td><code>http://perso.club-internet.fr/hdelboy/</code></td><td>novembre 1999 – septembre 2009</td></tr>
<tr><td><code>http://herve.delboy.perso.sfr.fr/</code></td><td>août 2009 – novembre 2016</td></tr>
</table>
<p>Les deux adresses sont hors ligne. Les pages proviennent de l'Internet Archive
(Wayback Machine) ; le <a href="sommaire.html">sommaire</a> donne la date de la capture
de chaque page et le lien vers cette capture.</p>
<table class="data">
<tr><th>Pages</th><th class="n">Nombre</th></tr>
<tr><td>Pages d'alchimie reconstituées</td><td class="n">247</td></tr>
<tr><td><a href="hors-perimetre.html">Pages écartées</a> (astrologie, musique, échecs, statistiques, pages personnelles)</td><td class="n">88</td></tr>
<tr><td><a href="lacunes.html">Pages référencées sans contenu archivé</a></td><td class="n">45</td></tr>
</table>
<h2>Fidélité</h2>
<p>Les pages sont données telles que l'auteur les a établies : graphies, coupures
de mots, coquilles, mise en page. Interventions : encodage des caractères, liens
et images rendus locaux, une ligne de navigation en tête de page.</p>
<h2>Droits</h2>
<p>Les textes, transcriptions, traductions, notices, mises en page et images
reproduits ici sont l'œuvre d'Hervé Delboy ou des auteurs qu'il citait. Ils
demeurent protégés par le droit d'auteur et appartiennent à leurs auteurs et à
leurs ayants droit.</p>
<p>Cette reconstitution constitue un usage de consultation, de recherche et de
conservation : elle ne fait l'objet d'aucune vente, d'aucune diffusion
publicitaire, d'aucune exploitation commerciale.</p>
<p>Toute demande d'un auteur ou d'un ayant droit — retrait d'une page ou d'une
image, correction d'une mention, précision de crédit — sera suivie d'effet sans
délai.</p>
<h2>Outils</h2>
<p><a href="sommaire.html">Sommaire</a> dans l'ordre du plan de l'auteur ·
<a href="recherche.html">recherche</a> en texte intégral · <a href="symboles.html">dictionnaire
des symboles</a> de l'auteur · un PDF par section · sur chaque page : taille du
texte, loupe, impression ou PDF, EPUB.</p>
"""


def main_of(path: str) -> str:
    t = open(path, encoding="utf-8").read()
    return t[t.index("<main>") + 6:t.index("</main>")]


def write(name: str, title: str, body: str) -> None:
    open(os.path.join(SITE, name), "w", encoding="utf-8").write(lec.page(title, body, ""))


def main() -> None:
    write("notice.html", "Notice — Hervé Delboy, alchimie", NOTICE)

    b = main_of(os.path.join(SITE, "hors-perimetre.html"))
    b = re.sub(r'<p class="lead">.*?</p>',
               '<p class="facts">88 pages du site d\'origine, hors de la reconstitution : '
               'astrologie (directions primaires, transits, statistiques), musique, échecs, '
               'logiciels de statistiques, pages personnelles.</p>', b, count=1, flags=re.S)
    b = re.sub(r"<h1>[^<]*</h1>", "<h1>Pages écartées</h1>", b, count=1)
    write("hors-perimetre.html", "Pages écartées — Hervé Delboy, alchimie", b)

    b = main_of(os.path.join(SITE, "lacunes.html"))
    b = re.sub(r'<p class="lead">.*?</p>',
               '<p class="facts">45 pages référencées par le site d\'origine, archivées sans contenu : '
               'l\'hébergeur Club-Internet renvoyait sa page d\'erreur avec le code HTTP 200. '
               'Retrouvées : 5 · anciennes adresses d\'une page présente : 6 · perdues : 34.</p>',
               b, count=1, flags=re.S)
    b = re.sub(r"<h1>[^<]*</h1>", "<h1>Pages perdues</h1>", b, count=1)
    write("lacunes.html", "Pages perdues — Hervé Delboy, alchimie", b)

    b = main_of(os.path.join(SITE, "symboles.html"))
    b = re.sub(r'<p class="lead">.*?</p>',
               '<p class="facts">90 entrées, indexées par l\'auteur dans ses planches · source : '
               '<a href="original/symboles-alchimiques.html">symboles alchimiques</a>.</p>',
               b, count=1, flags=re.S)
    write("symboles.html", "Symboles — Hervé Delboy, alchimie", b)

    write("404.html", "Page absente — Hervé Delboy, alchimie",
          '<h1>Page absente</h1><p class="facts">Adresse absente de la reconstitution. '
          'Voir les <a href="/alchimie-delboy/lacunes.html">pages perdues</a> et le '
          '<a href="/alchimie-delboy/sommaire.html">sommaire</a>.</p>')
    p = os.path.join(SITE, "404.html")
    h = open(p, encoding="utf-8").read().replace("<head>", '<head><base href="/alchimie-delboy/">', 1)
    open(p, "w", encoding="utf-8").write(h)
    print("ok")


if __name__ == "__main__":
    main()
