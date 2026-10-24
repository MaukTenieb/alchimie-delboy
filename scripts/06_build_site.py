"""Étape 6 : construction du site.

Pour chaque page du périmètre, on produit deux vues :
  - articles/<slug>.html : article encyclopédique lisible (texte extrait,
    métadonnées, galerie, articles liés) ;
  - original/<slug>.html : réplique de la page archivée (markup d'origine,
    liens et images réécrits vers le site local).
Plus les pages d'axes : plan, sections, symboles, noms, méthode, lacunes.
"""
from __future__ import annotations

import html
import json
import os
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from urllib.parse import quote, unquote, urlsplit

from common import (DATA, RAW, SITE, log, read_json, slugify, strip_accents,
                    write_json)

CSS = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{root}style.css">
{extra}
</head><body>
<header class="topbar">
  <a class="brand" href="{root}index.html">Hervé Delboy<span> — alchimie</span></a>
  <nav>
    <a href="{root}plan.html">Plan</a>
    <a href="{root}guide.html">Index</a>
    <a href="{root}recherche.html">Recherche</a>
    <a href="{root}mots.html">Mots</a>
    <a href="{root}parcours.html">Dossiers</a>
    <a href="{root}method.html">Méthode</a>
  </nav>
</header>
<main>
"""

FOOT = """
</main>
<footer class="foot">
  <p class="rights">© Hervé Delboy et ayants droit —
  <span class="url">perso.club-internet.fr/hdelboy</span>, puis
  <span class="url">herve.delboy.perso.sfr.fr</span> (site disparu).
  Reproduction à des fins de consultation, de recherche et de conservation ;
  aucune exploitation commerciale. Tous droits réservés aux auteurs et à
  leurs ayants droit.</p>
  <p><a href="{root}notice.html">Notice, droits et provenance</a> ·
  <a href="{root}guide.html">Tous les index</a> ·
  <a href="{root}method.html">Méthode et sources</a> ·
  <a href="{root}lacunes.html">Pages perdues</a></p>
</footer>
</body></html>
"""

SECTIONS = {
    "1": ("Collection des grands traités",
          "Les grandes collections imprimées (Bibliotheca chemica curiosa, "
          "Theatrum chemicum, Musaeum hermeticum…) et les manuscrits."),
    "2": ("Gravures et emblèmes",
          "Les cycles d'emblèmes : Atalanta fugiens, Philosophia reformata, "
          "Douze Clefs, Livre d'Abraham Juif, Aurora consurgens…"),
    "3": ("Symboles et spagyrie",
          "Dictionnaire des symboles alchimiques, planche par planche."),
    "4": ("L'idée alchimique",
          "La thèse de l'auteur : l'alchimie comme science des transmutations "
          "réelles, lue à travers Chevreul, Berthelot, Newton."),
    "5": ("Précis de symbolisme",
          "Études de symbolisme appliqué : portails, vitraux, retables, "
          "tarot, zodiaque alchimique."),
    "6": ("L'arsenal hermétique",
          "Les matières de l'œuvre : mercure, soufre, sel, antimoine, "
          "salpêtre, potasses, teintures."),
    "7": ("Le laboratoire légendaire",
          "Les lieux et les instruments : fourneaux, caves, tours, "
          "laboratoires reconstitués."),
    "8": ("Les textes",
          "Les traités reproduits in extenso, avec notices."),
    "DC": ("Les Douze Clefs de philosophie",
           "Le dossier le plus dense du site : le traité attribué à Basile "
           "Valentin, clef par clef, figure par figure."),
    "9": ("Études et annexes",
          "Les études historiques et les appendices qui nourrissent "
          "l'argumentation alchimique."),
}

STOP = set("""le la les un une des du de d au aux a et ou mais donc or ni car
que qui quoi dont où ce cet cette ces celui celle ceux celles son sa ses leur
leurs il elle ils elles nous vous je tu on se sy en y ne pas plus moins très
être avoir fait faire comme tout tous toute toutes autre autres même aussi
bien peut peu sans sous sur dans par pour avec contre entre chez vers est sont
était étaient être fut furent ont avait avaient cette ainsi alors donc quand
comme depuis pendant après avant encore non oui si deux trois quatre cinq
premier première second seconde partie chapitre plan page suite fin début
""".split())

NAME_FIX = {
    "paracelse": "Paracelse", "flamel": "Nicolas Flamel", "basile": "Basile Valentin",
    "valentin": "Basile Valentin", "maier": "Michael Maier", "ripley": "Georges Ripley",
    "sethon": "Alexandre Sethon", "cosmopolite": "Le Cosmopolite",
    "newton": "Isaac Newton", "chevreul": "Eugène Chevreul",
    "berthelot": "Marcelin Berthelot", "hoefer": "Ferdinand Hoefer",
    "geber": "Geber", "avicenne": "Avicenne", "razis": "Razis",
    "artephius": "Artephius", "morienus": "Morienus", "calid": "Kalid",
    "lulle": "Raymond Lulle", "paracelsus": "Paracelse", "jung": "Carl Gustav Jung",
    "sendivogius": "Sendivogius", "d'espagnet": "D'Espagnet", "espagnet": "D'Espagnet",
    "mylius": "Johann Daniel Mylius", "libavius": "Andreas Libavius",
    "palissy": "Bernard Palissy", "gobineau": "Esprit Gobineau",
    "fulcanelli": "Fulcanelli", "canseliet": "Eugène Canseliet",
    "delesse": "Achille Delesse", "daubrée": "Gabriel Daubrée",
    "ebelmen": "Jacques-Joseph Ebelmen", "lavoisier": "Lavoisier",
    "philalethe": "Philalèthe", "eyrenaeus": "Eyrénée Philalèthe",
    "pontanus": "Pontanus", "dorneus": "Gérard Dorn", "dorn": "Gérard Dorn",
    "huginus": "Huginus à Barma", "cambriel": "Cambriel",
    "cyliani": "Cyliani", "zachaire": "Denis Zachaire",
    "grosparmy": "Grosparmy", "limojon": "Limojon de Saint-Didier",
    "tollius": "Tollius", "orthelius": "Orthelius", "stolcius": "Stolcius",
    "maurier": "Clovis Hesteau de Nuysement", "nuysement": "Nuysement",
    "van": "Van Helmont", "helmont": "Van Helmont", "boehme": "Jacob Böhme",
    "böhme": "Jacob Böhme", "agrippa": "Agrippa", "villeneuve": "Arnaud de Villeneuve",
    "albert": "Albert le Grand", "roger": "Roger Bacon", "bacon": "Roger Bacon",
    "bacon": "Roger Bacon", "synesius": "Synesius", "zozime": "Zosime",
    "ostanes": "Ostanès", "hermès": "Hermès", "hermes": "Hermès",
}

LINK_MARK = "«{0}»"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def fmt(n: int) -> str:
    """Nombre avec séparateur de milliers étroit (sans casser les virgules
    du texte environnant)."""
    return f"{n:,}".replace(",", "\u202f")


def unq(s: str) -> str:
    """Décode un pourcentage d'URL : UTF-8 si valide, sinon latin-1
    (le site date des années 2000 et mélange les deux encodages)."""
    try:
        return unquote(s, encoding="utf-8", errors="strict")
    except Exception:
        return unquote(s, encoding="latin-1", errors="replace")


def name_slug(n: str) -> str:
    return slugify(n, 60)


def norm_anchor(s: str) -> str:
    """Forme comparable d'une ancre : minuscules, sans accents ni ponctuation."""
    s = html.unescape(unq(s)).lower()
    s = re.sub(r"[\s_]+", " ", s)
    s = re.sub(r"[^\w\u00c0-\u00ff ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve_anchor(b: "SiteBook", key: str, frag: str) -> str:
    """Retrouve l'ancre réelle visée par un fragment, ou "".

    Le site d'origine contient des centaines de liens croisés vers des ancres
    approximatives (« #Van Helmont. », « #soufres blancs et »). On tente :
    correspondance exacte, préfixe, puis similarité de chaîne ; au-delà du
    seuil on renvoie l'ancre réelle, sinon rien (le lien mènera au haut de
    page plutôt qu'à une impasse).
    """
    amap = getattr(b, "anchors", None)
    if amap is None:
        amap = {}
        for r in b.kept:
            d = {}
            for a in b.docs[r["key"]]["anchors"]:
                d.setdefault(norm_anchor(a), unq(a))
            amap[r["key"]] = d
        b.anchors = amap
    table = amap.get(key)
    if not table:
        return ""
    n = norm_anchor(frag)
    if not n:
        return ""
    if n in table:
        return table[n]
    # barre alphabétique du haut de page : l'ancre « l » renvoie en réalité à
    # la rubrique « l_t » (les entrées de la liste portent le suffixe _t)
    if len(n) == 1 and n + "_t" in table:
        return table[n + "_t"]
    # préfixe (les ancres d'origine sont souvent tronquées)
    starts = [v for k, v in table.items() if k.startswith(n) or n.startswith(k)]
    if len(starts) == 1:
        return starts[0]
    best, score = "", 0.0
    for k, v in table.items():
        r = SequenceMatcher(None, n, k).ratio()
        if r > score:
            best, score = v, r
    return best if score >= 0.86 else ""


class SiteBook:
    def __init__(self) -> None:
        self.docs = {d["key"]: d for d in
                     (json.loads(l) for l in
                      open(os.path.join(DATA, "docs.jsonl"), encoding="utf-8"))}
        sel = read_json(os.path.join(DATA, "selection.json"))
        self.sel = sel
        self.kept = [r for r in sel["kept"] if r["key"] in self.docs]
        self.kept.sort(key=lambda r: (r["section"], -r["chars"], r["key"]))
        self.by_key = {r["key"]: r for r in self.kept}
        self.slug = {}
        used = set()
        for r in self.kept:
            base = slugify(os.path.splitext(r["key"])[0], 70)
            s, i = base, 2
            while s in used:
                s = f"{base}-{i}"
                i += 1
            used.add(s)
            self.slug[r["key"]] = s
        self.assets = {}
        if os.path.isdir(os.path.join(SITE, "assets")):
            for f in os.listdir(os.path.join(SITE, "assets")):
                self.assets[f.lower()] = f
        self.recovered = read_json(os.path.join(DATA, "recovered.json"), {}) or {}
        # adresses anciennes → page présente (renommages du site d'origine)
        self.renames = read_json(os.path.join(DATA, "aliases.json"), {}) or {}
        self.name_by_doc = {}
        self.name_slugs = {}
        self._kw = {}

    # ------------------------------------------------------------- helpers
    def resolve(self, key: str) -> str:
        """Clé d'une page du corpus, y compris via une ancienne adresse."""
        if key in self.by_key:
            return key
        return self.renames.get(key, "")

    def page(self, path: str, title: str, body: str, root: str = "",
             extra: str = "") -> None:
        out = CSS.format(title=esc(title), root=root, extra=extra) + body + \
            FOOT.format(root=root)
        full = os.path.join(SITE, path)
        os.makedirs(os.path.dirname(full) or SITE, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(out)

    def local_asset(self, src: str) -> str:
        name = unquote(src.split("?")[0].split("/")[-1])
        name = re.sub(r'[<>:"/\\|?*]+', "_", name)
        return self.assets.get(name.lower(), "")

    def excerpt(self, text: str, n: int = 220) -> str:
        t = re.sub(r"\s+", " ", text or "").strip()
        return t[:n].rsplit(" ", 1)[0] + ("…" if len(t) > n else "")

    def keywords(self, key: str, k: int = 8) -> list[str]:
        c = self._kw.get(key)
        if c is None:
            words = re.findall(r"[a-zA-Zà-ÿ]{4,}",
                               strip_accents(self.docs[key]["text"]).lower())
            c = Counter(w for w in words if w not in STOP)
            self._kw[key] = c
        return [w for w, _ in c.most_common(k)]


# ----------------------------------------------------------------- articles

def render_article(b: SiteBook, r: dict) -> str:
    d = b.docs[r["key"]]
    sid = r["section"]
    label = SECTIONS.get(sid, ("Autres", ""))[0]
    rec = b.recovered.get(r["key"])
    if rec and rec.get("source", "").startswith("wayback "):
        _, ts, url = rec["source"].split(" ", 2)
        source = (f'page retrouvée — <a href="https://web.archive.org/web/{ts}/{url}" '
                  f'target="_blank" rel="noopener">capture du {ts[:4]}-'
                  f'{ts[4:6]}-{ts[6:8]}</a>')
    elif rec:
        source = f'page retrouvée — {esc(rec.get("source", ""))}'
    else:
        source = (f'source : '
                  f'<a href="https://web.archive.org/web/{d["ts"]}/{d["url"]}" '
                  f'target="_blank" rel="noopener">capture du {d["ts"][:4]}-'
                  f'{d["ts"][4:6]}-{d["ts"][6:8]}</a>')
    parts = [f'<article class="article">',
             f'<nav class="crumb"><a href="../plan.html">Plan</a> › '
             f'<a href="../sections/{sid.lower()}.html">{esc(label)}</a></nav>',
             f'<h1>{esc(d["title"])}</h1>',
             f'<p class="meta">'
             f'<a href="../liseuse.html?p={b.slug[r["key"]]}">lire</a> · '
             f'<a href="../original/{b.slug[r["key"]]}.html">page d\'origine</a>'
             f' · {len(d["images"])} illustrations · {source}</p>']

    # sommaire si le texte comporte des titres
    heads = [(i, k, t) for i, (k, t) in enumerate(d["paras"]) if k.startswith("h")]
    if len(heads) >= 3:
        parts.append('<details class="toc"><summary>Sommaire</summary><ul>')
        for i, k, t in heads[:60]:
            parts.append(f'<li class="lvl{k[-1]}"><a href="#p{i}">{esc(t)}</a></li>')
        parts.append("</ul></details>")

    body = []
    for i, (kind, t) in enumerate(d["paras"]):
        if kind == "txt":
            if len(t) < 4:
                continue
            # chaque paragraphe porte son ancre : la recherche et les index
            # d'autorité peuvent pointer le passage exact (#p12)
            body.append(f'<p id="p{i}">{esc(t)}</p>')
        elif kind.startswith("h"):
            lvl = min(3, max(2, int(kind[-1])))
            body.append(f'<h{lvl} id="p{i}">{esc(t)}</h{lvl}>')
    parts.append('<div class="prose">' + "\n".join(body) + "</div>")

    imgs = []
    seen = set()
    for img in d["images"]:
        loc = b.local_asset(img["src"])
        if not loc or loc in seen:
            continue
        seen.add(loc)
        imgs.append(f'<figure><a href="../assets/{quote(loc)}" target="_blank">'
                    f'<img src="../assets/{quote(loc)}" loading="lazy" '
                    f'alt="{esc(img["alt"] or d["title"])}"></a>'
                    f'<figcaption>{esc(img["alt"])}</figcaption></figure>')
    if imgs:
        parts.append(f'<section class="gallery"><h2>Illustrations '
                     f'({len(imgs)})</h2><div class="grid">'
                     + "".join(imgs) + "</div></section>")

    # articles liés : liens internes du site, puis mots-clés communs
    rel, seen_rel = [], {r["key"]}
    for l in d["links"]:
        k = b.resolve(l["key"])
        if k and k not in seen_rel:
            seen_rel.add(k)
            rel.append((k, l["text"] or b.docs[k]["title"]))
    if len(rel) < 8:
        kw = set(b.keywords(r["key"], 24))
        scored = []
        for other in b.kept:
            if other["key"] in seen_rel:
                continue
            share = len(kw & set(b.keywords(other["key"], 24)))
            if share >= 3:
                scored.append((share, other["key"]))
        scored.sort(reverse=True)
        for _, k in scored[:8]:
            rel.append((k, b.docs[k]["title"]))
    if rel:
        parts.append('<section class="related"><h2>Articles liés</h2><ul>')
        for k, t in rel[:24]:
            if k in b.by_key:
                parts.append(f'<li><a href="{b.slug[k]}.html">{esc(t)[:110]}</a></li>')
        parts.append("</ul></section>")

    names = b.name_by_doc.get(r["key"], [])
    if names:
        parts.append('<section class="names-cited"><h2>Noms cités</h2><p>' +
                     " · ".join(f'<a href="../noms/{sl}.html">{esc(n)}</a>'
                                for n, sl in names) + "</p></section>")

    # navigation sérielle dans la section
    sib = b.order_in_section.get(r["key"], ([], []))
    prev_key, next_key = sib
    nav = []
    if prev_key:
        nav.append(f'<a class="prev" href="{b.slug[prev_key]}.html">‹ '
                   f'{esc(b.docs[prev_key]["title"])[:70]}</a>')
    if next_key:
        nav.append(f'<a class="next" href="{b.slug[next_key]}.html">'
                   f'{esc(b.docs[next_key]["title"])[:70]} ›</a>')
    if nav:
        parts.append('<nav class="series">' + "".join(nav) + "</nav>")

    parts.append("</article>")
    return "\n".join(parts)


# ----------------------------------------------------------------- réplique

def rewrite_links(html_text: str, b: SiteBook, r: dict,
                  banner: str | None = None) -> str:
    ts = b.docs[r["key"]]["ts"]

    def href_sub(m):
        attr, val = m.group(1), m.group(2)
        if val.lower().startswith(("mailto:", "javascript:")):
            return m.group(0)
        # lien interne à la page (barre alphabétique, sommaire) : l'ancre
        # d'origine est souvent approximative, on la résout ou on la retire
        if val.startswith("#"):
            frag = val[1:]
            if not frag:
                return m.group(0)
            resolved = resolve_anchor(b, r["key"], frag)
            if resolved:
                return f'{attr}="#{quote(resolved)}"'
            return (f'{attr}="#" class="lien-repare" title="ancre absente '
                    f"de la page d'origine (lien ramené en haut de page)\"")
        base = val.split("#")[0]
        raw_frag = val.split("#", 1)[1] if "#" in val else ""
        key = unquote(base.split("/")[-1]).lower()
        key = b.resolve(key) or key
        if key in b.slug:
            frag, broken = "", False
            if raw_frag:
                resolved = resolve_anchor(b, key, raw_frag)
                if resolved:
                    frag = "#" + quote(resolved)
                else:
                    broken = True
            cls = (' class="lien-repare" title="ancre absente de la page '
                   'd\'origine : lien ramené en haut de page"') if broken else ""
            return f'{attr}="../original/{b.slug[key]}.html{frag}"{cls}'
        if key in b.by_key:
            return f'{attr}="../articles/{b.slug[key]}.html"'
        if base.lower().startswith("http") or base.startswith("//"):
            return f'{attr}="https://web.archive.org/web/{ts}/{val}" target="_blank" rel="noopener"'
        return f'{attr}="#" title="lien mort dans l\'archive"'

    def src_sub(m):
        attr, val = m.group(1), m.group(2)
        loc = b.local_asset(val)
        if loc:
            return f'{attr}="../assets/{quote(loc)}"'
        if val.lower().startswith("http"):
            return f'{attr}="https://web.archive.org/web/{ts}/{val}"'
        return f'{attr}="data:image/gif;base64,R0lGODlhAQABAAAAACw="'

    out = re.sub(r'<script\b[^>]*>.*?</script>', '', html_text,
                 flags=re.I | re.S)
    # le document est réencodé en UTF-8 : on retire les vieilles déclarations
    out = re.sub(r'<meta[^>]+charset[^>]*>', '', out, flags=re.I)
    # les ancres du site mélangent caractères littéraux, échappements %XX et
    # entités HTML (« Prot&eacute;e ») : on décode les %XX mais on laisse les
    # entités telles quelles, sinon le navigateur ne reconnaît plus l'ancre
    # (les ancres du site s'écrivent aussi sans guillemets : <a name=l_t>)
    def name_sub(m):
        head = m.group(1)
        val = next(g for g in m.groups()[1:] if g is not None)
        return head + ' name="' + unq(val).replace('"', '&quot;') + '"'

    out = re.sub(r'(<a\b[^>]*?)\bname\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
                 name_sub, out, flags=re.I)
    out = re.sub(r'(href)\s*=\s*"([^"]*)"', href_sub, out, flags=re.I)
    out = re.sub(r"(src)\s*=\s*\"([^\"]*)\"", src_sub, out, flags=re.I)
    # bandeau d'information + lien vers la vue lisible
    if banner is None:
        banner = (
            '<div class="replica-note">Réplique de la page archivée · '
            f'<a href="../articles/{b.slug[r["key"]]}.html">version lisible</a> · '
            f'<a href="../plan.html">plan</a></div>'
        )
    out = re.sub(r"(<body[^>]*>)", r"\1" + banner, out, count=1, flags=re.I)
    if "<body" not in out.lower():
        out = banner + out
    out = re.sub(r"<head([^>]*)>",
                 r'<head\1><meta charset="utf-8">', out, count=1, flags=re.I)
    out = out.replace("</head>",
                      '<link rel="stylesheet" href="../style.css"></head>', 1)
    return out


# ------------------------------------------------------------------- pages

def build(b: SiteBook) -> None:
    # on repart d'un dossier propre pour ne pas laisser de pages orphelines
    import shutil
    for sub in ("articles", "original", "sections", "noms", "data"):
        p = os.path.join(SITE, sub)
        if os.path.isdir(p):
            shutil.rmtree(p)
    os.makedirs(os.path.join(SITE, "articles"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "original"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "sections"), exist_ok=True)

    # les noms d'abord : les articles s'y rattachent
    build_names(b)

    # ordre de lecture dans chaque section (pour les liens précédent/suivant)
    b.order_in_section = {}
    sec_lists = defaultdict(list)
    for r in b.kept:
        sec_lists[r["section"]].append(r)
    for items in sec_lists.values():
        items.sort(key=lambda x: strip_accents(x["title"]).lower())
        for i, r in enumerate(items):
            b.order_in_section[r["key"]] = (
                items[i - 1]["key"] if i else None,
                items[i + 1]["key"] if i + 1 < len(items) else None)

    # articles + répliques
    for r in b.kept:
        slug = b.slug[r["key"]]
        b.page(f"articles/{slug}.html", r["title"],
               render_article(b, r), root="../")
        raw_path = os.path.join(RAW, "pages", r["key"])
        if os.path.exists(raw_path):
            from common import decode_html
            original = decode_html(open(raw_path, "rb").read())
            body = rewrite_links(original, b, r)
            with open(os.path.join(SITE, "original", f"{slug}.html"), "w",
                      encoding="utf-8") as f:
                f.write(body)
    log(f"{len(b.kept)} articles + répliques")

    # la page d'accueil d'origine, telle qu'elle était : c'est le menu du site
    raw_home = os.path.join(RAW, "pages", "index.html")
    if os.path.exists(raw_home) and "index.html" in b.docs:
        from common import decode_html
        html_home = decode_html(open(raw_home, "rb").read())
        body = rewrite_links(
            html_home, b, {"key": "index.html"},
            banner=('<div class="replica-note">Page d’accueil du site '
                    'd’origine · <a href="../index.html">accueil</a> · '
                    '<a href="../plan.html">plan</a></div>'))
        with open(os.path.join(SITE, "original", "accueil.html"), "w",
                  encoding="utf-8") as f:
            f.write(body)
        log("page d'accueil d'origine : original/accueil.html")

    # plan
    by_sec = defaultdict(list)
    for r in b.kept:
        by_sec[r["section"]].append(r)
    rows = []
    order = ["1", "2", "3", "4", "5", "6", "7", "8", "DC", "9"]
    total = sum(r["chars"] for r in b.kept)
    for sid in order:
        items = by_sec.get(sid, [])
        if not items:
            continue
        label, desc = SECTIONS[sid]
        chars = sum(i["chars"] for i in items)
        rows.append(
            f'<section class="sec"><h2><a href="sections/{sid.lower()}.html">'
            f'{esc(label)}</a> <span class="count">{len(items)} pages · '
            f'{chars//1000} k car.</span></h2><p>{esc(desc)}</p><ul class="cols">')
        for i in sorted(items, key=lambda x: -x["chars"])[:12]:
            rows.append(f'<li><a href="articles/{b.slug[i["key"]]}.html">'
                        f'{esc(i["title"])[:90]}</a></li>')
        if len(items) > 12:
            rows.append(f'<li><a href="sections/{sid.lower()}.html">'
                        f'tous les {len(items)} articles →</a></li>')
        rows.append("</ul></section>")

    b.page("plan.html", "Plan de la partie alchimique",
           f'<h1>Plan général de la partie alchimique</h1>'
           f'<p class="lead">Reprise du plan établi par Hervé Delboy '
           f'(<a href="articles/{b.slug.get("plan_alchimie.htm","")}.html">'
           f'plan d\'origine</a>), complété par les pages rattachées. '
           f'{len(b.kept)} pages, {total//1_000_000} millions de caractères.'
           f'</p>' + "\n".join(rows))

    for sid, items in by_sec.items():
        label, desc = SECTIONS[sid]
        li = "".join(
            f'<li><a href="../articles/{b.slug[i["key"]]}.html">{esc(i["title"])}</a>'
            f'<span class="dim"> · {i["chars"]//1000} k car.</span></li>'
            for i in sorted(items, key=lambda x: x["title"].lower()))
        pdf = os.path.join(SITE, "pdf", f"section-{sid.lower()}.pdf")
        pdf_li = (f'<p><a class="btn ghost" href="../pdf/section-{sid.lower()}.pdf">'
                  f'Télécharger le PDF</a></p>' if os.path.exists(pdf) else "")
        b.page(f"sections/{sid.lower()}.html", label,
               f'<h1>{esc(label)}</h1><p class="lead">{esc(desc)}</p>'
               f'{pdf_li}<ul class="list">{li}</ul>', root="../")

    # symboles : dictionnaire reconstruit depuis les ancres
    build_symbols(b)
    build_home(b)
    build_general_index(b)
    build_method(b)
    build_notice(b)
    build_out(b)
    build_404(b)


def build_symbols(b: SiteBook) -> None:
    sym_docs = [k for k in ("symboles_alchimiques.html",
                            "symboles_alchimiques_2.html") if k in b.by_key]
    from common import decode_html
    entries, seen = [], set()
    for key in sym_docs:
        path = os.path.join(RAW, "pages", key)
        if not os.path.exists(path):
            continue
        raw = decode_html(open(path, "rb").read())
        # la « Liste » alphabétique du haut de page donne les entrées indexées
        for m in re.finditer(r'<a\s+href="(#[^"]+)"[^>]*>(.*?)</a>', raw,
                             re.I | re.S):
            anchor, label = m.group(1)[1:], re.sub(r"<[^>]+>", "", m.group(2))
            label = html.unescape(re.sub(r"\s+", " ", label)).strip()
            if not label or len(label) > 90:
                continue
            k = strip_accents(label).lower()
            if k in seen:
                continue
            seen.add(k)
            entries.append((label, key, unq(anchor)))
    # entrées sans lien mais dotées d'une ancre
    for key in sym_docs:
        for a in b.docs[key]["anchors"]:
            name = re.sub(r"\s+", " ", a.replace("_", " ")).strip()
            k = strip_accents(name).lower()
            if name and k not in seen:
                seen.add(k)
                entries.append((name, key, a))
    # certaines entrées de la liste n'ont pas d'ancre dans la page d'origine :
    # on ne fabrique pas de fragment qui ne mènerait nulle part
    have = {k: {unq(a).lower() for a in b.docs[k]["anchors"]} for k in sym_docs}
    entries = [(n, k, a, unq(a).lower() in have.get(k, set()))
               for (n, k, a) in entries]
    entries.sort(key=lambda e: strip_accents(e[0]).lower())
    log(f"symboles : {len(entries)} entrées, "
        f"{sum(1 for e in entries if e[3])} avec ancre")

    letters = defaultdict(list)
    for name, key, anchor, has in entries:
        letters[strip_accents(name)[0].upper()].append((name, key, anchor, has))
    nav = " ".join(f'<a href="#L{l}">{l}</a>' for l in sorted(letters))
    blocks = []
    for l in sorted(letters):
        blocks.append(f'<h2 id="L{l}">{l}</h2><ul class="glossary">')
        for name, key, anchor, has in letters[l]:
            frag = "#" + quote(anchor) if has else ""
            blocks.append(
                f'<li><a href="original/{b.slug[key]}.html{frag}"'
                f'{"" if has else " title=\'entrée non ancrée dans la page d\'origine\'"}'
                f'>{esc(name)}</a></li>')
        blocks.append("</ul>")
    b.page("symboles.html", "Dictionnaire des symboles alchimiques",
           f'<h1>Dictionnaire des symboles alchimiques et spagyriques</h1>'
           f'<p class="lead">{len(entries)} entrées, telles que les a indexées '
           f'l\'auteur dans ses planches. Chaque entrée renvoie à la notice '
           f'illustrée.</p><p class="alpha">{nav}</p>' + "".join(blocks))
    log(f"symboles : {len(entries)} entrées")


COMMON_FR = set("""voici voila quant enfin lorsque cependant puis aussi encore
    toujours jamais souvent parfois depuis durant pendant avant apres contre entre
    selon suivant malgre hormis outre parmi vers chez sans sous sur dans avec pour
    par mais donc ni car si comme quand puisque quoique afin ainsi alors autant
    tant tel telle tels telles ceci cela celui celle ceux celles chaque plusieurs
    quelques certain certains aucune aucun autre autres meme memes tout tous toute
    toutes rien personne quelque chose choses partie parties page pages plan
    chapitre livre livres tome note notes introduction preface conclusion
    appendice tableau figure figures planche planches premier premiere deuxieme
    troisieme quatrieme cinquieme sixieme septieme huitieme neuvieme dixieme
    grand grande grands grandes petit petite petits saint sainte notre votre leur
    leurs mon ma mes ton ta tes son sa ses dieu terre nature esprit corps ame
    ciel eau feu air sel or argent cuivre fer plomb etain vif oeuvre matiere
    pierre pierres sages anciens philosophes artiste artistes homme hommes femme
    femmes roi prince comte duc eveque pape pere fils mere enfant gens monde temps
    jour jours nuit annee siecle fois lieu lieux main mains oeil yeux tete coeur
    vie mort amour haine verite raison science art arts notez demeures cathedrales
    fables gardes amoureux bibliotheque philosophorum chemicum introitus donum
    monade faveurs""".split())


def build_names(b: SiteBook) -> None:
    """Index des noms propres : fréquence, articles, contexte.

    Un nom propre est ici une suite capitalisée qui reste capitalisée dans au
    moins 88 % de ses occurrences (les noms communs capitalisés en début de
    phrase tombent), présente dans 10 articles au moins.
    """
    name_docs = defaultdict(set)
    doc_names = defaultdict(set)
    name_count = Counter()
    name_total = Counter()
    name_display = {}
    pat = re.compile(r"\b([A-ZÀ-Ý][a-zà-ÿ]{3,})\b")
    lowpat = re.compile(r"\b([a-zà-ÿ]{4,})\b")
    for r in b.kept:
        text = b.docs[r["key"]]["text"]
        for m in pat.finditer(text):
            w = m.group(1)
            low = strip_accents(w).lower()
            if low in STOP or low in COMMON_FR or len(low) < 4:
                continue
            name_docs[low].add(r["key"])
            doc_names[r["key"]].add(low)
            name_count[low] += 1
            name_display.setdefault(low, w)
        for w in lowpat.findall(strip_accents(text).lower()):
            name_total[w] += 1

    entries = []
    for low, keys in name_docs.items():
        if len(keys) < 10 or name_count[low] < 25:
            continue
        if name_count[low] / max(1, name_total[low]) < 0.88:
            continue
        entries.append((name_display[low], low, len(keys), name_count[low]))
    entries.sort(key=lambda e: strip_accents(e[0]).lower())
    log(f"noms : {len(entries)} entrées")

    # graphe article → noms, utilisé par les pages d'articles
    b.name_slugs = {low: (disp, name_slug(disp)) for disp, low, _, _ in entries}
    for key, lows in doc_names.items():
        names = [b.name_slugs[low] for low in lows if low in b.name_slugs]
        names.sort(key=lambda x: (-name_count[strip_accents(x[0]).lower()], x[0]))
        b.name_by_doc[key] = names[:14]

    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "noms"), exist_ok=True)
    write_json(os.path.join(SITE, "data", "noms.json"),
               [{"n": e[0], "s": name_slug(e[0]), "d": e[2], "c": e[3]}
                for e in entries])

    # page d'index
    letters = defaultdict(list)
    for name, low, nd, cnt in entries:
        letters[strip_accents(name)[0].upper()].append((name, nd, cnt))
    nav = " ".join(f'<a href="#L{l}">{l}</a>' for l in sorted(letters))
    blocks = []
    for l in sorted(letters):
        blocks.append(f'<h2 id="L{l}">{l}</h2><ul class="glossary">')
        for name, nd, cnt in letters[l]:
            blocks.append(f'<li><a href="noms/{name_slug(name)}.html">{esc(name)}</a>'
                          f' <span class="dim">{nd} art.</span></li>')
        blocks.append("</ul>")
    b.page("noms.html", "Index des noms",
           f'<h1>Index des noms</h1><p class="lead">Noms propres présents dans '
           f'au moins trois articles du corpus ({len(entries)} entrées). '
           f'Chaque page donne les passages où le nom apparaît.</p>'
           f'<p class="alpha">{nav}</p>' + "".join(blocks))

    # contextes : un seul parcours du corpus, on ne retient que les noms
    wanted = {low: name for name, low, _, _ in entries}
    ctx = defaultdict(list)
    for r in b.kept:
        text = b.docs[r["key"]]["text"]
        for m in pat.finditer(text):
            low = strip_accents(m.group(1)).lower()
            if low not in wanted:
                continue
            if len(ctx[low]) < 8 and r["key"] not in {c[3] for c in ctx[low]}:
                s = text[max(0, m.start() - 200):m.start() + 260]
                ctx[low].append((r["key"], s.strip(), m.start(), r["key"]))

    for name, low, nd, cnt in entries:
        occ = []
        for k, s, _, _ in ctx[low][:8]:
            occ.append(
                f'<li><a href="../articles/{b.slug[k]}.html">'
                f'{esc(b.docs[k]["title"])[:80]}</a><br>'
                f'<span class="ctx">…{esc(s)}…</span></li>')
        b.page(f"noms/{name_slug(name)}.html", name,
               f'<h1>{esc(name)}</h1>'
               f'<p class="dim">{cnt} occurrences dans {nd} articles</p>'
               f'<p><a href="../recherche.html?q={quote(name)}">'
               f'chercher « {esc(name)} » dans le corpus</a></p>'
               f'<ul class="occ">{"".join(occ)}</ul>', root="../")


def build_home(b: SiteBook) -> None:
    total = sum(r["chars"] for r in b.kept)
    words = sum(len(re.findall(r"\w+", b.docs[r["key"]]["text"])) for r in b.kept)
    nimg = sum(len(b.docs[r["key"]]["images"]) for r in b.kept)
    top = sorted(b.kept, key=lambda r: -r["chars"])[:10]
    cards = "".join(
        f'<li><a href="articles/{b.slug[r["key"]]}.html">{esc(r["title"])}</a>'
        f'<span class="dim"> · {r["chars"]//1000} k car.</span></li>' for r in top)
    b.page("index.html", "Hervé Delboy — alchimie",
           f'<section class="hero"><h1>L\'alchimie d\'Hervé Delboy</h1>'
           f'<p class="lead">Reconstitution de la partie alchimique d\'un site '
           f'disparu, à partir des archives publiques : {len(b.kept)} pages, '
           f'centaines de traités, emblèmes et notices.</p>'
           f'<form action="recherche.html" method="get" class="bigsearch">'
           f'<input name="q" placeholder="Chercher un traité, un auteur, un '
           f'symbole, une question…" autocomplete="off">'
           f'<button>Chercher</button></form>'
           f'<p class="dim">ou <a href="recherche.html?q=&mode=question">'
           f'poser une question</a></p></section>'
           f'<section class="stats"><div><b>{len(b.kept)}</b><span>pages</span></div>'
           f'<div><b>{words/1e6:.1f} M</b><span>mots</span></div>'
           f'<div><b>{total//1_000_000} M</b><span>caractères</span></div>'
           f'<div><b>{len(b.assets)}</b><span>illustrations</span></div>'
           f'<div><b>10</b><span>sections</span></div></section>'
           f'<section class="two"><div><h2>Entrer par le plan</h2>'
           f'<p>Les dix sections établies par l\'auteur : collections, '
           f'emblèmes, symboles, idée alchimique, symbolisme, arsenal, '
           f'laboratoire, textes, Douze Clefs.</p>'
           f'<p><a class="btn" href="plan.html">Plan complet</a></p></div>'
           f'<div><h2>Les plus longs traités</h2><ul class="list">{cards}</ul></div>'
           f'</section>')


def build_general_index(b: SiteBook) -> None:
    """Index alphabétique de tous les articles, toutes sections confondues."""
    letters = defaultdict(list)
    for r in b.kept:
        title = r["title"].strip()
        first = strip_accents(title)[0].upper() if title else "?"
        if not first.isalpha():
            first = "0-9"
        letters[first].append(r)
    nav = " ".join(f'<a href="#L{quote(l)}">{l}</a>' for l in sorted(letters))
    blocks = []
    for l in sorted(letters):
        blocks.append(f'<h2 id="L{quote(l)}">{l}'
                      f' <span class="dim">{len(letters[l])}</span></h2><ul class="list">')
        for r in sorted(letters[l], key=lambda x: strip_accents(x["title"]).lower()):
            blocks.append(
                f'<li><a href="articles/{b.slug[r["key"]]}.html">{esc(r["title"])}</a>'
                f' <span class="dim">· {esc(SECTIONS.get(r["section"], ("", ""))[0])}</span></li>')
        blocks.append("</ul>")
    b.page("index-general.html", "Index général",
           f'<h1>Index général des {len(b.kept)} articles</h1>'
           f'<p class="lead">Tout le corpus, par ordre alphabétique, avec la '
           f'section d\'origine. Les colonnes de gauche (plan, sections, noms, '
           f'symboles) restent les voies d\'entrée thématiques.</p>'
           f'<p class="alpha">{nav}</p>' + "".join(blocks))


def build_404(b: SiteBook) -> None:
    b.page("404.html", "Page introuvable",
           '<h1>Cette page n\'existe pas</h1>'
           '<p class="lead">La reconstitution ne contient pas cette adresse. '
           'Elle correspond peut-être à une page perdue du site d\'origine.</p>'
           '<p><a class="btn" href="index.html">Accueil</a> '
           '<a class="btn" href="plan.html">Plan</a> '
           '<a class="btn" href="recherche.html">Recherche</a></p>')


def build_method(b: SiteBook) -> None:
    sel = b.sel
    b.page("method.html", "Méthode et sources",
           f'<h1>Méthode, sources, limites</h1>'
           f'<h2>Sources</h2>'
           f'<p>Le site d\'origine a eu deux adresses successives : '
           f'<code>perso.club-internet.fr/hdelboy</code> (années 2000) puis '
           f'<code>herve.delboy.perso.sfr.fr</code>. Il n\'existe plus. '
           f'Les pages ont été récupérées dans l\'Internet Archive '
           f'(Wayback Machine) via son API CDX, qui recense toutes les '
           f'captures ; l\'archive.today/archive.fo, protégée par un CAPTCHA, '
           f'n\'a pas pu être aspirée automatiquement.</p>'
           f'<h2>Chaîne de traitement</h2><ol>'
           f'<li>inventaire CDX des deux hôtes (11 000 captures, '
           f'5 500 URL uniques) ;</li>'
           f'<li>aspiration des 375 pages HTML et de leurs images ;</li>'
           f'<li>extraction structurée (titres, paragraphes, liens, images, '
           f'ancres) ;</li>'
           f'<li>délimitation du périmètre à partir du plan alchimique de '
           f'l\'auteur (230 cibles) et des liens internes ;</li>'
           f'<li>exclusion de l\'astrologie, de la musique, des échecs, des '
           f'statistiques et des pages personnelles ;</li>'
           f'<li>génération du site : articles lisibles, répliques des pages '
           f'archivées, index de recherche, axes de consultation.</li></ol>'
           f'<h2>Chiffres</h2><p>{len(b.kept)} pages retenues, '
           f'{fmt(sum(r["chars"] for r in b.kept))} caractères, '
           f'des pages sans contenu exploitable au départ (voir '
           f'<a href="lacunes.html">les lacunes et les pages retrouvées</a>), '
           f'{len([o for o in sel["out"] if o.get("raison","").startswith("hors sujet")])} '
           f'pages écartées comme hors sujet.</p>' +
           f'<h2>Récupération des pages perdues</h2>'
           f'<p>Une seconde campagne a été menée sur d\'autres services, pour '
           f'les pages dont l\'archive ne gardait que la page d\'erreur de '
           f'l\'hébergeur (Club-Internet répondait 200 avec un corps de 404) :</p>'
           f'<ul>'
           f'<li><b>Wayback</b>, toutes captures confondues : 1 page de contenu '
           f'retrouvée, et 2 adresses qui n\'étaient que des doublons d\'une page '
           f'déjà reconstituée ;</li>'
           f'<li><b>Common Crawl</b> (campagnes 2014-2016) : 2 pages retrouvées, '
           f'hors périmètre alchimique ;</li>'
           f'<li><b>Arquivo.pt</b> (archive portugaise, API CDX) : captures du '
           f'site présentes, mais aucune des pages manquantes ;</li>'
           f'<li><b>Ghost Archive</b> : aucune capture ;</li>'
           f'<li><b>archive.today / archive.fo</b> : CAPTCHA et limitation '
           f'(HTTP 429), inexploitable par un programme ;</li>'
           f'<li><b>Memento TimeTravel</b> : service arrêté fin 2025 ;</li>'
           f'<li><b>BnF, Archives de l\'internet</b> : seule piste institutionnelle '
           f'restante pour le Web français de cette époque, mais consultation '
           f'sur place uniquement, sans API.</li></ul>'
           f'<p>Le détail page par page est sur <a href="lacunes.html">la page '
           f'des lacunes</a>.</p>'
           f'<h2>Limites</h2><ul>'
           f'<li>certaines pages ne sont conservées que partiellement ou pas '
           f'du tout (voir <a href="lacunes.html">les lacunes</a>) ;</li>'
           f'<li>les images manquantes sont remplacées par un pixel '
           f'transparent ;</li>'
           f'<li>la recherche est lexicale (BM25 sur passages), non '
           f'sémantique : elle rapproche les formes, pas les idées.</li></ul>')


def build_notice(b: SiteBook) -> None:
    """Notice sur l'auteur, les droits et la provenance des pages."""
    total = sum(r["chars"] for r in b.kept)
    b.page(
        "notice.html", "Notice, droits et provenance",
        '<h1>Notice, droits et provenance</h1>'

        '<h2>L’auteur et son travail</h2>'
        '<p>Hervé Delboy a tenu, à titre personnel, un site consacré à ce qu’il '
        'nommait lui-même « la mesure » : pierres, étoiles, sons, nombres. '
        'L’alchimie y occupait la place centrale, et c’est cette partie que '
        'reconstitue le présent site. Les archives publiques en gardent des '
        'captures de 1999 à 2016, réparties sur deux adresses successives.</p>'

        '<p>Ce qu’il y a fait est rare, et d’une autre nature que le commentaire. '
        'Là où la plupart des pages consacrées à l’art hermétique se contentent '
        'de citer, il a transcrit : l’<i>Atalanta fugiens</i>, la <i>Toison '
        'd’or</i> de Trismosin, les <i>Douze Clefs</i>, le <i>Mutus liber</i>, la '
        '<i>Table d’émeraude</i>, les traités de Basile Valentin, de Ripley, de '
        'Flamel, le <i>Cosmopolite</i>, les recueils de Berthelot et les études '
        'de Chevreul. Des dizaines de milliers de lignes, souvent données en '
        'entier, sans coupes, avec leurs planches.</p>'

        '<p>À cette masse il a imposé une architecture : un plan en dix '
        'sections, un dictionnaire des symboles, un index des noms, des notices '
        'introductives, des renvois d’une page à l’autre. Le lecteur n’était pas '
        'invité à croire, mais à lire : c’est la démarche d’un lettré, non '
        'd’un prosélyte. Son sous-titre le disait assez — <i>entre science et '
        'poésie</i> — et son introduction rappelait que Newton, Berthelot, '
        'Chevreul et Jung avaient pris ces textes au sérieux.</p>'

        '<p>Ce travail était offert : les pages archivées ne portent aucune '
        'publicité, aucun accès payant, aucun extrait tronqué. Pendant près de '
        'dix-sept ans, il a été consultable sans contrepartie.</p>'

        '<h2>Adresses historiques</h2>'
        '<p>Le site a eu deux adresses :</p>'
        '<ul>'
        '<li><code>http://perso.club-internet.fr/hdelboy/</code> — captures de '
        'novembre 1999 à septembre 2009 ;</li>'
        '<li><code>http://herve.delboy.perso.sfr.fr/</code> — captures d’août '
        '2009 à novembre 2016.</li>'
        '</ul>'
        '<p>Ces adresses ne répondent plus. Les pages réunies ici proviennent de '
        'l’Internet Archive (Wayback Machine) ; la date et l’URL exacte de la '
        'capture utilisée sont indiquées en tête de chaque article, et chaque '
        'réplique renvoie à la capture d’origine.</p>'

        '<h2>Droits</h2>'
        '<p>Les textes, transcriptions, traductions, notices, mises en page et '
        'images reproduits ici sont l’œuvre d’Hervé Delboy ou des auteurs qu’il '
        'citait. Ils demeurent protégés par le droit d’auteur et appartiennent à '
        'leurs auteurs et à leurs ayants droit. La mention « © Hervé Delboy et '
        'ayants droit » figure au pied de chaque page.</p>'
        '<p>Cette reconstitution constitue un usage de consultation, de '
        'recherche et de conservation : elle ne fait l’objet d’aucune vente, '
        'd’aucune diffusion publicitaire, d’aucune exploitation commerciale. '
        'Elle existe parce que le site d’origine a disparu et que ses textes ne '
        'sont plus accessibles autrement.</p>'
        '<p>Toute demande d’un auteur ou d’un ayant droit — retrait d’une page '
        'ou d’une image, correction d’une mention, précision de crédit — sera '
        'suivie d’effet sans délai.</p>'

        '<h2>Fidélité au texte</h2>'
        '<p>Les pages sont données telles qu’Hervé Delboy les avait établies : '
        'mêmes graphies, mêmes coupures de mots, mêmes coquilles, même mise en '
        'page. C’est là leur valeur documentaire, et c’est ce qui permet de les '
        'citer. Les seules interventions portent sur l’encodage des caractères, '
        'les liens et les images, pour que les textes s’affichent et se '
        'parcourent. Les pages que l’archive n’a pas conservées sont signalées '
        'comme telles, à l’endroit où elles manquent.</p>'

        '<h2>L’appareil de consultation</h2>'
        '<p>Le plan, les index, les planches, les dossiers et le moteur de '
        'recherche servent à lire l’œuvre. Ils sont signalés comme tels.</p>')


def build_out(b: SiteBook) -> None:
    sel = b.sel
    rec = read_json(os.path.join(DATA, "recovered.json"), {}) or {}
    aliases = read_json(os.path.join(DATA, "aliases.json"), {}) or {}
    failed = read_json(os.path.join(DATA, "recovery_failed.json"), {}) or {}
    lost = [o for o in sel["out"] if o.get("raison", "").startswith("capture")]
    still = [o for o in lost if o["key"] not in rec and o["key"] not in aliases]
    other = [o for o in sel["out"] if o not in lost]

    rec_li = "".join(
        f'<li><code>{esc(k)}</code> — {esc(b.docs[k]["title"]) if k in b.docs else ""}'
        f'<br><span class="dim">retrouvée via {esc(v.get("source", ""))}'
        f' ({v.get("bytes", 0)} octets)</span></li>' for k, v in rec.items())
    alias_items = []
    for k, v in sorted(aliases.items()):
        target = (f'<a href="articles/{b.slug[v]}.html">{esc(b.docs[v]["title"])}</a>'
                  if v in b.slug else f'<code>{esc(v)}</code>')
        alias_items.append(f'<li><code>{esc(k)}</code> → {target} '
                           f'<span class="dim">(<code>{esc(v)}</code>, même page)</span></li>')
    alias_li = "".join(alias_items)
    lost_items = []
    for o in still:
        why = failed.get(o["key"], "")
        extra = f' <span class="dim">({esc(why)})</span>' if why else ""
        lost_items.append(f'<li><code>{esc(o["key"])}</code> — '
                          f'{esc(o["title"])}{extra}</li>')
    lost_li = "".join(lost_items)
    n_alias = len(aliases)
    n_total = len(still) + len(rec) + n_alias
    other_li = "".join(f'<li><code>{esc(o["key"])}</code> — {esc(o["title"])}</li>'
                       for o in sorted(other, key=lambda o: o["key"]))

    b.page("lacunes.html", "Pages perdues et pages retrouvées",
           f'<h1>Pages perdues, pages retrouvées</h1>'
           f'<p class="lead">{n_total} pages du site d\'origine étaient '
           f'référencées sans contenu exploitable : l\'hébergeur Club-Internet '
           f'servait sa page d\'erreur 404 avec un code HTTP 200, si bien que '
           f'l\'archive a conservé des captures vides. Une campagne de '
           f'récupération a été menée sur plusieurs services.</p>'
           f'<h2>Retrouvées ({len(rec)})</h2>'
           f'<ul class="list">{rec_li or "<li>aucune</li>"}</ul>'
           f'<h2>Anciennes adresses d\'une page présente ({n_alias})</h2>'
           f'<p class="dim">Le site a été refondu plusieurs fois : ces adresses '
           f'citées par les captures anciennes n\'ont jamais été archivées avec '
           f'un contenu, parce que la page avait été renommée entre-temps. Le '
           f'texte est bien dans la reconstitution sous son nouveau nom, et les '
           f'liens qui pointaient vers l\'ancienne adresse ont été réparés.</p>'
           f'<ul class="list">{alias_li}</ul>'
           f'<h2>Définitivement perdues ({len(still)})</h2>'
           f'<p class="dim">Aucune capture de contenu n\'existe : la page était '
           f'déjà morte chez l\'hébergeur au moment de l\'archivage, et les '
           f'archives consultées n\'en gardent que la page d\'erreur.</p>'
           f'<ul class="list mono">{lost_li}</ul>')
    b.page("hors-perimetre.html", "Hors périmètre",
           f'<h1>Ce qui a été écarté</h1>'
           f'<p class="lead">Le site mêlait plusieurs domaines. Sont exclus de '
           f'cette reconstitution : l\'astrologie (directions primaires, '
           f'transits, statistiques astrologiques), la musique, les études '
           f'd\'échecs, les logiciels de statistiques et les pages '
           f'personnelles. {len(other)} pages concernées.</p>'
           f'<ul class="list mono">{other_li}</ul>')


def main() -> None:
    b = SiteBook()
    log(f"{len(b.kept)} pages dans le périmètre")
    build(b)
    log("site généré dans", SITE)


if __name__ == "__main__":
    main()
