# Consigne de publication

**Destinataire** : l'agent qui dispose d'un accès en écriture au compte GitHub du propriétaire.
**Objet** : mettre en ligne, tel quel, le site statique contenu dans ce dossier. Aucune modification de contenu n'est demandée. Aucune amélioration, aucun nettoyage, aucune réécriture.

---

## 1. Ce que vous recevez

| | |
|---|---|
| fichiers | 4 728 |
| taille | 332 Mo |
| pages HTML | 1 493 |
| plus gros fichier | `site/pdf/section-dc.pdf` — 47 072 693 octets |

```
site/                     le site complet, prêt à servir
  index.html              accueil (portail)
  plan.html, guide.html, recherche.html, parcours.html, notice.html…
  articles/               247 articles de l'encyclopédie
  original/               les répliques des pages d'origine
  sections/               pages de section
  axes/, noms/, mots/     index d'autorité, index des noms, concordance
  assets/                 3 106 images (103 Mo)
  data/                   index de recherche éclaté (43 Mo) — indispensable
  pdf/                    10 livres PDF (106 Mo)
  style.css, moteur.js
  .nojekyll               obligatoire (voir §2)
scripts/                  chaîne de production Python (13 fichiers)
.github/workflows/pages.yml   publication automatique vers Pages
README.md, serve.py, .gitignore
```

Le site est **statique** : aucune dépendance, aucun build, aucun serveur. `site/` est le dossier à publier.

## 2. Règles absolues

1. **Ne rien modifier.** Pas de renommage, pas de minification, pas de conversion d'encodage, pas de « correction » de liens. Les noms de fichiers comportent majuscules, accents et `~` : c'est voulu.
2. **Ne pas exécuter `scripts/`.** Ces scripts exigent 130 Mo de corpus absent de ce dossier et reconstruiraient `site/` intégralement.
3. **Ne pas supprimer `site/.nojekyll`.** Sans lui, Jekyll ignore les fichiers commençant par `_` et casse des pages.
4. **Ne pas ajouter de licence libre** (MIT, CC0, CC BY…). Les textes et images appartiennent à Hervé Delboy et à ses ayants droit, pas au propriétaire du dépôt.
5. **Ne pas toucher** à `site/notice.html` ni au pied de page de droits présent sur les 1 493 pages.
6. **Un seul dépôt, public.** GitHub Pages avec un compte gratuit exige un dépôt public.
7. **Rien publier ailleurs** : ni Netlify, ni Vercel, ni Cloudflare Pages, ni nom de domaine. Un dépôt, une URL `github.io`.
8. **Ne pas créer de tag ni de release**, ne pas réécrire l'historique, ne pas forcer de push sur un dépôt existant.

## 3. Procédure

### 3.1 Créer le dépôt

Nom proposé : `delboy-alchimie`. Vide : ni README, ni licence, ni `.gitignore` (ils sont déjà dans le dossier).

### 3.2 Envoyer les fichiers

Depuis la racine de ce dossier :

```bash
git init -b main
git config core.compression 9
git config http.postBuffer 524288000
git add -A
git commit -m "Reconstitution de la partie alchimique du site d'Hervé Delboy"
git remote add origin https://github.com/COMPTE/delboy-alchimie.git
git push -u origin main
```

Notes d'exécution :

- 332 Mo en un seul envoi : compter 10 à 40 minutes selon la liaison. Ne pas interrompre, ne pas relancer en parallèle.
- Si l'envoi échoue en cours de route (`RPC failed`, `HTTP 411`), relancer `git push` : il reprend, il ne recommence pas.
- Le plus gros fichier fait 47 Mo : très en dessous de la limite GitHub de 100 Mo. Aucun Git LFS n'est nécessaire — et **il ne faut pas l'introduire**.
- `git add -A` est sûr ici : le dossier ne contient que le site, les scripts et la documentation.

### 3.3 Activer Pages

Interface : **Settings → Pages → Build and deployment → Source : GitHub Actions**.

API, si l'agent n'a que l'API :

```
POST /repos/COMPTE/delboy-alchimie/pages
{ "build_type": "workflow" }
```

Le workflow `Publier le site` (déjà présent) se déclenche alors. Il prend `site/` et le publie. Ne pas ajouter d'étape de build : il n'y en a pas besoin.

### 3.4 Attendre et relever

L'adresse est `https://COMPTE.github.io/delboy-alchimie/`. Elle n'est valide qu'une fois le workflow terminé (2 à 5 minutes après le push).

## 4. Vérifications à faire, et à rapporter

À exécuter sur l'URL publique, pas en local. Rapporter le code HTTP et la taille réels de chaque point.

| # | requête | attendu |
|---|---|---|
| 1 | `/` | 200, HTML contenant « Hervé Delboy » |
| 2 | `/data/search/meta.json` | 200, JSON avec une clé `docs` (247 entrées) |
| 3 | `/articles/` (un article au hasard) | 200, plus de 20 000 octets |
| 4 | `/original/` (une réplique) | 200 |
| 5 | `/pdf/section-dc.pdf` | 200, `Content-Length` = 47 072 693 |
| 6 | `/assets/` (une image) | 200, `Content-Type: image/*` |
| 7 | `/notice.html` | 200, contient « ayants droit » |
| 8 | 20 liens internes pris au hasard dans l'accueil | 20 × 200 |

Si le point 2 échoue alors que le point 1 réussit, c'est que `site/data/` n'a pas été envoyé : corriger l'envoi, ne pas régénérer l'index.

## 5. Ce qu'il ne faut pas « améliorer »

- pas de réécriture du `README.md` ;
- pas de workflow supplémentaire (lint, tests, cache) ;
- pas d'analytics, pas de cookie, pas de police distante, pas de CDN ;
- pas de fichier `CNAME` ;
- pas de « correction » des liens : ils ont été vérifiés (160 297 liens, 0 mort, 0 ancre cassée, 0 page orpheline).

## 6. En cas d'échec

| symptôme | cause | action |
|---|---|---|
| Pages renvoie 404 après le workflow | source restée sur « Deploy from a branch » | remettre `Source : GitHub Actions` |
| le workflow échoue à `configure-pages` | Pages pas encore activé | refaire §3.3, relancer le workflow |
| pages sans style, images cassées | `.nojekyll` absent, ou `site/` publié au lieu de sa racine | vérifier l'artefact : la racine doit contenir `index.html` |
| push refusé, dépôt déjà peuplé | dépôt créé avec un README initial | `git pull --rebase` puis pousser ; ne pas forcer |
| Actions désactivées sur le compte | réglage du compte | le signaler, ne pas contourner en publiant ailleurs |

## 7. Rapport attendu

1. l'URL publique ;
2. le SHA du commit poussé et le lien du run Actions ;
3. le tableau du §4 rempli avec les codes et tailles réellement observés ;
4. toute anomalie, dite telle quelle, sans la corriger de sa propre initiative.
