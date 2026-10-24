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
<p class="facts">Le site d'Hervé Delboy sur l'alchimie, années 2000 : 247 pages en
dix sections, dans l'ordre de son plan, 3 002 images, dix livres PDF. Remise en
ligne par Mauk Tenieb, 2026.</p>
<h2>Provenance</h2>
<table class="data">
<tr><th>Adresse d'origine</th><th>Captures</th></tr>
<tr><td><code>http://perso.club-internet.fr/hdelboy/</code></td><td>novembre 1999 – septembre 2009</td></tr>
<tr><td><code>http://herve.delboy.perso.sfr.fr/</code></td><td>août 2009 – novembre 2016</td></tr>
</table>
<p>Les deux adresses ont disparu. Les pages viennent des captures de l'Internet Archive
(Wayback Machine) ; le <a href="sommaire.html">sommaire</a> donne, pour chaque page,
la date de sa capture et le lien vers elle.</p>
<table class="data">
<tr><th>Pages</th><th class="n">Nombre</th></tr>
<tr><td>Pages d'alchimie reconstituées</td><td class="n">247</td></tr>
<tr><td><a href="hors-perimetre.html">Pages écartées</a> (astrologie, musique, échecs, statistiques, pages personnelles)</td><td class="n">88</td></tr>
<tr><td><a href="lacunes.html">Pages citées, archivées vides</a></td><td class="n">45</td></tr>
</table>
<h2>Fidélité</h2>
<p>Chaque page reprend la page de l'auteur : graphies, coupures de mots, coquilles,
mise en page. La reconstitution intervient sur l'encodage des caractères, sur les
liens et les images, rendus locaux, et ajoute une barre de lecture en tête de page.</p>
<h2>Droits</h2>
<p>Textes, transcriptions, traductions, notices, mises en page et images : l'œuvre
d'Hervé Delboy et des auteurs qu'il citait, protégée par le droit d'auteur,
propriété de leurs auteurs et de leurs ayants droit.</p>
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
               '<p class="facts">88 pages du site d\'origine traitent d\'autres domaines et restent hors de la reconstitution : '
               'astrologie (directions primaires, transits, statistiques), musique, échecs, '
               'logiciels de statistiques, pages personnelles.</p>', b, count=1, flags=re.S)
    b = re.sub(r"<h1>[^<]*</h1>", "<h1>Pages écartées</h1>", b, count=1)
    write("hors-perimetre.html", "Pages écartées — Hervé Delboy, alchimie", b)

    b = main_of(os.path.join(SITE, "lacunes.html"))
    b = re.sub(r'<p class="lead">.*?</p>',
               '<p class="facts">45 pages référencées par le site d\'origine, archivées vides : '
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
