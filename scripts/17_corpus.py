"""Étape 17 : corpus des textes alchimiques libres de droits.
Lit corpus/corpus.json, écrit site/corpus.html. À lancer depuis la racine."""
from __future__ import annotations

import html
import importlib.util
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
spec = importlib.util.spec_from_file_location("lec", os.path.join(ROOT, "scripts", "13_lecture.py"))
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)

E = html.escape
ERAS = [("A", "Antiquité grecque"), ("B", "Réception arabe, corpus arabo-latins"),
        ("C", "Alchimie latine, XIIIe-XVe siècle"), ("D", "XVIe-XIXe siècle")]
LISTES = {"calvet": "Calvet", "poisson": "Poisson", "pereira": "Pereira", "bonardel": "Bonardel"}

HEAD = """<h1>Corpus <span class="sub">textes alchimiques libres de droits</span></h1>
<p class="facts">{n} textes · {c} copies numérisées gratuites · liens contrôlés chaque semaine</p>
<p class="facts">Listes de départ : Antoine Calvet, <i>L'Alchimie au Moyen Âge</i> (Vrin, 2018) ·
Albert Poisson, <i>Théories et symboles des alchimistes</i> (1891), introduction ·
Michela Pereira (dir.), <i>Alchimia. I testi della tradizione occidentale</i> (Mondadori, 2006) ·
Françoise Bonardel (dir.), <i>Philosopher par le feu</i> (Seuil, 1995).</p>
<p class="facts">Par texte : éditions anciennes imprimées, copies numérisées des bibliothèques, éditions critiques modernes en référence.</p>
<p><input id="cf" type="search" placeholder="Filtrer : auteur, titre, bibliothèque" aria-label="Filtrer le corpus" style="width:100%;max-width:32rem;padding:.4rem;font:inherit"></p>
"""

FOOT = ('<footer class="foot"><p>Corpus dressé par Mauk Tenieb à partir des quatre listes citées. '
        'Copies numérisées : les bibliothèques nommées sur chaque fiche, qui les hébergent. '
        'Contact : mauktenieb chez Gmail.</p></footer>')

SCRIPT = """<script>
(function(){var i=document.getElementById('cf');if(!i)return;
i.addEventListener('input',function(){var q=i.value.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
document.querySelectorAll('.fiche').forEach(function(f){var t=f.textContent.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');
f.hidden=q&&t.indexOf(q)<0;});});})();
</script>"""


def fiche(t: dict) -> str:
    out = [f'<article class="fiche" id="{E(t["id"])}">',
           f'<h3>{E(t["auteur"])} — <i>{E(t["titre"])}</i></h3>']
    meta = [x for x in (t.get("titre_original"), t.get("langue"), t.get("date")) if x]
    ls = [LISTES[x] for x in t.get("listes", []) if x in LISTES]
    if ls:
        meta.append("cité par " + ", ".join(ls))
    out.append(f'<p class="dim">{E(" · ".join(meta))}</p>')
    eds = t.get("editions_anciennes") or []
    if eds:
        out.append('<p><b>Éditions anciennes</b></p><ul class="list quiet">'
                   + "".join(f"<li>{E(e['ref'])}</li>" for e in eds) + "</ul>")
    cps = t.get("copies") or []
    if cps:
        out.append('<p><b>Copies numérisées</b></p><ul class="list quiet">'
                   + "".join(f'<li><a href="{E(c["url"])}">{E(c["bib"])}</a> — {E(c.get("edition", ""))}</li>'
                             for c in cps) + "</ul>")
    trs = t.get("traductions_fr_anciennes") or []
    if trs:
        out.append('<p><b>Traductions françaises anciennes</b></p><ul class="list quiet">'
                   + "".join(f'<li>{E(x["ref"])}' + (f' — <a href="{E(x["url"])}">copie</a>' if x.get("url") else "")
                             + "</li>" for x in trs) + "</ul>")
    crit = t.get("editions_critiques") or []
    if crit:
        out.append('<p><b>Éditions critiques</b></p><ul class="list quiet">'
                   + "".join(f"<li>{E(x)}</li>" for x in crit) + "</ul>")
    if t.get("note"):
        out.append(f'<p class="dim">{E(t["note"])}</p>')
    out.append("</article>")
    return "\n".join(out)


def main() -> None:
    data = json.load(open(os.path.join(ROOT, "corpus", "corpus.json"), encoding="utf-8"))
    n = len(data)
    c = sum(len(t.get("copies") or []) for t in data)
    body = [HEAD.format(n=n, c=f"{c:,}".replace(",", " "))]
    body.append('<p class="facts">' + " · ".join(
        f'<a href="#ere-{k}">{E(v)}</a>' for k, v in ERAS) + "</p>")
    for k, v in ERAS:
        rows = [t for t in data if t.get("ere") == k]
        body.append(f'<h2 id="ere-{k}">{E(v)} <span class="dim">({len(rows)})</span></h2>')
        body.extend(fiche(t) for t in rows)
    body.append(SCRIPT)
    page = lec.page("Corpus alchimique libre de droits", "\n".join(body), "")
    page = re.sub(r'<footer class="foot">.*?</footer>', FOOT, page, flags=re.S)
    open(os.path.join(SITE, "corpus.html"), "w", encoding="utf-8").write(page)
    print(f"corpus.html : {n} textes, {c} copies")


if __name__ == "__main__":
    main()
