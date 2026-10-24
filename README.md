# Hervé Delboy — alchimie

Le site d'Hervé Delboy sur l'alchimie, années 2000, remis en ligne depuis les archives du web :
https://mauktenieb.github.io/alchimie-delboy/

## Le site

- Les pages de l'auteur, telles qu'il les a écrites et mises en page : 247 pages en dix sections, dans l'ordre de son plan. L'écran titre reprend sa page « La clef du labyrinthe hermétique ».
- Une barre de lecture en tête de chaque page : sommaire, recherche (touche `/`), page précédente et suivante, taille, police, colonne, modes nuit et noir et blanc, loupe et visionneuse des planches, lecture à voix haute, surlignages et notes, traduction en anglais, PDF et EPUB de la page, PDF de la section.
- Le sommaire : chaque page avec sa date de révision, ses caractères, ses images, la date et le lien de sa capture.
- La recherche : 18 427 passages, syntaxe ci-dessous ; un résultat ouvre la page de l'auteur au passage, surligné.
- Le dictionnaire des symboles de l'auteur ; dix livres PDF, un par section, imprimés depuis ses pages ; la notice : provenance, fidélité, droits.

## Contenu

| | |
|---|---|
| pages d'alchimie | 247 |
| pages de l'auteur dans `site/original/` | 249 (avec l'accueil du site et l'accueil Club-Internet de 2002) |
| caractères | 27,2 millions |
| images | 3 002 planches et figures ; 3 106 fichiers, 103 Mo |
| passages indexés | 18 427 |
| mots indexés | 62 580 |
| entrées du dictionnaire des symboles | 90 |
| entrées du filtre « Domaines » de la recherche | 188 |
| pages écartées (astrologie, musique, échecs, statistiques, pages personnelles) | 88 |

## Provenance

| adresse d'origine | captures de la Wayback Machine |
|---|---|
| `http://perso.club-internet.fr/hdelboy/` | novembre 1999 – septembre 2009 |
| `http://herve.delboy.perso.sfr.fr/` | août 2009 – novembre 2016 |

Club-Internet renvoyait sa page d'erreur avec le code HTTP 200 : l'archive enregistrait alors une page vide. 45 pages citées par le site sont dans ce cas. Bilan de la récupération : 6 retrouvées, 6 anciennes adresses reliées à leur page sous un nouveau nom, 33 perdues. Détail : `site/lacunes.html`.

| service consulté | résultat |
|---|---|
| Wayback Machine, toutes captures et variantes d'adresse | pages retrouvées, dont le tableau périodique de Mendeleïev et l'accueil Club-Internet de 2002 |
| Common Crawl (2013-2019) | 1 page, hors alchimie |
| Arquivo.pt | captures du site, zéro page parmi les manquantes |
| Ghost Archive | zéro capture |
| archive.today | CAPTCHA, lecture par programme impossible |
| BnF, Archives de l'internet | consultation sur place seulement |

Notes sur la source :

- Les pages déclarent ISO-8859-1 et emploient cp1252 : le décodage rétablit œ, ’ et les tirets.
- Les ancres s'écrivent avec ou sans guillemets, parfois avec des entités HTML (`Prot&eacute;e`) : la réécriture des liens les reconnaît toutes.
- Quelques mots coupés (`c arbonate`, `m étal`) viennent de la mise en page d'origine et restent tels quels.

## Lancer en local

```bash
python serve.py          # http://127.0.0.1:8788/
```

Le serveur compresse l'index de recherche (43 Mo, 13 Mo compressés). Un navigateur bloque la lecture de l'index sur une page ouverte en `file://`.

## Publier

Le workflow `.github/workflows/pages.yml` publie `site/` sur GitHub Pages à chaque envoi sur `main` (Settings → Pages → Source : GitHub Actions). `site/.nojekyll` garde les fichiers tels quels. Le plus gros fichier pèse 47 Mo, sous la limite de 100 Mo de GitHub. `.gitignore` garde hors du dépôt le corpus intermédiaire (`cache/`, `data/`, `raw/`, 130 Mo).

## Recherche

| écriture | effet |
|---|---|
| `mercure soufre` | l'un ou l'autre, classés par pertinence (BM25) |
| `"pierre philosophale"` | expression exacte |
| `+soufre +antimoine` | les deux termes dans le même passage |
| `-astrologie` | exclusion |
| `philosoph*` | préfixe |
| `mercur~` | une lettre d'écart |
| `titre:` `fichier:` `section:` | titre, nom du fichier d'origine, section |

Une requête charge les fragments d'index des premières lettres de ses termes, puis les passages affichés : 20 à 300 ms. Facettes : sections, genre (textes transcrits, études de l'auteur), pages illustrées, domaines. Export CSV ; la requête et les filtres restent dans l'adresse.

## Chaîne de traitement

```bash
cd scripts
python 01_inventory.py    # captures de la Wayback Machine (API CDX), deux hôtes
python 02_fetch_pages.py  # 375 pages HTML
python 03_extract.py      # titres, paragraphes, liens, images, ancres
python 04_classify.py     # périmètre alchimie, anciennes adresses
python 05_assets.py       # images
python 06_build_site.py   # répliques, sections, pages perdues
python 07_build_index.py  # index de recherche
python 08_verify.py       # liens, ancres, images
python 09_recover.py      # pages perdues : autres captures, autres services
python 10_axes.py         # entrées du filtre « Domaines »
python 11_portail.py      # ancien portail, remplacé par l'étape 13
python 12_pdf.py          # anciens livres PDF, remplacés par l'étape 15
python 13_lecture.py      # barre de lecture, sommaire, sections
python 14_pages.py        # notice, pages perdues, pages écartées, symboles, 404
python 15_pdf.py          # dix livres PDF, imprimés par Chromium depuis les pages de l'auteur
python 16_seo.py          # titres, descriptions, données structurées, plan du site, llms.txt
```

Les étapes 01 à 12 lisent le corpus intermédiaire ; 13 à 16 travaillent sur `site/` seul, dans cet ordre. Le périmètre part du plan de l'auteur (`plan_alchimie.htm`), suit ses liens internes et écarte l'astrologie, la musique, les échecs et les statistiques ; `FORCED_IN` et `FORCED_OUT` (`04_classify.py`) tranchent les cas limites.

## Droits

© Hervé Delboy (auteur du fonds complet, années 2000). Tout ici, remis en ligne, demeure la propriété d'Hervé Delboy et des auteurs qu'il citait. Contact : mauktenieb chez Gmail.
