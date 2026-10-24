"""Étape 4 : délimitation du périmètre.

Le site d'Hervé Delboy mêlait alchimie, astrologie, statistiques, musique et
échecs. Le plan officiel de la partie alchimique (plan_alchimie.htm) fait foi :
ses 8 sections + le dossier des Douze Clefs définissent le noyau. On y ajoute
les pages atteignables par liens internes, puis on écarte ce qui relève de
l'astrologie et des autres domaines.

Produit data/corpus.json (documents du périmètre) et data/hors_perimetre.json.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict, deque

from common import (DATA, RAW, log, parse_html, read_json, resolve_rename,
                    write_json)

SECTION_NAMES = {
    "1_-_Collection_des_grands_traités": ("1", "Collection des grands traités"),
    "2_-_Gravures_et_emblèmes_alchimiques": ("2", "Gravures et emblèmes"),
    "3_-_Symboles_alchimiques_et_spagyriques": ("3", "Symboles et spagyrie"),
    "4_-_Lidée_alchimique": ("4", "L'idée alchimique"),
    "Dyas_Chymica_Tripartita": ("4", "L'idée alchimique"),
    "Ripley_Scrowle": ("4", "L'idée alchimique"),
    "Poliphile": ("2", "Gravures et emblèmes"),
    "5_-_Précis_de_symbolisme_alchimique": ("5", "Précis de symbolisme"),
    "6_-_Larsenal_hermétique": ("6", "L'arsenal hermétique"),
    "7_-_Le_Laboratoire_légendaire": ("7", "Le laboratoire légendaire"),
    "8_-_Les_textes": ("8", "Les textes"),
    "Les_Douze_Clefs_de_philosophie": ("DC", "Les Douze Clefs de philosophie"),
    "1": ("8", "Les textes"),
}

ASTRO = re.compile(
    r"astrolog|zodiaque astrolog|th[eè]me astral|ascendant|éphéméride|"
    r"directions? primaires?|transits? planétaires?|horoscope|"
    r"maisons? astrologiques?|signe solaire|natalit", re.I)
ALCH = re.compile(
    r"alchim|herm[ée]t|chrysop[ée]e|pierre philosophale|athanor|spagyr|"
    r"[ée]lixir|mercure des philosophes|soufre|sel philosoph|"
    r"philosophes? par le feu|cabale|ros[ae]croix|paracelse|flamel|"
    r"basile valentin|geber| ripell?ey|maier|sethon|cosmopolite", re.I)

# Pages explicitement incluses : alchimiques mais pauvres en lexique
# (planches, sommaires, courtes notices) ou rattachées au noyau par leur sujet.
FORCED_IN = {
    "abraham.html", "alchimie_flamel.html", "azoth.html",
    "oeuvre_saturne.html", "apotheose.html", "mellonms41.htm",
    "domcampanus.htm", "escalier_des_sages.html", "escalier_des_sages_i_a.html",
    "tour_rivalland.html", "cap_tr_engl.htm",
    "biblio_alchimie.html", "lexique_essai.html", "plan_alchimie.htm",
    "intro_alchimie.htm", "alchemy_pdf.html",
    # histoire de la chimie / minéralogie : matériau de l'argumentation
    # alchimique de Delboy (Chevreul, Ebelmen, Hoefer, Palissy, Gobineau)
    "chevreul_hoefer.html", "chevreul_hoefer_2.html", "chevreul_hoefer_3.html",
    "add_chevreul_hoefer.html", "ebelmen_2.html", "mineralogistes.html",
    "palissy_alchimie.html", "gobineau.html", "idee_alchimique_8.html",
    # planche du tableau de Mendeleïev, citée par « Les origines de
    # l'alchimie » (Berthelot) : zéro lexique alchimique, mais dans le dossier
    "elements_mendeleiv.html",
}

# Pages explicitement hors périmètre (astrologie, musique, échecs, politique,
# statistiques, divers) : vérifiées une à une sur leur contenu.
FORCED_OUT = {
    "earl_hines.html", "earl_hines_2.html", "heinrich_schutz.html",
    "scott_ross.html", "quasi_newton.html",
    "quasi_newton2.html", "nv_rech1.htm", "nv_rech4.htm",
    "nv_rech4_engl.htm", "livres.html", "index.html", "index2.html",
    "introgenerale.htm", "recherche.htm", "renifle.htm", "menu_opera.html",
    "stat_alchimie.html",
    "organigramme.html", "notes_protee.html", "notes_protee_2.html",
    "domcampanus.htm", "cap_tr_engl.htm", "j2ramsengl.html",
    "journeerams2.htm", "rams.htm", "rams_engl.htm", "nv_rech1_engl.htm",
    "nv_rech2.htm", "nv_rech3.htm", "nv_rech3_engl.htm",
    "salverte_4.html", "news.html", "nouveautes.html", "disparition.htm",
    "hard_stroke.htm", "partenaires.htm", "general.htm", "mineralogistes_bis.html",
    "abstraction_chevreul.html", "pierres_precieuses.html",
    "alea.htm", "alea_3.htm", "alea_4.htm", "alea_6.htm",
    "plan_stat.html", "prev_pol.htm", "transit_pol.html",
    "transit_pol_engl.html", "nonlin.htm", "nonlinear.htm",
    "nonparam.htm", "equations.html", "pharmacokin_sample.html",
    "computdir.htm", "ortho.htm", "epoqclim.htm", "connaissances_humaines.html",
    "histoires_directions_primaires.html", "hISTOIRE+DES+DIRECTIONS+PRIMAIRES.html",
    "direction.html", "direction_engl.html", "direct_exemple.htm",
    "d_exemple_engl.htm", "symb_dir_prim_demo.html",
    "chess_1.htm", "chess_2.htm", "chess_3.htm", "chess_4.htm",
    "end_games.html", "end_games_2.html", "end_games_3.html",
    "end_games_4.html", "endgame_plan.html", "alekhine_euwe.htm",
    "celibidache.html", "celibidache_2.html", "kubbel_1.htm", "kubbel_2.htm",
    "kubbel_3.htm", "kubbel_4.htm", "rins.htm", "rinck_2.htm",
    "troitzky.htm", "troitzky_2.htm", "troitzky_3.htm", "troitzky_4.htm",
    "troitzky_5.htm", "portanus.htm", "havel_2.htm", "divers.htm",
    "timeline.htm", "news.html", "nouveautes.html", "download_software.html",
    "telech_fichier.html", "logiciel.htm", "logiciel_engl.htm",
    "formulaire.htm", "partenaires.htm", "gobineau.html", "general.htm",
    "bourges.htm", "artic.html", "article+complet+pour+l'astrologue.html",
}


def toc_sections() -> dict[str, dict]:
    raw = open(os.path.join(RAW, "plan_alchimie.htm"), "rb").read().decode("latin-1")
    root = parse_html(raw)
    body = root.find_all("body")[0]
    seq = []
    stack = [body]
    while stack:
        n = stack.pop()
        if isinstance(n, str):
            continue
        if n.tag == "a":
            if n.get("name"):
                seq.append(("ANCHOR", n.get("name")))
            elif n.get("href"):
                seq.append(("LINK", n.get("href")))
        stack.extend(reversed(n.children))
    out, cur = {}, "(intro)"
    for kind, val in seq:
        if kind == "ANCHOR":
            cur = val
            continue
        k = val.split("#")[0].split("/")[-1].lower()
        if not k or not (k.endswith(".htm") or k.endswith(".html")):
            continue
        sid, label = SECTION_NAMES.get(cur, ("9", "Autres pages alchimiques"))
        out.setdefault(k, {"section": sid, "label": label})
    return out


def main() -> None:
    docs = [json.loads(l) for l in open(os.path.join(DATA, "docs.jsonl"),
                                       encoding="utf-8")]
    by_key = {d["key"]: d for d in docs}
    toc = toc_sections()
    log(f"Plan alchimique : {len(toc)} cibles, "
        f"{len({v['section'] for v in toc.values()})} sections")

    # --- graphe interne
    graph = {}
    for d in docs:
        neigh = []
        for l in d["links"]:
            k = l["key"]
            if k in by_key and k != d["key"]:
                neigh.append(k)
        graph[d["key"]] = sorted(set(neigh))

    # --- noyau : sections du plan + parcours des liens internes (2 sauts)
    core = set(k for k in toc if k in by_key)
    frontier = deque((k, 0) for k in core)
    while frontier:
        k, depth = frontier.popleft()
        if depth >= 2:
            continue
        for n in graph.get(k, []):
            if n not in core and n not in FORCED_OUT:
                core.add(n)
                frontier.append((n, depth + 1))

    # textes des liens entrants : ils donnent le vrai titre des pages perdues
    inbound = defaultdict(list)
    for d in docs:
        for l in d["links"]:
            t = (l.get("text") or "").strip()
            if t and l["key"] != d["key"]:
                inbound[l["key"]].append(t)

    def title_of_lost(key: str, fallback: str) -> str:
        texts = [t for t in inbound.get(key, []) if 3 <= len(t) <= 90]
        if not texts:
            return fallback
        best = max(set(texts), key=lambda t: (texts.count(t), len(t)))
        return best

    kept, out, lost = [], [], []
    aliases = dict(read_json(os.path.join(DATA, "aliases.json"), {}) or {})
    for d in docs:
        k = d["key"]
        text = d["text"]
        alch = len(ALCH.findall(text))
        astro = len(ASTRO.findall(text))
        density = alch * 1000.0 / max(1, d["chars"])
        dead = ("erreur 404" in d["title"].lower()
                or "page n'existe plus" in d["title"].lower()
                or d["chars"] == 0
                # capture d'image servie à la place d'une page
                or d["text"].startswith(("GIF8", "%PDF", "\x89PNG")))
        if dead and k not in FORCED_IN:
            # page seulement renommée ? le texte est alors déjà dans le corpus
            renamed = resolve_rename(k, set(by_key))
            if renamed:
                aliases[k] = renamed
                out.append({"key": k,
                            "title": title_of_lost(k, by_key[renamed]["title"]),
                            "chars": by_key[renamed]["chars"],
                            "alch": 0, "astro": 0, "section": "-",
                            "label": "Ancienne adresse d'une page présente",
                            "in_plan": k in toc,
                            "raison": "adresse ancienne (page renommée)",
                            "renamed_to": renamed})
                continue
            out.append({"key": k,
                        "title": title_of_lost(k, d["title"]),
                        "chars": d["chars"],
                        "alch": alch, "astro": astro, "section": "-",
                        "label": "Page perdue dans l'archive", "in_plan": k in toc,
                        "raison": "capture indisponible (404 / vide)"})
            lost.append(k)
            continue
        if k in FORCED_OUT:
            in_core = False
        elif k in FORCED_IN:
            in_core = True
        elif k in toc:
            in_core = True
        else:
            in_core = (k in core and alch >= 3 and alch >= 1.5 * astro
                       and density >= 2.0)
        rec = {
            "key": k,
            "title": d["title"],
            "chars": d["chars"],
            "alch": alch,
            "astro": astro,
            "section": toc.get(k, {}).get("section", "9"),
            "label": toc.get(k, {}).get("label", "Autres pages alchimiques"),
            "in_plan": k in toc,
        }
        (kept if in_core else out).append(rec)
        if not in_core and k not in lost:
            rec.setdefault("raison", "hors sujet (astrologie, musique, échecs, "
                                   "statistiques, divers)")

    # pages retenues mais à dominante astrologique et absentes du plan
    for r in list(kept):
        d = by_key[r["key"]]
        if not r["in_plan"] and r["chars"] > 0:
            a = len(ASTRO.findall(d["text"]))
            c = len(ALCH.findall(d["text"]))
            if a > c * 1.5 and a > 5:
                kept.remove(r)
                r["raison"] = "dominante astrologique"
                out.append(r)

    log(f"Périmètre alchimie : {len(kept)} pages | hors périmètre : "
        f"{len(out)} dont {len(lost)} pages perdues")
    log(f"Volume retenu : {sum(r['chars'] for r in kept):,} caractères"
        .replace(",", " "))
    write_json(os.path.join(DATA, "aliases.json"), dict(sorted(aliases.items())))
    write_json(os.path.join(DATA, "selection.json"),
               {"kept": sorted(kept, key=lambda r: r["key"]),
                "out": sorted(out, key=lambda r: r["key"]),
                "lost": sorted(lost)})
    log(f"Adresses anciennes reliées à une page présente : {len(aliases)}")

    from collections import Counter
    c = Counter((r["section"], r["label"]) for r in kept)
    for (sid, label), n in sorted(c.items()):
        log(f"  {sid:>2} {label:<38} {n:>3} pages")


if __name__ == "__main__":
    main()
