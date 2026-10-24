/* Moteur de recherche du corpus Delboy — alchimie.
 *
 * Index éclaté (scripts/07_build_index.py) :
 *   data/search/meta.json       articles, sections, df, longueurs de passages
 *   data/search/post/<x>.json   occurrences des termes commençant par <x>
 *   data/search/pass/<n>.json   passages, seau n = id % 12
 *
 * Une requête ne charge que les fragments utiles, puis les seaux des passages
 * qu'elle affiche. Le moteur applique BM25 sur les passages, agrège par
 * article, et expose des facettes calculées sur les résultats.
 */
const Moteur = (() => {
  const STOP = new Set(`le la les un une des du de d au aux a et ou mais donc or ni
car que qui quoi dont ce cet cette ces celui celle ceux celles son sa ses leur
leurs il elle ils elles nous vous je tu on se sy en y ne pas plus moins tres
etre avoir fait faire comme tout tous toute toutes autre autres meme aussi
bien peut peu sans sous sur dans par pour avec contre entre chez vers est sont
ete etait etaient fut furent ont avait avaient ainsi alors quand depuis
pendant apres avant encore non oui si deux trois quatre cinq premier premiere
second seconde partie chapitre plan page suite fin debut lors selon cest setait
nest quun quune jusqu lorsqu puis ici cela ceci chaque plusieurs certains
certaines`.split(/\s+/).filter(Boolean));

  const TRUNC = 7;
  const BUCKETS = 12;
  const K1 = 1.2, B = 0.75;

  /* thésaurus alchimique : équivalences de vocabulaire entre traditions */
  const THES = {
    mercure: ["vif-argent", "hydrargyre", "argent-vif", "lune", "esprit"],
    soufre: ["feu", "ame", "or", "sulfur"],
    sel: ["nitre", "alkali", "sel marin", "spagyrie"],
    pierre: ["pierre philosophale", "elixir", "teinture", "or potable", "magistere"],
    oeuvre: ["grand oeuvre", "magnum opus", "putrefaction", "albedo", "rubedo"],
    athanor: ["four", "fourneau", "fournaise"],
    alambic: ["distillation", "cornue", "cucurbite", "distiller"],
    putrefaction: ["corbeau", "tete de corbeau", "nigredo", "pourriture"],
    albedo: ["blanchiment", "lune", "argent"],
    rubedo: ["rubification", "soleil", "or", "roi"],
    or: ["soleil", "aurum", "metal parfait"],
    argent: ["lune", "argent vif", "metal"],
    antimoine: ["stibium", "loup", "lupus", "regule"],
    vitriol: ["acide sulfurique", "huile de vitriol", "couleuvre"],
    rebis: ["androgyne", "hermaphrodite", "double"],
    alchimie: ["hermetisme", "spagyrie", "chrysopee", "art sacre"],
    transmutation: ["transmuer", "conversion", "projection"],
    flamel: ["nicolas flamel", "livre d'abraham", "hieroglyphes"],
    paracelse: ["paracelsus", "tria prima"],
    basile: ["basile valentin", "douze clefs", "antimoine"],
    fulcanelli: ["mystere des cathedrales", "canseliet", "demeures philosophales"],
    maier: ["michael maier", "atalanta fugiens", "emblemes"],
    ripley: ["georges ripley", "rotulus", "scrowle", "roue"],
    jung: ["psychologie", "archetype", "carl gustav"],
    ouroboros: ["serpent", "queue", "cercle"],
    caducee: ["serpent", "baton", "hermes"],
    mariage: ["noces", "conjonction", "union", "hierogamie"],
    mort: ["putrefaction", "corbeau", "tombeau", "cercueil"],
    eau: ["liqueur", "fontaine", "bain", "mer"],
    feu: ["flamme", "fourneau", "ardeur", "soufre"],
    terre: ["substance", "corps", "matiere", "limon"],
    air: ["souffle", "vent", "esprit"],
    roi: ["soleil", "prince", "or"],
    reine: ["lune", "blanche", "argent"],
  };

  const norm = (s) => s.toLowerCase().replace(/œ/g, "oe").replace(/æ/g, "ae")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  function tokens(text) {
    return norm(text).replace(/[^a-z0-9]+/g, " ").split(/\s+/)
      .filter((w) => w.length >= 3 && !STOP.has(w) && !/^\d+$/.test(w));
  }

  const term = (w) => w.slice(0, TRUNC);

  /* ------------------------------------------------------------ chargement */
  let meta = null, VOCAB = [], TITLES = [];
  const post = {}, pass = {}, loading = {};

  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + " → HTTP " + r.status);
    return r.json();
  }

  async function shard(ch) {
    if (post[ch]) return post[ch];
    if (loading["p" + ch]) return loading["p" + ch];
    loading["p" + ch] = getJSON(`data/search/post/${ch}.json`)
      .then((j) => (post[ch] = j)).catch(() => (post[ch] = {}));
    return loading["p" + ch];
  }

  const shardOf = (t) => (/[a-z0-9]/.test(t[0]) ? t[0] : "_");

  async function bucket(b) {
    if (pass[b]) return pass[b];
    if (loading["b" + b]) return loading["b" + b];
    loading["b" + b] = getJSON(`data/search/pass/${b}.json`)
      .then((j) => (pass[b] = j));
    return loading["b" + b];
  }

  const passage = (pid) => (pass[pid % BUCKETS] || [])[Math.floor(pid / BUCKETS)];

  async function ensurePassages(pids) {
    const need = [...new Set(pids.map((p) => p % BUCKETS))];
    await Promise.all(need.map(bucket));
  }

  async function init() {
    meta = await getJSON("data/search/meta.json");
    VOCAB = Object.keys(meta.df);          // déjà trié par le script Python
    TITLES = meta.docs.map((d) => norm(d.t));
    return meta;
  }

  /* axes d'autorité : auteurs, œuvres, thèmes, époques, pays, matériel,
     techniques, matériaux — chargés seulement quand on s'en sert */
  let AXES = null;
  async function loadAxes() {
    if (AXES) return AXES;
    const j = await getJSON("data/axes.json");
    j.byId = {};
    for (const e of j.entries) j.byId[e.id] = e;
    AXES = j;
    return AXES;
  }

  /* vrai si l'article satisfait la sélection : OU à l'intérieur d'une
     catégorie, ET entre catégories */
  function axisPass(docIdx, ids) {
    if (!AXES) return true;
    const byCat = {};
    for (const id of ids) {
      const e = AXES.byId[id];
      if (!e) continue;
      (byCat[e.cat] = byCat[e.cat] || []).push(e);
    }
    for (const cat of Object.keys(byCat)) {
      if (!byCat[cat].some((e) => e.docs[String(docIdx)] !== undefined)) return false;
    }
    return true;
  }

  /* ------------------------------------------------------------- analyse */
  const FIELD = /^(titre|fichier|section):(.+)$/i;

  function parse(q) {
    const spec = {
      terms: [],        /* {raw, w, required, excluded, prefix, fuzzy, field} */
      phrases: [],      /* {text, required, excluded} */
      filters: {},      /* titre / fichier / section */
      errors: [],
    };
    const rx = /"[^"]*"|[()]|\S+/g;
    let m, orPending = false;
    while ((m = rx.exec(q))) {
      let w = m[0];
      if (w === "(" || w === ")") continue;
      if (w === "|" || w === "OR" || w === "ou") { orPending = true; continue; }
      let neg = false, req = false;
      while (w.length > 1 && (w[0] === "-" || w[0] === "+")) {
        if (w[0] === "-") neg = true; else req = true;
        w = w.slice(1);
      }
      if (w === "") continue;
      if (w[0] === '"') {
        const text = w.replace(/^"|"$/g, "").trim();
        if (!text) continue;
        (neg ? spec.excludedPhrases ||= [] : spec.phrases).push(text);
        if (!neg && req) spec.requiredPhrase = text;
        continue;
      }
      const fm = w.match(FIELD);
      if (fm) {
        spec.filters[fm[1].toLowerCase()] =
          (spec.filters[fm[1].toLowerCase()] || []).concat([fm[2]]);
        continue;
      }
      let prefix = false, fuzzy = false;
      if (w.endsWith("*") && w.length > 2) { prefix = true; w = w.replace(/\*+$/, ""); }
      if (w.includes("~")) { fuzzy = true; w = w.replace(/~.*$/, ""); }
      const toks = tokens(w);
      for (const t of toks) {
        spec.terms.push({
          raw: w, t: term(t), w: orPending ? 0.55 : 1,
          required: req && !neg, excluded: neg, prefix, fuzzy,
        });
      }
      orPending = false;
    }
    return spec;
  }

  function vocabPrefix(p, limit = 40) {
    let lo = 0, hi = VOCAB.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (VOCAB[mid] < p) lo = mid + 1; else hi = mid;
    }
    const out = [];
    for (let i = lo; i < VOCAB.length && out.length < limit; i++) {
      if (!VOCAB[i].startsWith(p)) break;
      out.push(VOCAB[i]);
    }
    return out;
  }

  function lev1(a, b) {
    if (Math.abs(a.length - b.length) > 1) return false;
    let i = 0, j = 0, diff = 0;
    while (i < a.length && j < b.length) {
      if (a[i] === b[j]) { i++; j++; continue; }
      if (++diff > 1) return false;
      if (a.length > b.length) i++;
      else if (b.length > a.length) j++;
      else { i++; j++; }
    }
    return true;
  }

  function fuzzyMatches(t, limit = 6) {
    const out = [];
    const pre = t.slice(0, Math.max(2, Math.min(4, t.length - 1)));
    for (const v of vocabPrefix(pre, 400)) {
      if (lev1(t, v)) out.push(v);
      if (out.length >= limit) break;
    }
    return out;
  }

  /* --------------------------------------------------------------- requête */
  /* premier passage d'un article : sert à donner un extrait même quand la
     requête ne porte que sur un champ (titre:, section:, fichier:) */
  let firstPid = null;
  function docFirstPassage(id) {
    if (!firstPid) {
      firstPid = {};
      meta.pdoc.forEach((d, pid) => { if (firstPid[d] === undefined) firstPid[d] = pid; });
    }
    return firstPid[id];
  }

  async function search(query, opts = {}) {
    const t0 = performance.now();
    const spec = parse(query);
    if (!spec.terms.length && !spec.phrases.length && !Object.keys(spec.filters).length) {
      return { docs: [], spec, ms: 0, total: 0, loaded: 0 };
    }

    /* requête purement « champ » : aucun terme à classer, on renvoie les
       articles qui passent le filtre, dans l'ordre alphabétique */
    if (!spec.terms.length && !spec.phrases.length) {
      const docs0 = [];
      meta.docs.forEach((d, i) => {
        if (!matchFilters(d, spec.filters)) return;
        docs0.push({ doc: i, score: 1, hits: 0, best: docFirstPassage(i),
          bestScore: 0, pids: [docFirstPassage(i)].filter((x) => x !== undefined),
          top: [docFirstPassage(i)].filter((x) => x !== undefined) });
      });
      docs0.sort((a, b) => norm(meta.docs[a.doc].t)
        .localeCompare(norm(meta.docs[b.doc].t), "fr"));
      return { docs: docs0, spec, qterms: [], ms: Math.round(performance.now() - t0),
        total: docs0.length, loaded: Object.keys(post).length, fieldOnly: true };
    }

    const qterms = [];      /* {t, w, required, excluded} */
    for (const s of spec.terms) {
      let list;
      if (s.prefix) list = vocabPrefix(s.t, 30).map((t) => ({ t, w: 0.9 }));
      else {
        list = meta.df[s.t] !== undefined ? [{ t: s.t, w: 1 }] : [];
        /* mot plus court que la troncature : on cherche aussi ses
           prolongements (« mercur » doit trouver « mercure ») */
        if (!s.fuzzy && s.t.length < TRUNC && (meta.df[s.t] || 0) < 200) {
          for (const v of vocabPrefix(s.t, 12))
            if (v !== s.t) list.push({ t: v, w: 0.7 });
        }
        if (s.fuzzy) {
          for (const v of fuzzyMatches(s.t))
            if (!list.some((x) => x.t === v)) list.push({ t: v, w: 0.55 });
        }
        if (!list.length && s.t.length >= 5) {
          for (const v of fuzzyMatches(s.t)) list.push({ t: v, w: 0.45 });
        }
      }
      if (!list.length && !s.excluded) spec.errors.push(s.raw);
      for (const l of list) {
        qterms.push({ ...l, w: l.w * s.w, required: s.required,
          excluded: s.excluded, field: s.field });
      }
    }
    /* mode question : élargissement thématique */
    if (opts.thesaurus) {
      const nq = " " + norm(query) + " ";
      for (const [base, syns] of Object.entries(THES)) {
        if (!nq.includes(" " + base)) continue;
        for (const s of syns) {
          for (const w of tokens(s)) {
            const t = term(w);
            if (meta.df[t] !== undefined && !qterms.some((x) => x.t === t)) {
              qterms.push({ t, w: 0.3, required: false, excluded: false });
            }
          }
        }
      }
    }
    /* phrases : au minimum tous les termes présents, adjacence vérifiée après */
    for (const ph of [...spec.phrases, ...(spec.excludedPhrases || [])]) {
      for (const w of tokens(ph)) {
        qterms.push({ t: term(w), w: 0.7, required: true,
          excluded: (spec.excludedPhrases || []).includes(ph) });
      }
    }

    if (!qterms.length) return { docs: [], spec, ms: 0, total: 0, loaded: 0 };

    await Promise.all([...new Set(qterms.map((x) => shardOf(x.t)))].map(shard));

    const scores = new Map(), hitTerms = new Map();
    const reqSets = [], exclDocs = new Set();
    const N = meta.n, avg = meta.avgdl;

    for (const qt of qterms) {
      const p = post[shardOf(qt.t)];
      const list = p && p[qt.t];
      if (!list) { if (qt.required) reqSets.push(new Set()); continue; }
      const df = meta.df[qt.t] || list.length / 2;
      const idf = Math.log(1 + (N - df + 0.5) / (df + 0.5));
      const set = qt.required ? new Set() : null;
      for (let i = 0; i < list.length; i += 2) {
        const pid = list[i], tf = list[i + 1];
        const dl = meta.dl[pid] || avg;
        const s = qt.w * idf * tf * (K1 + 1) /
          (tf + K1 * (1 - B + B * dl / avg));
        if (qt.excluded) {
          exclDocs.add(meta.pdoc[pid]);
          continue;
        }
        scores.set(pid, (scores.get(pid) || 0) + s);
        if (set) set.add(pid);
        if (hitTerms.get(pid) === undefined) hitTerms.set(pid, []);
        hitTerms.get(pid).push(qt.t);
      }
      if (set) reqSets.push(set);
    }

    /* les termes obligatoires doivent figurer dans le même passage */
    if (reqSets.length > 1) {
      reqSets.sort((a, b) => a.size - b.size);
      for (const pid of [...scores.keys()]) {
        if (!reqSets.every((s) => s.has(pid))) scores.delete(pid);
      }
    }

    /* un titre qui contient le terme suffit à retenir l'article, même si son
       corps ne le répète pas (planches, tables, pages de titre) */
    const titleHits = new Map();
    for (const qt of qterms) {
      if (qt.excluded || qt.t.length < 4) continue;
      const df = meta.df[qt.t] || 1;
      const idf = Math.log(1 + (N - df + 0.5) / (df + 0.5));
      const w = Math.min(12, idf * 2.2);
      for (let i = 0; i < TITLES.length; i++) {
        if (TITLES[i].includes(qt.t))
          titleHits.set(i, Math.max(titleHits.get(i) || 0, w));
      }
    }

    /* agrégation par article */
    const docs = new Map();
    for (const [pid, s] of scores) {
      const id = meta.pdoc[pid];
      const cur = docs.get(id) ||
        { doc: id, score: 0, best: pid, bestScore: 0, hits: 0, pids: [] };
      cur.hits++;
      cur.pids.push(pid);
      if (s > cur.bestScore) { cur.bestScore = s; cur.best = pid; }
      docs.set(id, cur);
    }
    for (const [id, sc] of titleHits) {
      if (docs.has(id)) continue;
      const pid = docFirstPassage(id);
      docs.set(id, { doc: id, score: sc, best: pid, bestScore: 0, hits: 0,
        pids: pid === undefined ? [] : [pid],
        top: pid === undefined ? [] : [pid], titleOnly: sc });
    }

    for (const v of docs.values()) {
      if (v.titleOnly) { v.score = v.titleOnly; continue; }
      v.score = v.bestScore * (1 + 0.10 * Math.log2(v.hits + 1));
      v.pids.sort((a, b) => (scores.get(b) || 0) - (scores.get(a) || 0));
      v.top = v.pids.slice(0, 4);
    }

    /* filtres */
    for (const [id, v] of docs) {
      const d = meta.docs[id];
      if (exclDocs.has(id)) { docs.delete(id); continue; }
      if (!matchFilters(d, spec.filters)) { docs.delete(id); continue; }
      if (opts.sections && opts.sections.size && !opts.sections.has(d.sec)) {
        docs.delete(id); continue;
      }
      if (opts.type && opts.type !== "tout" && d.type !== opts.type) {
        docs.delete(id); continue;
      }
      if (opts.images && !d.img) { docs.delete(id); continue; }
      /* prime au titre */
      let bonus = 0;
      for (const qt of qterms) {
        if (qt.excluded) continue;
        if (TITLES[id].includes(qt.t)) bonus += 1.6;
      }
      v.score += bonus;
    }

    /* phrase exacte : vérification sur les passages des meilleurs articles */
    let ranked = [...docs.values()].sort((a, b) => b.score - a.score);
    const phrase = spec.phrases[0];
    if (phrase) {
      const nph = norm(phrase).replace(/\s+/g, " ").trim();
      const probe = ranked.slice(0, 40);
      const pids = probe.flatMap((v) => v.top);
      if (pids.length) {
        await ensurePassages(pids);
        for (const v of probe) {
          const okP = v.top.some((pid) => {
            const p = passage(pid);
            return p && norm(p.t).replace(/\s+/g, " ").includes(nph);
          });
          if (okP) v.score *= 1.5; else v.score *= 0.35;
        }
        ranked = [...docs.values()].sort((a, b) => b.score - a.score);
      }
    }

    return {
      docs: ranked, spec, qterms,
      ms: Math.round(performance.now() - t0),
      total: ranked.length,
      loaded: Object.keys(post).length,
    };
  }

  function matchFilters(d, f) {
    for (const [k, vals] of Object.entries(f || {})) {
      for (const v of vals) {
        const nv = norm(v).replace(/\s+/g, " ");
        if (k === "titre" && !norm(d.t).includes(nv)) return false;
        if (k === "fichier" && !norm(d.k).includes(nv.replace(/\s+/g, "_"))) return false;
        if (k === "section") {
          const lab = norm(meta.sections[d.sec] || "");
          if (d.sec.toLowerCase() !== nv && !lab.includes(nv)) return false;
        }
      }
    }
    return true;
  }

  /* ------------------------------------------------------- mise en avant */
  const ACC = { a: "[aàâä]", e: "[eéèêë]", i: "[iîï]", o: "[oôö]", u: "[uùûü]",
    c: "[cç]", y: "[yÿ]", n: "[nñ]", s: "[sß]" };

  function rxWord(w) {
    const parts = norm(w).split("").map((ch) => ACC[ch] || ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    return new RegExp("(" + parts.join("") + "[a-zà-ÿ]*)", "gi");
  }

  function esc(s) {
    return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function highlight(text, words) {
    let out = esc(text);
    const seen = new Set();
    for (const w of words) {
      const key = norm(w).slice(0, 5);
      if (seen.has(key) || key.length < 3) continue;
      seen.add(key);
      try { out = out.replace(rxWord(w), "<mark>$1</mark>"); } catch (e) { /* ignore */ }
    }
    return out;
  }

  function snippet(text, words, len = 340) {
    const low = norm(text);
    let pos = -1;
    for (const w of words) {
      const k = low.indexOf(norm(w).slice(0, 5));
      if (k >= 0 && (pos < 0 || k < pos)) pos = k;
    }
    if (pos < 0) pos = 0;
    const start = Math.max(0, pos - Math.floor(len / 3));
    let s = text.slice(start, start + len);
    if (start > 0) s = "… " + s;
    if (start + len < text.length) s += " …";
    return s;
  }

  /* résultat « sans requête » : tous les articles, pour ne filtrer que par
     les axes et les facettes */
  function allDocs() {
    const docs = meta.docs.map((d, i) => {
      const pid = docFirstPassage(i);
      return { doc: i, score: 1, hits: 0, bestScore: 0,
        pids: pid === undefined ? [] : [pid],
        top: pid === undefined ? [] : [pid] };
    });
    return { docs, spec: { terms: [], phrases: [], filters: {}, errors: [] },
      qterms: [], ms: 0, total: docs.length, loaded: Object.keys(post).length };
  }

  return {
    init, search, parse, passage, ensurePassages, snippet, highlight, esc,
    tokens, norm, term, THES, STOP, loadAxes, axisPass, allDocs,
    get axes() { return AXES; },
    get meta() { return meta; },
    get vocab() { return VOCAB; },
    sectionName: (id) => (meta.sections[id] || id),
    version: 3,
  };
})();
