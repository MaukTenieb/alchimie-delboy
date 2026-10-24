# Hervé Delboy — reconstitution de la partie alchimique

Site disparu (`perso.club-internet.fr/hdelboy`, puis
`herve.delboy.perso.sfr.fr`), reconstitué depuis les archives publiques, avec :

- **la réplique** de chaque page d'origine (markup archivé, images locales,
  liens et ancres réécrits vers le site local) ;
- **une encyclopédie** : 247 articles lisibles, plan de l'auteur, index
  alphabétique, index des noms, dictionnaire des symboles, index des mots,
  **axes d'autorité** (auteurs, œuvres, thèmes, époques, pays, matériel,
  techniques, matériaux, illustrations, textes) ;
- **un moteur de recherche** complet sur 18 427 passages (25 millions de
  caractères).

## Lancer le site

```bash
python serve.py          # http://127.0.0.1:8788/
```

Le serveur sert les fichiers avec compression (l'index de recherche fait
43 Mo, ~13 Mo compressés) et les bons types MIME. Ouvrir les pages par
`file://` empêche le navigateur de charger l'index.

## Ce que contient le corpus

| | |
|---|---|
| pages aspirées (site entier) | 375 |
| pages retenues (alchimie) | 247 |
| caractères de texte | 25 157 781 |
| passages indexés | 18 427 |
| termes indexés | 62 580 (dont 27 648 vus une seule fois) |
| illustrations locales | 3 119 (~100 Mo) |
| pages HTML générées | 1 454 (articles, répliques, axes, index) |
| noms propres indexés | 740 |
| entrées du dictionnaire des symboles | 90 |
| entrées d'autorité (8 catégories) | 188 |
| pages écartées (astrologie, musique, échecs, stats) | 88 |

## Architecture du site

Depuis le 24 octobre 2026 (étapes 13 et 14), le site se lit comme l'original :
les pages de l'auteur sont la lecture, sans réécriture.

```
site/
  index.html            écran titre : « La clef du labyrinthe hermétique »
                        (réplique d'intro-alchimie, chemins ramenés à la racine)
  original/<slug>.html  les 248 pages de l'auteur, markup archivé ; liens et
                        images rendus locaux ; une barre de lecture en tête
  barre.js, barre.css   barre de lecture : précédent et suivant dans l'ordre du
                        plan, taille (60 à 250 %), police, colonne, modes
                        original, noir et blanc, nuit, loupe et visionneuse des
                        planches, PDF de la page, EPUB de la page, PDF de la
                        section ; #passage=<mots> ouvre la page au passage cité
  sommaire.html         les 247 pages dans l'ordre du plan : révision,
                        caractères, images, date et lien de la capture
  sections/<id>.html    une section du plan, même tableau, PDF de la section
  recherche.html        moteur (interface) ; moteur.js : BM25, facettes
  symboles.html         dictionnaire des symboles de l'auteur
  notice.html           provenance, fidélité, droits
  lacunes.html          pages perdues, retrouvées, adresses renommées
  hors-perimetre.html   pages écartées
  pdf/                  dix livres PDF, un par section
  data/search/          index éclaté ; data/nav.json : ordre du plan
  articles/<slug>.html  anciennes adresses, renvoi vers original/<slug>.html
```

Pages retirées le 24 octobre 2026 et remplacées par un renvoi au sommaire :
portail, plan, guide, index alphabétique, index des mots, index des noms,
axes, notions, dossiers, méthode, liseuse, textes, illustrations.

## Publier sur GitHub

Le dépôt est prêt pour GitHub Pages : le workflow `.github/workflows/pages.yml`
publie le dossier `site/` à chaque envoi sur `main` (Settings → Pages →
Source : GitHub Actions). `site/.nojekyll` évite que Jekyll ne réécrive les
fichiers.

Ce qui se publie : `site/` (348 Mo, plus gros fichier 47 Mo — un livre PDF),
le `README.md`, `serve.py`, `scripts/`. Ce qui ne se publie pas, et que `.gitignore` exclut :
`cache/`, `data/`, `raw/` (le corpus intermédiaire, 130 Mo, reconstituable par
les étapes 01 à 05, et fourni dans l'archive complète).

Aucun fichier ne dépasse la limite GitHub de 100 Mo ; l'ensemble reste sous
le Go recommandé. Les textes, images et la mise en page restent la propriété
de leurs auteurs et ayants droit : `notice.html` porte la mention de droits,
les deux adresses historiques du site et la provenance des captures.

## Le moteur de recherche

L'index est **éclaté** pour rester utilisable : une requête ne charge que les
fragments des premières lettres de ses termes (35 fragments), puis les seaux
des passages qu'elle affiche (12 seaux). Métadonnées : 0,9 Mo. Requête
typique : 20 à 300 ms.

Syntaxe reconnue :

| écriture | effet |
|---|---|
| `mercure soufre` | l'un ou l'autre, classement BM25 |
| `"pierre philosophale"` | expression exacte (adjacence vérifiée) |
| `+soufre +antimoine` | les deux termes dans le même passage |
| `-astrologie` | écarte les articles qui en parlent |
| `philosoph*` | préfixe |
| `mercur~` | tolère une faute de frappe |
| `titre:` `fichier:` `section:` | restriction de champ |
| `mercure \| argent` | alternative équilibrée |

Mesures faites sur le site en fonctionnement : sur un jeu de 16 requêtes
visant un texte précis, 11 le placent en tête et 15 dans les dix premiers
(MRR 0,75) ; sur 24 termes tirés au hasard dans le vocabulaire, 23 retrouvent
l'article qui les contient. Requête type : 20 à 300 ms, 1 à 4 fragments
chargés.

Fonctions de l'interface : suggestions (mots, noms, sections), facettes calculées sur les résultats (sections, nature, articles
illustrés), **filtres par axes d'autorité** (OU dans une catégorie, ET entre
catégories), tri (pertinence, titre, longueur, date d'archivage), trois
extraits par article avec renvoi au passage dans la page de l'auteur
(`#passage=`), export CSV,
état dans l'URL, raccourci `/`.

## Les axes d'autorité

`10_axes.py` repère dans les paragraphes 188 entrées réparties en huit
catégories — auteurs (40), œuvres (22), thèmes (34), époques (9), pays et
régions (15), matériel et instruments (16), techniques et procédés (25),
matériaux et substances (27) — à partir d'un lexique de formes françaises,
latines et de graphies anciennes. Chaque entrée a sa fiche : effectifs,
répartition par section, passages situés, entrées voisines, et un lien pour
filtrer le corpus sur cet axe. Rien n'est inventé : la fiche ne fait que
réunir ce que le corpus dit de l'entrée.

## Chaîne de traitement

```bash
cd scripts
python 01_inventory.py    # API CDX : 39 772 captures, deux hôtes
python 02_fetch_pages.py  # aspiration des 375 pages HTML (cache + reprise)
python 03_extract.py      # titres, paragraphes, liens, images, ancres
python 04_classify.py     # périmètre alchimie + renommages d'adresses
python 05_assets.py       # images référencées par le corpus
python 06_build_site.py   # articles, répliques, sections, index, lacunes
python 07_build_index.py  # index éclaté du moteur (passages, postings)
python 08_verify.py       # contrôle liens / ancres / orphelins / images
python 09_recover.py      # pages perdues : autres archives et services
python 10_axes.py         # index d'autorité, notions, concordance, planches
python 11_portail.py      # portail, guide des index, dossiers de lecture
python 12_pdf.py          # dix livres PDF dans site/pdf/
python 13_lecture.py      # lecture sur les pages de l'auteur, sommaire, sections
python 14_pages.py        # notice, pages perdues, pages écartées, symboles, 404
```

Les étapes 13 et 14 tournent sur `site/` seul, sans le corpus intermédiaire.

Chaque étape est idempotente et reprend où elle s'est arrêtée (`cache/`).
L'ordre compte : `06` reconstruit `site/`, donc `07` et `10` doivent suivre.

### Délimitation du périmètre

`plan_alchimie.htm` — le plan des sections alchimiques établi par l'auteur —
sert de noyau (230 cibles, 8 sections + le dossier des *Douze Clefs*). Les
pages atteintes par liens internes sont ajoutées, puis un classement lexical
(densité de vocabulaire alchimique / astrologique) écarte ce qui relève de
l'astrologie, de la musique, des échecs ou des statistiques. Les cas ambigus
ont été tranchés un par un (`FORCED_IN` / `FORCED_OUT` dans `04_classify.py`).

### Adresses anciennes

Le site a été refondu plusieurs fois. Quatre pages citées par les captures de
2001-2002 n'existent plus sous ce nom, mais leur texte est bien présent sous
un autre :

| ancienne adresse | page présente |
|---|---|
| `portanus.htm` | `pontanus.html` |
| `toyson_d_or.htm` | `toyson.html` |
| `zodiaque_alch.htm` | `zodiaque_alchimique.html` |
| `origines.htm` | `origine_alchimie.htm` |

Preuve : le plan de l'auteur (2009-2013) ne cite que les nouveaux noms, et les
captures de ces années-là ne connaissent que ceux-là. `common.RENAMES` porte
la correspondance ; `04` la vérifie contre le corpus, `06` répare les liens
qui pointaient vers l'ancienne adresse, `lacunes.html` les publie.

## Pages perdues : ce qui a été tenté

Les pages sans contenu ne manquaient pas par hasard : **Club-Internet
renvoyait sa page d'erreur 404 avec un code HTTP 200**. L'archive a conservé
des captures « valides » mais vides (≈ 6 958 octets compressés), et le
dédoublonnage par empreinte (`collapse=digest`) les avait fait disparaître de
l'inventaire initial. C'est corrigé (`raw/cdxall_*.txt`).

| service | état | résultat |
|---|---|---|
| Wayback, toutes captures + variantes d'URL | en ligne | 1 page de contenu + 2 doublons d'adresse |
| Common Crawl (2013-2019, API CDX + WARC) | en ligne | 2 pages (hors alchimie) |
| Arquivo.pt (archive portugaise) | en ligne | captures du site, aucune page manquante |
| Ghost Archive | en ligne | aucune capture (404) |
| archive.today / archive.fo / .is | CAPTCHA | HTTP 429, inexploitable par programme |
| Memento TimeTravel | arrêté fin 2025 | — |
| BnF, Archives de l'internet | sur place uniquement, sans API | piste restante à la main |

Bilan : **3 pages retrouvées** (dont le tableau périodique de Mendeleïev,
planche citée par *Les Origines de l'alchimie* de Berthelot), **6 adresses
anciennes** reliées à une page présente, **35 pages définitivement perdues** —
la page était déjà morte chez l'hébergeur au moment de l'archivage. Détail sur
`site/lacunes.html`.

## Notes sur les sources

- **archive.fo / archive.today** (`https://archive.fo/dHfCA`) est protégé par
  un CAPTCHA : inexploitable par un programme. La reconstitution vient de
  l'**Internet Archive**, qui garde l'intégralité des deux hôtes.
- **Reporhogo** (`https://mauktenieb.github.io/reporhogo/`) est un collecteur
  d'URL de recherche sur 41 forges : interrogé sur « wayback machine
  scraper », il renvoie `melgrove/wayback-machine-scraper`,
  `sangaline/wayback-machine-scraper`, etc., qui font la même chose que
  l'étape 02. Le pipeline d'ici a été écrit sur place pour garder la main sur
  le choix des captures, le ré-encodage cp1252 → UTF-8 et le filtrage
  thématique.
- Les pages déclarent ISO-8859-1 mais sont en cp1252 : le décodage a été
  corrigé (œ, ’, —), sinon la recherche ratait tous les « œuvre ».
- Les ancres du site s'écrivent avec ou sans guillemets, parfois après
  d'autres attributs et avec des entités HTML (`Prot&eacute;e`) : la
  réécriture et le contrôle en tiennent compte, sinon des milliers de liens
  internes tombaient à côté.
- Quelques mots sont coupés dans la source (`c arbonate`, `m étal`) :
  artefacts de mise en page de l'époque, conservés tels quels.

## Limites

- La recherche est lexicale (BM25 sur passages, préfixes, fautes de frappe) : elle rapproche les formes, pas les idées.
- Les axes sont un repérage lexical : ils trouvent les mentions, pas les
  analyses implicites.
- Certaines pages ne sont conservées que partiellement, et les images
  manquantes sont remplacées par un pixel transparent.

## Droits

Les textes, transcriptions, traductions, notices, mises en page et images
reproduits restent la propriété d'Hervé Delboy, des auteurs qu'il citait et de
leurs ayants droit. La mention « © Hervé Delboy et ayants droit » figure au
pied de chaque page ; `site/notice.html` expose la provenance des captures,
les deux adresses historiques et l'engagement de retrait.

Le site est publié à des fins de consultation, de recherche et de
conservation, sans publicité ni exploitation commerciale. Toute demande d'un
auteur ou d'un ayant droit — retrait d'une page ou d'une image, correction
d'une mention, précision de crédit — est suivie d'effet sans délai, par les
signalements (Issues) de ce dépôt.
