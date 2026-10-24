"""Étape 10 : index d'autorité — les axes de consultation.

Le corpus ne se laisse pas interroger seulement par mots : on veut pouvoir
entrer par un auteur, une œuvre, un thème, une époque, un pays, un instrument,
un procédé, une substance, une planche ou un texte. Cette étape construit cet
index d'autorité :

  - un lexique par catégorie (formes françaises, latines, variantes d'usage) ;
  - le repérage de chaque entrée dans les paragraphes du corpus, avec l'ancre
    du paragraphe pour pointer le passage exact ;
  - une page d'index par catégorie et une fiche par entrée : effectifs,
    répartition par section, passages, entrées voisines ;
  - site/data/axes.json, chargé par le moteur pour filtrer les résultats.

Aucun texte n'est inventé : une fiche ne fait que réunir ce que le corpus dit
de l'entrée, avec les renvois nécessaires.
"""
from __future__ import annotations

import html
import importlib.util
import json
import os
import re
import unicodedata
from collections import defaultdict
from urllib.parse import quote

from common import DATA, SITE, log, read_json, slugify, write_json

# --------------------------------------------------------------- lexiques
# Chaque entrée : libellé → formes rencontrées dans le corpus. Les alias sont
# comparés sans accents ni casse ; les variantes latines et les graphies
# anciennes sont donc explicites.

AUTEURS = {
    "Albert le Grand": ["albert le grand", "albertus magnus", "albert le grand"],
    "Agricola": ["agricola", "georgius agricola", "georg bauer"],
    "Arnaud de Villeneuve": ["arnaud de villeneuve", "arnaldus de villanova",
                            "arnald de villeneuve"],
    "Artephius": ["artephius", "artefius"],
    "Avicenne": ["avicenne", "avicenna", "ibn sina"],
    "Basile Valentin": ["basile valentin", "basilius valentinus",
                        "basil valentine"],
    "Bernard le Trévisan": ["bernard le trevisan", "bernardus trevisanus",
                            "bernard de treves"],
    "Blaise de Vigenère": ["blaise de vigenere", "vigenere"],
    "Boyle": ["robert boyle", "boyle"],
    "Chevreul": ["chevreul", "michel eugene chevreul"],
    "Cyliani": ["cyliani"],
    "Della Porta": ["della porta", "jean baptiste della porta",
                    "giambattista della porta"],
    "Denis Zachaire": ["denis zachaire", "zachaire"],
    "Eyrénée Philalèthe": ["philalethe", "eyrenee philalethe", "philalethes",
                           "eirenaeus philalethes"],
    "Flamel": ["flamel", "nicolas flamel"],
    "Fulcanelli": ["fulcanelli"],
    "Geber": ["geber", "jabir", "djarir"],
    "Glauber": ["glauber", "rudolph glauber"],
    "Hermès Trismégiste": ["hermes trismegiste", "hermes", "trismegiste",
                           "thrice great hermes"],
    "Hollandus": ["hollandus", "isaac hollandus", "jean isaac hollandus"],
    "Jollivet-Castelot": ["jollivet-castelot", "jollivet castelot"],
    "Jung": ["carl gustav jung", "c. g. jung", "jung"],
    "Kunckel": ["kunckel", "kunckel von lowenstern"],
    "Lulle": ["raymond lulle", "raimond lulle", "lulle", "lullius",
              "ramon llull"],
    "Maier": ["michael maier", "maier", "mayr", "michel maier"],
    "Morien": ["morien", "morienus", "morienus romanus"],
    "Newton": ["newton", "isaac newton"],
    "Nicolas Valois": ["nicolas valois", "valois"],
    "Paracelse": ["paracelse", "paracelsus", "philippus aureolus"],
    "Pernety": ["pernety", "dom pernety", "antoine joseph pernety"],
    "Pontanus": ["pontanus", "jean pontanus", "giovanni pontano"],
    "Ripley": ["ripley", "georges ripley", "george ripley"],
    "Roger Bacon": ["roger bacon", "bacon"],
    "Sendivogius": ["sendivogius", "sendivoge", "michel sendivogius"],
    "Stahl": ["stahl", "georg ernst stahl"],
    "Thomas d'Aquin": ["thomas d'aquin", "thomas aquin", "saint thomas"],
    "Trismosin": ["trismosin", "salomon trismosin"],
    "Van Helmont": ["van helmont", "helmont", "jean baptiste van helmont"],
    "Vaughan": ["thomas vaughan", "eugenius philalethes", "vaughan"],
    "Zosime": ["zosime", "zosimos", "zosimus"],
}

OEUVRES = {
    "Atalanta fugiens": ["atalanta fugiens", "atalanta"],
    "Aurora consurgens": ["aurora consurgens"],
    "Bibliotheca chemica curiosa": ["bibliotheca chemica curiosa",
                                    "bibliotheque chimique"],
    "Le Char triomphal de l'antimoine": ["char triomphal", "currus triumphalis"],
    "Le Cosmopolite": ["le cosmopolite", "cosmopolite", "nouvelle lumiere chymique"],
    "Les Douze Clefs de philosophie": ["douze clefs", "zwolf schlussel"],
    "Le Livre d'Abraham le Juif": ["livre d'abraham", "abraham le juif"],
    "Hypnerotomachie": ["hypnerotomachie", "songe de poliphile", "poliphile"],
    "Mutus liber": ["mutus liber"],
    "Le Rosaire des philosophes": ["rosarium philosophorum", "rosaire des philosophes"],
    "Ripley Scrowle": ["ripley scrowle", "scrowle", "rotulus"],
    "La Toison d'or": ["toison d'or", "toyson d'or", "toyson"],
    "Turba philosophorum": ["turba philosophorum", "turba"],
    "Le Testament attribué à Flamel": ["testament de flamel", "testament"],
    "La Table d'émeraude": ["table d'emeraude", "tabula smaragdina"],
    "Le Grand Œuvre": ["grand oeuvre", "magnum opus"],
    "Amphitheatrum sapientiae": ["amphitheatrum", "amphitheatrum sapientiae"],
    "Utriusque cosmi historia": ["utriusque cosmi", "fludd"],
    "Le Musée hermétique": ["musaeum hermeticum", "musee hermeneutique"],
    "Theatrum chemicum": ["theatrum chemicum"],
    "De re metallica": ["de re metallica"],
    "Le Triomphe de l'antimoine": ["triomphe de l'antimoine"],
}

THEMES = {
    "Grand Œuvre": ["grand oeuvre", "oeuvre au noir", "oeuvre au blanc",
                    "oeuvre au rouge", "magnum opus"],
    "Pierre philosophale": ["pierre philosophale", "pierre des philosophes",
                            "pierre au grand oeuvre"],
    "Élixir": ["elixir", "elixir de vie", "elixir des philosophes"],
    "Transmutation": ["transmutation", "transmuer", "transmutatoire"],
    "Rebis": ["rebis", "androgyne", "hermaphrodite"],
    "Mariage alchimique": ["mariage alchimique", "noces", "hierogamie",
                           "conjonction"],
    "Mort et résurrection": ["mort et resurrection", "resurrection",
                             "putrefaction", "renaissance"],
    "Nigredo": ["nigredo", "oeuvre au noir", "tete de corbeau", "corbeau"],
    "Albedo": ["albedo", "oeuvre au blanc", "blanchiment"],
    "Rubedo": ["rubedo", "oeuvre au rouge", "rubification"],
    "Secret": ["secret", "discipline de l'arcane", "arcane"],
    "Initiation": ["initiation", "initie", "initiatique"],
    "Hermétisme": ["hermetisme", "hermetique", "hermes"],
    "Cabale": ["cabale", "kabbale", "cabbalistique"],
    "Symbolisme": ["symbolisme", "symbole", "symbolique"],
    "Chrysopée": ["chrysopee", "chrysopee"],
    "Spagyrie": ["spagyrie", "spagyrique"],
    "Médecine universelle": ["medecine universelle", "panacee", "remedium"],
    "Or potable": ["or potable", "aurum potabile"],
    "Quintessence": ["quintessence", "cinquième essence"],
    "Athanor": ["athanor"],
    "Laboratoire": ["laboratoire", "officine", "atelier"],
    "Emblème": ["embleme", "emblemes", "gravure"],
    "Allégorie": ["allegorie", "allegorique"],
    "Mythologie": ["mythologie", "mythe", "fable"],
    "Religion": ["religion", "chretien", "eglise", "bible"],
    "Philosophie": ["philosophie", "philosophe"],
    "Science": ["science", "scientifique", "chimie"],
    "Psychologie": ["psychologie", "psychique", "inconscient"],
    "Art royal": ["art royal", "art sacre", "art d'alchimie"],
    "Pierre des sages": ["pierre des sages", "lapis"],
    "Eau philosophique": ["eau philosophique", "eau des philosophes",
                          "mercure philosophique"],
    "Feu secret": ["feu secret", "feu philosophique", "feu de nature"],
    "Dissolution du moi": ["dissolution du moi", "mort du moi"],
}

EPOQUES = {
    "Antiquité": ["antiquite", "antiquite grecque", "alexandrie", "egypte ancienne"],
    "Haut Moyen Âge": ["haut moyen age", "viiie siecle", "ixe siecle",
                       "xe siecle", "xie siecle"],
    "Moyen Âge": ["moyen age", "xiiie siecle", "xive siecle", "xve siecle",
                  "medieval"],
    "Renaissance": ["renaissance", "xvie siecle", "seizieme siecle"],
    "XVIIe siècle": ["xviie siecle", "dix-septieme siecle", "1600"],
    "XVIIIe siècle": ["xviiie siecle", "dix-huitieme siecle", "1700"],
    "XIXe siècle": ["xixe siecle", "dix-neuvieme siecle", "1800"],
    "XXe siècle": ["xxe siecle", "vingtieme siecle", "1900"],
    "Temps modernes": ["temps modernes", "epoque moderne"],
}

PAYS = {
    "France": ["france", "francais", "paris", "lorraine", "bourgogne",
               "languedoc", "provence"],
    "Allemagne": ["allemagne", "allemand", "germanique", "saxe", "baviere"],
    "Angleterre": ["angleterre", "anglais", "londres", "oxford"],
    "Italie": ["italie", "italien", "venise", "florence", "rome", "naples"],
    "Espagne": ["espagne", "espagnol", "castille", "aragon"],
    "Pays-Bas et Flandres": ["flandres", "flamand", "pays-bas", "hollande",
                             "anvers", "bruges"],
    "Suisse": ["suisse", "bale", "zurich", "geneve"],
    "Bohême": ["boheme", "prague", "bohème"],
    "Pologne": ["pologne", "polonais", "cracovie"],
    "Égypte": ["egypte", "egyptien", "alexandrie", "memphis"],
    "Grèce": ["grece", "grec", "athenes", "hellenistique"],
    "Arabie et Perse": ["arabie", "arabe", "perse", "persan", "bagdad",
                        "damas", "istanbul", "constantinople"],
    "Chine et Inde": ["chine", "chinois", "inde", "indien", "tibet"],
    "Amérique": ["amerique", "mexique", "perou"],
    "Russie": ["russie", "russe", "moscou"],
}

MATERIEL = {
    "Athanor": ["athanor", "four a tour", "tour"],
    "Fourneau": ["fourneau", "four", "foyer", "fournaise"],
    "Alambic": ["alambic", "alembic", "chapelle"],
    "Cornue": ["cornue", "retorte", "retort"],
    "Cucurbite": ["cucurbite", "cucurbit"],
    "Récipient": ["recipient", "vase", "matras", "flacon", "fiole"],
    "Creuset": ["creuset", "creuset de terre"],
    "Mortier": ["mortier", "pilum"],
    "Balance": ["balance", "poids", "trutina"],
    "Bain-marie": ["bain-marie", "balneum mariae", "bain de sable"],
    "Lampe": ["lampe", "lampe a huile", "luminaire"],
    "Soufflet": ["soufflet", "soufflerie"],
    "Filtre": ["filtre", "filtration", "entonnoir", "hypocras"],
    "Vaisseau clos": ["vaisseau clos", "vase clos", "vaisseau scelle",
                      "oeuf philosophique"],
    "Moule": ["moule", "lingotiere"],
    "Instrument de mesure": ["thermometre", "areometre", "alcoometre",
                             "pese-liqueur"],
}

TECHNIQUES = {
    "Distillation": ["distillation", "distiller", "distillatoire"],
    "Sublimation": ["sublimation", "sublimer", "sublime"],
    "Calcination": ["calcination", "calciner", "calcine"],
    "Dissolution": ["dissolution", "dissoudre", "dissolvant"],
    "Coagulation": ["coagulation", "coaguler", "coagul"],
    "Putréfaction": ["putrefaction", "putrefier", "pourriture"],
    "Fermentation": ["fermentation", "fermenter", "ferment"],
    "Digestion": ["digestion", "digere", "digestion lente"],
    "Circulation": ["circulation", "circuler", "pelican"],
    "Projection": ["projection", "projeter", "poudre de projection"],
    "Cémentation": ["cementation", "cementer", "cement"],
    "Amalgamation": ["amalgamation", "amalgame", "amalgamer"],
    "Lixiviation": ["lixiviation", "lixivier", "lessive"],
    "Filtration": ["filtration", "filtrer", "passer par le filtre"],
    "Évaporation": ["evaporation", "evaporer", "dessiccation"],
    "Fixation": ["fixation", "fixer", "fixatif"],
    "Multiplication": ["multiplication", "multiplier"],
    "Teinture": ["teinture", "teindre", "teinture philosophique"],
    "Cohobation": ["cohobation", "cohober"],
    "Incinération": ["incineration", "incinerer", "cendres"],
    "Fusion": ["fusion", "fondre", "fonte"],
    "Précipitation": ["precipitation", "precipiter", "precipite"],
    "Cristallisation": ["cristallisation", "cristalliser", "cristaux"],
    "Extraction": ["extraction", "extraire", "extrait"],
    "Purification": ["purification", "purifier", "depuration"],
}

MATERIAUX = {
    "Mercure": ["mercure", "vif-argent", "argent-vif", "hydrargyre", "mercury"],
    "Soufre": ["soufre", "sulfur", "sulphur"],
    "Sel": ["sel", "sel marin", "sel commun", "sel gemme"],
    "Antimoine": ["antimoine", "stibium", "regule d'antimoine"],
    "Vitriol": ["vitriol", "huile de vitriol", "couleuvre"],
    "Or": ["or", "aurum", "or fin", "or philosophique"],
    "Argent": ["argent", "argent fin", "lune"],
    "Plomb": ["plomb", "saturne"],
    "Étain": ["etain", "jupiter"],
    "Fer": ["fer", "mars"],
    "Cuivre": ["cuivre", "venus", "chypre"],
    "Nitre": ["nitre", "salpetre", "salpetre"],
    "Alun": ["alun", "alumen"],
    "Cinabre": ["cinabre", "cinnabar"],
    "Arsenic": ["arsenic", "orpiment", "realgar"],
    "Talc": ["talc", "talcum"],
    "Bol d'Arménie": ["bol d'armenie", "bolus"],
    "Eau-forte": ["eau-forte", "eau forte", "esprit de nitre"],
    "Esprit-de-vin": ["esprit-de-vin", "esprit de vin", "alcool"],
    "Sel ammoniac": ["sel ammoniac", "sel d'ammoniac", "ammoniac"],
    "Terre sigillée": ["terre sigillee", "terra sigillata"],
    "Cendre": ["cendre", "cendres", "lessive de cendres"],
    "Sable": ["sable", "bain de sable"],
    "Eau": ["eau", "eau commune", "eau de pluie", "eau de source"],
    "Pierre": ["pierre", "pierres", "caillou"],
    "Métal": ["metal", "metaux", "metal parfait"],
    "Minéral": ["mineral", "mineraux", "mine"],
}

CATS = [
    ("auteurs", "Auteurs", "Alchimistes, chimistes et auteurs cités par le corpus", AUTEURS),
    ("oeuvres", "Œuvres", "Traités, recueils et ouvrages nommés", OEUVRES),
    ("themes", "Notions", "Notions, motifs et lieux communs de l'art", THEMES),
    ("epoques", "Époques", "Périodes historiques évoquées", EPOQUES),
    ("pays", "Pays et régions", "Aires géographiques et culturelles", PAYS),
    ("materiel", "Instruments", "Fourneaux, vaisseaux et instruments", MATERIEL),
    ("techniques", "Opérations", "Opérations et procédés de l'œuvre", TECHNIQUES),
    ("materiaux", "Substances", "Substances, métaux, sels et esprits", MATERIAUX),
]

NAV_EXTRA = {
    "illustrations": ("Illustrations", "Les planches du corpus, page par page"),
    "textes": ("Textes", "Traités et recueils transcrits dans le corpus"),
}


# ----------------------------------------------------------------- outils
def norm(s: str) -> str:
    s = s.lower().replace("œ", "oe").replace("æ", "ae")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def pat_of(aliases: list[str]) -> re.Pattern:
    parts = []
    for a in aliases:
        a = norm(a)
        e = re.escape(a).replace(r"\ ", r"[\s\-]+")
        if " " in a or len(a) <= 4 or not a[-1].isalpha():
            parts.append(e)
        else:
            parts.append(e + r"(?:s|es|x)?")
    parts.sort(key=len, reverse=True)      # les formes longues d'abord
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")


def load_shell():
    """Réutilise l'enveloppe HTML du site (mêmes feuille de style et pied)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "06_build_site.py")
    spec = importlib.util.spec_from_file_location("build_site", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def main() -> None:
    bs = load_shell()
    sel = read_json(os.path.join(DATA, "selection.json"))
    docs = {d["key"]: d for d in
            (json.loads(l) for l in
             open(os.path.join(DATA, "docs.jsonl"), encoding="utf-8"))}
    kept = [r for r in sel["kept"] if r["key"] in docs]
    kept.sort(key=lambda r: (r["section"], -r["chars"], r["key"]))
    slug = {r["key"]: bs.slugify(os.path.splitext(r["key"])[0], 70) for r in kept}
    # les slugs du site sont dédupliqués dans l'ordre de 06 ; on refait pareil
    used, fixed = set(), {}
    for r in kept:
        base, i = slug[r["key"]], 2
        s = base
        while s in used:
            s = f"{base}-{i}"
            i += 1
        used.add(s)
        fixed[r["key"]] = s
    slug = fixed

    doc_index = {r["key"]: i for i, r in enumerate(kept)}
    para_norm = []            # texte normalisé par paragraphe, par document
    for r in kept:
        para_norm.append([norm(t) for _, t in docs[r["key"]]["paras"]])

    os.makedirs(os.path.join(SITE, "axes"), exist_ok=True)
    export = {"cats": [], "entries": []}
    cat_index = []
    per_cat = {}

    for cat_id, cat_label, cat_desc, lex in CATS:
        cdir = os.path.join(SITE, "axes", cat_id)
        os.makedirs(cdir, exist_ok=True)
        entries = []
        for label, aliases in lex.items():
            pat = pat_of(aliases)
            hits = []          # (doc, occurrences, [(para, extrait)])
            for di, r in enumerate(kept):
                occ, samples = 0, []
                for pi, t in enumerate(para_norm[di]):
                    found = len(pat.findall(t))
                    if not found:
                        continue
                    occ += found
                    if len(samples) < 3:
                        m = pat.search(t)
                        pos = max(0, (m.start() if m else 0) - 90)
                        src = docs[r["key"]]["paras"][pi][1]
                        samples.append((pi, src[pos:pos + 260]))
                if occ:
                    hits.append((di, occ, samples))
            if not hits:
                continue
            entries.append({"label": label, "slug": slugify(label, 60),
                            "aliases": aliases, "hits": hits})

        entries.sort(key=lambda e: (-sum(h[1] for h in e["hits"]), e["label"]))
        per_cat[cat_id] = entries
        export["cats"].append({"id": cat_id, "label": cat_label,
                               "desc": cat_desc, "n": len(entries)})

        # -------- index de catégorie
        by_letter = defaultdict(list)
        for e in entries:
            by_letter[norm(e["label"])[0].upper()].append(e)
        letters = " ".join(f'<a href="#L{l}">{l}</a>' for l in sorted(by_letter))
        blocks = []
        for l in sorted(by_letter):
            blocks.append(f'<h2 id="L{l}">{l}</h2><ul class="list">')
            for e in sorted(by_letter[l], key=lambda x: norm(x["label"])):
                nd = len(e["hits"])
                occ = sum(h[1] for h in e["hits"])
                blocks.append(
                    f'<li><a href="../axes/{cat_id}/{e["slug"]}.html">'
                    f'{esc(e["label"])}</a> <span class="dim">'
                    f'{nd} articles · {occ} occurrences</span></li>')
            blocks.append("</ul>")
        body = (f'<h1>{esc(cat_label)}</h1>'
                f'<p class="lead">{esc(cat_desc)} — {len(entries)} entrées '
                f'relevées dans le corpus. La taille de chaque nom suit son '
                f'poids dans les textes.</p>'
                f'<p class="cloud">' + cloud(entries, cat_id) + '</p>'
                f'<p class="alpha">{letters}</p>' + "".join(blocks))
        write_page(bs, os.path.join(SITE, "axes", f"{cat_id}.html"),
                   cat_label, body, root="../")
        cat_index.append((cat_id, cat_label, cat_desc, len(entries)))

        # -------- fiches
        for e in entries:
            nd = len(e["hits"])
            occ = sum(h[1] for h in e["hits"])
            secs = defaultdict(int)
            for di, o, _ in e["hits"]:
                secs[kept[di]["section"]] += o
            maxs = max(secs.values()) if secs else 1
            bars = "".join(
                f'<div class="bar"><span class="lab">'
                f'{esc(bs.SECTIONS.get(s, ("Autres",))[0])}</span>'
                f'<span class="gauge" style="width:{round(100 * n / maxs)}%"></span>'
                f'<span class="n">{n}</span></div>'
                for s, n in sorted(secs.items(), key=lambda x: -x[1]))

            top = sorted(e["hits"], key=lambda h: -h[1])[:14]
            rows = []
            for di, o, samples in top:
                r = kept[di]
                links = "".join(
                    f'<p class="ctx">… {esc(s)} … '
                    f'<a href="../../articles/{slug[r["key"]]}.html#p{pi}">situer</a></p>'
                    for pi, s in samples[:2])
                rows.append(
                    f'<li><a href="../../articles/{slug[r["key"]]}.html">'
                    f'{esc(r["title"])}</a> <span class="dim">· {o} occurrences'
                    f' · {esc(bs.SECTIONS.get(r["section"], ("Autres",))[0])}'
                    f'</span>{links}</li>')

            # entrées voisines : mêmes articles, autre entrée
            docs_here = {h[0] for h in e["hits"]}
            near = []
            for other in entries:
                if other is e:
                    continue
                share = len(docs_here & {h[0] for h in other["hits"]})
                if share >= 3:
                    near.append((share, other))
            near.sort(key=lambda x: -x[0])

            body = (
                f'<nav class="crumb"><a href="../../index.html">Accueil</a> › '
                f'<a href="../../axes.html">Axes</a> › '
                f'<a href="../{cat_id}.html">{esc(cat_label)}</a></nav>'
                f'<h1>{esc(e["label"])}</h1>'
                f'<p class="meta">{nd} articles · {occ} occurrences · '
                f'formes repérées : {esc(", ".join(e["aliases"][:6]))}</p>'
                f'<p><a class="btn" href="../../recherche.html?q='
                f'{quote(e["label"])}">chercher « {esc(e["label"])} »</a> '
                f'<a class="btn ghost" href="../../recherche.html?ax={cat_id}/'
                f'{e["slug"]}">filtrer le corpus sur cet axe</a></p>'
                f'<h2>Répartition par section</h2><div class="bars">{bars}</div>'
                f'<h2>Passages</h2><ul class="list occ">{"".join(rows)}</ul>')
            if near:
                body += ('<h2>Entrées voisines</h2><p class="chips">' + "".join(
                    f'<a class="chip" href="{n["slug"]}.html">{esc(n["label"])}'
                    f' <span class="dim">{share}</span></a>'
                    for share, n in near[:16]) + "</p>")
            write_page(bs, os.path.join(cdir, f'{e["slug"]}.html'),
                       f'{e["label"]} — {cat_label}', body, root="../../")

            export["entries"].append({
                "id": f'{cat_id}/{e["slug"]}', "cat": cat_id,
                "label": e["label"], "slug": e["slug"],
                "n": nd, "occ": occ,
                "docs": {str(di): o for di, o, _ in e["hits"]},
            })

    # -------- page d'accueil des axes
    cards = "".join(
        f'<section class="sec"><h2><a href="axes/{cid}.html">{esc(lab)}</a>'
        f' <span class="count">{n} entrées</span></h2>'
        f'<p>{esc(desc)}</p></section>' for cid, lab, desc, n in cat_index)
    extra = (f'<section class="sec"><h2><a href="illustrations.html">Illustrations</a>'
             f'</h2><p>Les planches du corpus : entrées par page, avec les '
             f'images conservées et leur légende.</p></section>'
             f'<section class="sec"><h2><a href="textes.html">Textes</a></h2>'
             f'<p>Les traités et recueils transcrits, avec leur volume, leurs '
             f'illustrations et leur date de capture.</p></section>'
             f'<section class="sec"><h2><a href="mots.html">Mots</a></h2>'
             f'<p>Le vocabulaire du corpus, ses effectifs et ses formes '
             f'voisines.</p></section>')
    write_page(bs, os.path.join(SITE, "axes.html"), "Axes de consultation",
               f'<h1>Axes de consultation</h1>'
               f'<p class="lead">Le corpus peut s’interroger par mots, mais '
               f'aussi par auteurs, œuvres, thèmes, époques, pays, instruments, '
               f'procédés, substances, planches et textes. Chaque entrée réunit '
               f'les passages où elle apparaît, avec les renvois nécessaires.'
               f'</p>{cards}{extra}')

    build_illustrations(bs, kept, docs, slug)
    build_textes(bs, kept, docs, slug)
    build_notions(bs, per_cat, {c[0]: c[1] for c in cat_index}, kept, slug)
    build_concordance(bs, slug, kept)

    write_json(os.path.join(SITE, "data", "axes.json"), export)
    log(f"axes : {len(export['entries'])} entrées, "
        f"{sum(len(e['docs']) for e in export['entries'])} couples "
        f"entrée/article")
    log(f"poids data/axes.json : "
        f"{os.path.getsize(os.path.join(SITE, 'data', 'axes.json')) / 1e6:.2f} Mo")


def cloud(entries, cat_id: str) -> str:
    """Nuage pondéré : la taille du nom suit son nombre d'occurrences."""
    top = sorted(entries, key=lambda e: -sum(h[1] for h in e["hits"]))[:60]
    if not top:
        return ""
    mx = max(sum(h[1] for h in e["hits"]) for e in top)
    out = []
    for e in sorted(top, key=lambda x: norm(x["label"])):
        occ = sum(h[1] for h in e["hits"])
        size = 0.85 + 1.25 * (occ / mx) ** 0.6
        out.append(f'<a class="cl" style="font-size:{size:.2f}rem" '
                   f'href="{cat_id}/{e["slug"]}.html">{esc(e["label"])}</a>')
    return " ".join(out)


def build_notions(bs, per_cat, cat_labels, kept, slug) -> None:
    """Index analytique : toutes les entrées, A-Z, avec leurs localisateurs."""
    rows = []
    for cat_id, entries in per_cat.items():
        for e in entries:
            rows.append((e["label"], cat_id, cat_labels[cat_id], e))
    rows.sort(key=lambda r: (norm(r[0]), r[0]))
    by_letter = defaultdict(list)
    for r in rows:
        by_letter[norm(r[0])[0].upper()].append(r)

    letters = " ".join(f'<a href="#L{l}">{l}</a>' for l in sorted(by_letter))
    blocks = []
    for l in sorted(by_letter):
        blocks.append(f'<h2 id="L{l}">{l}</h2><ul class="notions">')
        for label, cat_id, cat_label, e in by_letter[l]:
            nd = len(e["hits"])
            occ = sum(h[1] for h in e["hits"])
            locs = sorted(e["hits"], key=lambda h: -h[1])[:3]
            where = ", ".join(
                f'<a href="articles/{slug[kept[di]["key"]]}.html#p{pi}">'
                f'{esc(kept[di]["title"])[:52]}</a>'
                for di, o, samples in locs
                for pi in ([samples[0][0]] if samples else [0]))
            blocks.append(
                f'<li><a class="nt" href="axes/{cat_id}/{e["slug"]}.html">'
                f'{esc(label)}</a> <span class="cat">{esc(cat_label)}</span> '
                f'<span class="dim">{occ} occ. · {nd} art.</span>'
                f'<span class="loc">{where}</span></li>')
        blocks.append("</ul>")

    write_page(bs, os.path.join(SITE, "notions.html"), "Index des notions",
               f'<h1>Index analytique des notions</h1>'
               f'<p class="lead">Toutes les entrées de l’index d’autorité en un '
               f'seul ordre alphabétique : {len(rows)} notions, œuvres, '
               f'auteurs, substances, opérations, instruments, lieux et '
               f'périodes, avec leurs localisateurs — les passages où les lire.'
               f'</p><p class="alpha">{letters}</p>' + "".join(blocks))


def build_concordance(bs, slug_of, kept) -> None:
    """Concordance complète : toutes les formes du corpus, A-Z, par lettre."""
    meta = read_json(os.path.join(SITE, "data", "search", "meta.json"))
    if not meta:
        log("concordance : index absent, étape ignorée")
        return
    df = meta["df"]
    groups = defaultdict(list)
    for term, n in df.items():
        letter = term[0].upper() if term[0].isalpha() else "0-9"
        groups[letter].append((term, n))
    os.makedirs(os.path.join(SITE, "mots"), exist_ok=True)
    total = 0
    letters = sorted(groups, key=lambda l: (l == "0-9", l))
    fname = {l: (l.lower() if l.isalnum() else "0-9") for l in letters}
    for letter in letters:
        forms = sorted(groups[letter])
        total += len(forms)
        items = "".join(
            f'<a href="../mots.html?m={quote(t)}">{esc(t)}'
            f'<span class="n">{n}</span></a>' for t, n in forms)
        write_page(bs, os.path.join(SITE, "mots", f"{fname[letter]}.html"),
                   f"Concordance — {letter}",
                   f'<nav class="crumb"><a href="../index.html">Accueil</a> › '
                   f'<a href="../mots.html">Mots</a></nav>'
                   f'<h1>{letter} <span class="count">{len(forms)} formes</span></h1>'
                   f'<p class="alpha">' + " ".join(
                       f'<a href="{fname[l]}.html">{l}</a>' for l in letters)
                   + '</p><p class="conc">' + items + "</p>", root="../")
    log(f"concordance : {total} formes réparties sur {len(letters)} pages")


def write_page(bs, path: str, title: str, body: str, root: str = "") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = bs.CSS.format(title=esc(title), root=root, extra="") + body + \
        bs.FOOT.format(root=root)
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)


def asset_map() -> dict[str, str]:
    """Nom de fichier d'origine → fichier réellement présent dans assets/."""
    from urllib.parse import unquote
    out = {}
    adir = os.path.join(SITE, "assets")
    if not os.path.isdir(adir):
        return out
    for f in os.listdir(adir):
        out[f.lower()] = f
    return out


def local_of(src: str, assets: dict[str, str]) -> str:
    from urllib.parse import unquote
    name = unquote(src.split("?")[0].split("/")[-1])
    name = re.sub(r'[<>:"/\\|?*]+', "_", name)
    return assets.get(name.lower(), "")


def build_illustrations(bs, kept, docs, slug) -> None:
    assets = asset_map()
    rows, total = [], 0
    for r in sorted(kept, key=lambda x: -len(docs[x["key"]]["images"])):
        imgs = docs[r["key"]]["images"]
        if not imgs:
            continue
        total += len(imgs)
        locs = [local_of(im["src"], assets) for im in imgs]
        thumbs = "".join(
            f'<a href="assets/{loc}" target="_blank">'
            f'<img src="assets/{loc}" loading="lazy" alt=""></a>'
            for loc in locs[:4] if loc)
        rows.append(
            f'<li><a href="articles/{slug[r["key"]]}.html">'
            f'{esc(r["title"])}</a> <span class="dim">· {len(imgs)} '
            f'illustrations · {esc(bs.SECTIONS.get(r["section"], ("Autres",))[0])}</span>'
            f'<div class="mini">{thumbs}</div></li>')
    write_page(bs, os.path.join(SITE, "illustrations.html"), "Illustrations",
               f'<h1>Illustrations</h1>'
               f'<p class="lead">{total} planches conservées dans '
               f'{len(rows)} pages du corpus. Chaque vignette ouvre l’image '
               f'originale ; la page de l’article donne la galerie complète '
               f'avec les légendes.</p><ul class="list occ">{"".join(rows)}</ul>')


def build_textes(bs, kept, docs, slug) -> None:
    rows = []
    for r in sorted(kept, key=lambda x: (-x["chars"])):
        if r["section"] not in {"1", "8", "DC"}:
            continue
        d = docs[r["key"]]
        rows.append(
            f'<li><a href="articles/{slug[r["key"]]}.html">{esc(r["title"])}</a>'
            f' <span class="dim">· {r["chars"] // 1000} k car. · '
            f'{len(d["images"])} ill. · capture {d["ts"][:4]}</span></li>')
    write_page(bs, os.path.join(SITE, "textes.html"), "Textes",
               f'<h1>Textes</h1>'
               f'<p class="lead">Les {len(rows)} traités et recueils '
               f'transcrits dans le corpus, du plus long au plus court. '
               f'Chacun dispose d’une version lisible et de la réplique de la '
               f'page archivée.</p><ul class="list">{"".join(rows)}</ul>')


if __name__ == "__main__":
    main()
