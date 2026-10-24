/* Liseuse des pages d'Hervé Delboy.
 * La page de l'auteur reste telle quelle ; la barre ajoute : page précédente
 * et suivante dans l'ordre du plan, taille, police, colonne, modes (original,
 * noir et blanc, nuit), loupe et visionneuse des planches, sorties PDF et EPUB.
 * Réglages gardés dans le navigateur (localStorage).
 */
(function () {
  "use strict";
  var me = document.currentScript || document.querySelector('script[src$="barre.js"]');
  var BASE = me ? me.getAttribute("src").replace(/barre\.js$/, "") : "../";
  var KEY = "dlb.liseuse.2";
  var S = { zoom: 1, mode: "nuit", font: "serif", col: false, loupe: false };
  try { Object.assign(S, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} }

  /* téléphone : les pages de l'auteur n'ont pas de viewport ; sans lui, elles
     sont mises en page sur 980 px puis réduites, et la barre devient illisible */
  if (!document.querySelector('meta[name="viewport"]') && matchMedia("(pointer: coarse)").matches &&
      Math.min(screen.width, screen.height) < 820) {
    var mv = document.createElement("meta");
    mv.name = "viewport"; mv.content = "width=device-width, initial-scale=1";
    document.head.appendChild(mv);
  }

  var path = location.pathname.split("/").pop() || "index.html";
  var inOrig = /\/original\/[^/]+$/.test(location.pathname);
  var atRoot = !inOrig && /^(index\.html)?$/.test(location.pathname.split("/").pop());
  var SLUG = inOrig ? path.replace(/\.html?$/, "") : atRoot ? "intro-alchimie" : null;

  var I = {
    prev: '<path d="M15 5l-7 7 7 7"/>', next: '<path d="M9 5l7 7-7 7"/>',
    minus: '<path d="M5 12h14"/>', plus: '<path d="M12 5v14M5 12h14"/>',
    loupe: '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>',
    col: '<path d="M7 4v16M17 4v16"/>',
    font: '<path d="M5 19l5.5-14h1L17 19M7.5 13.5h7"/>',
    mode: '<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor" stroke="none"/>',
    down: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    pdf: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 13h6M9 17h4"/>',
    book: '<path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v16H5.5A1.5 1.5 0 0 1 4 18.5zM20 5.5A1.5 1.5 0 0 0 18.5 4H13v16h5.5a1.5 1.5 0 0 0 1.5-1.5z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    list: '<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.5M4.5 12h.5M4.5 18h.5"/>',
    info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.6v.2"/>',
    say: '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
    mark: '<path d="M14.5 4.5l5 5L10 19H5v-5z"/><path d="M12 7l5 5M4 21h16"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.7 5.4 3.7 8.5s-1.2 5.9-3.7 8.5M12 3.5C9.5 6.1 8.3 8.9 8.3 12s1.2 5.9 3.7 8.5"/>'
  };
  function ic(n) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + I[n] + "</svg>"; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ------------------------------------------------ la page dans un cadre */
  var bar = document.querySelector(".replica-note");
  var wrap = document.createElement("div");
  wrap.id = "dlb-page";
  var kids = [].slice.call(document.body.childNodes);
  kids.forEach(function (n) { if (n !== bar && !(n.tagName === "SCRIPT")) wrap.appendChild(n); });
  document.body.appendChild(wrap);
  if (bar) document.body.insertBefore(bar, wrap);
  else { bar = document.createElement("div"); bar.className = "replica-note"; document.body.insertBefore(bar, wrap); }

  bar.className = "replica-note dlb-bar";
  bar.setAttribute("role", "toolbar");
  bar.innerHTML =
    '<a class="dlb-home" href="' + BASE + 'index.html">Hervé Delboy <span>alchimie</span></a>' +
    '<a class="dlb-som" href="' + BASE + 'sommaire.html" title="Sommaire, dans l\'ordre du plan de l\'auteur">' + ic("list") + "<span>Sommaire</span></a>" +
    '<a class="dlb-som dlb-info" href="' + BASE + 'notice.html" title="Le projet, la provenance, les droits">' + ic("info") + "<span>Info</span></a>" +
    '<form class="dlb-search" role="search" action="' + BASE + 'recherche.html">' + ic("loupe") +
      '<input type="search" name="q" placeholder="Rechercher dans le site…" aria-label="Rechercher dans le site (/)" autocomplete="off"></form>' +
    '<span class="dlb-where"><span class="dlb-sec"></span></span>' +
    '<span class="dlb-tools">' +
      '<a class="dlb-b" id="dlb-prev" title="Page précédente (←)">' + ic("prev") + "</a>" +
      '<a class="dlb-b" id="dlb-next" title="Page suivante (→)">' + ic("next") + "</a>" +
      '<span class="dlb-sep"></span>' +
      '<button class="dlb-b" id="dlb-minus" title="Réduire (−)">' + ic("minus") + "</button>" +
      '<button class="dlb-z" id="dlb-zoom" title="Taille d\'origine (0)">100 %</button>' +
      '<button class="dlb-b" id="dlb-plus" title="Agrandir (+)">' + ic("plus") + "</button>" +
      '<span class="dlb-sep"></span>' +
      '<button class="dlb-b dlb-lb" id="dlb-font" title="Police : originale, sérif, sans sérif">' + ic("font") + '<span class="dlb-lab"></span></button>' +
      '<button class="dlb-b dlb-lb" id="dlb-mode" title="Affichage : original, noir et blanc, nuit">' + ic("mode") + '<span class="dlb-lab"></span></button>' +
      '<button class="dlb-b" id="dlb-col" title="Colonne de lecture">' + ic("col") + "</button>" +
      '<button class="dlb-b" id="dlb-loupe" title="Loupe sur les planches (L)">' + ic("loupe") + "</button>" +
      '<button class="dlb-b" id="dlb-say" title="Lire à voix haute (depuis le passage sélectionné, ou depuis le haut de l\'écran)">' + ic("say") + "</button>" +
      '<button class="dlb-b dlb-lb" id="dlb-notesb" title="Mes surlignages et notes">' + ic("mark") + '<span class="dlb-cnt"></span></button>' +
      '<a class="dlb-b dlb-lb" id="dlb-en" target="_blank" rel="noopener" title="Lire cette page en anglais (Google Traduction, nouvel onglet)">' + ic("globe") + '<span class="dlb-lab">EN</span></a>' +
      '<span class="dlb-sep"></span>' +
      '<span class="dlb-outs">' +
        '<button class="dlb-x" data-out="pdf" title="Imprimer ou enregistrer la page en PDF">' + ic("pdf") + '<span class="dlb-xl">PDF</span></button>' +
        '<button class="dlb-x" data-out="epub" title="Télécharger la page en EPUB, avec ses images">' + ic("book") + '<span class="dlb-xl">EPUB</span></button>' +
        '<a class="dlb-x dlb-xs" id="dlb-secpdf" hidden>' + ic("down") + '<span class="dlb-xl">Section</span></a>' +
      "</span>" +
      '<span class="dlb-menuw"><button class="dlb-b" id="dlb-out" title="Plus">' + ic("menu") + "</button>" +
      '<span class="dlb-menu" id="dlb-menu" hidden>' +
        '<a id="dlb-en2" class="dlb-en2" target="_blank" rel="noopener">Lire en anglais</a>' +
        '<a href="' + BASE + 'notice.html">Notice</a>' +
        '<a href="' + BASE + 'lacunes.html">Pages perdues</a>' +
      "</span></span>" +
    "</span>";

  function $(id) { return document.getElementById(id); }
  /* page de recherche : la requête reste dans le champ de la barre */
  (function () {
    var q = new URLSearchParams(location.search).get("q");
    var f = bar.querySelector(".dlb-search input");
    if (q && f && /recherche\.html$/.test(location.pathname)) f.value = q;
  })();
  var root = document.documentElement;
  $("dlb-en").href = $("dlb-en2").href =
    "https://translate.google.com/translate?sl=fr&tl=en&u=" + encodeURIComponent(location.href.split("#")[0]);

  function apply() {
    wrap.style.zoom = S.zoom;
    $("dlb-zoom").textContent = Math.round(S.zoom * 100) + " %";
    root.classList.toggle("dlb-nb", S.mode === "nb");
    root.classList.toggle("dlb-nuit", S.mode === "nuit");
    root.classList.toggle("dlb-serif", S.font === "serif");
    root.classList.toggle("dlb-sans", S.font === "sans");
    root.classList.toggle("dlb-colonne", !!S.col);
    root.classList.toggle("dlb-loupe-on", !!S.loupe);
    $("dlb-col").classList.toggle("on", !!S.col);
    $("dlb-loupe").classList.toggle("on", !!S.loupe);
    $("dlb-mode").classList.toggle("on", S.mode !== "orig");
    $("dlb-font").classList.toggle("on", S.font !== "orig");
    $("dlb-mode").title = "Affichage : " + { orig: "original", nb: "noir et blanc", nuit: "nuit" }[S.mode];
    $("dlb-font").title = "Police : " + { orig: "originale", serif: "sérif", sans: "sans sérif" }[S.font];
    $("dlb-mode").querySelector(".dlb-lab").textContent = { orig: "Original", nb: "N & B", nuit: "Nuit" }[S.mode];
    $("dlb-font").querySelector(".dlb-lab").textContent = { orig: "Originale", serif: "Sérif", sans: "Sans" }[S.font];
    ["dlb-font", "dlb-mode", "dlb-col", "dlb-loupe"].forEach(function (id) {
      $(id).setAttribute("aria-pressed", $(id).classList.contains("on") ? "true" : "false");
    });
    save();
  }
  function zoom(d) { S.zoom = Math.min(2.5, Math.max(0.6, Math.round((S.zoom + d) * 10) / 10)); apply(); }
  $("dlb-minus").onclick = function () { zoom(-0.1); };
  $("dlb-plus").onclick = function () { zoom(0.1); };
  $("dlb-zoom").onclick = function () { S.zoom = 1; apply(); };
  $("dlb-col").onclick = function () { S.col = !S.col; apply(); };
  $("dlb-loupe").onclick = function () { S.loupe = !S.loupe; apply(); };
  $("dlb-mode").onclick = function () { S.mode = { orig: "nb", nb: "nuit", nuit: "orig" }[S.mode] || "orig"; apply(); };
  $("dlb-font").onclick = function () { S.font = { orig: "serif", serif: "sans", sans: "orig" }[S.font] || "orig"; apply(); };
  $("dlb-out").onclick = function (e) { e.stopPropagation(); $("dlb-menu").hidden = !$("dlb-menu").hidden; };
  document.addEventListener("click", function () { $("dlb-menu").hidden = true; });
  bar.addEventListener("click", function (e) {
    var b = e.target.closest("[data-out]");
    if (!b) return;
    if (b.dataset.out === "pdf") window.print();
    if (b.dataset.out === "epub") epub(b);
  });
  apply();

  /* ------------------------------------------------ ordre du plan */
  fetch(BASE + "data/nav.json").then(function (r) { return r.json(); }).then(function (N) {
    var p = SLUG && N.pages[SLUG];
    if (!p) { $("dlb-prev").classList.add("off"); $("dlb-next").classList.add("off"); return; }
    var sec = N.sections[p[1]];
    document.querySelector(".dlb-sec").innerHTML = '<a href="' + BASE + "sections/" + p[1] + '.html">' + esc(sec[0]) + "</a>";
    function link(id, s) {
      var a = $(id);
      if (s && N.pages[s]) { a.href = BASE + "original/" + s + ".html"; a.title += " — " + N.pages[s][0]; }
      else a.classList.add("off");
    }
    link("dlb-prev", p[2]); link("dlb-next", p[3]);
    if (sec[1]) { var sp = $("dlb-secpdf"); sp.hidden = false; sp.href = BASE + sec[1]; sp.title = "PDF de la section, " + sec[2]; }
    document.title = document.title || p[0];
  }).catch(function () {});

  /* ------------------------------------------------ feuilleter (écrans tactiles) */
  function scrollsX(el) {
    for (; el && el !== wrap; el = el.parentElement)
      if (el.scrollWidth > el.clientWidth + 2 && /auto|scroll/.test(getComputedStyle(el).overflowX)) return true;
    return false;
  }
  function settle() { wrap.style.transform = ""; wrap.style.opacity = ""; }
  var sw = null;
  wrap.addEventListener("touchstart", function (e) {
    sw = null;
    if (e.touches.length !== 1 || viewer.open || scrollsX(e.target)) return;
    if (window.visualViewport && visualViewport.scale > 1.05) return;  /* page agrandie au doigt */
    sw = { x: e.touches[0].clientX, y: e.touches[0].clientY, dx: 0, on: false };
  }, { passive: true });
  wrap.addEventListener("touchmove", function (e) {
    if (!sw) return;
    var dx = e.touches[0].clientX - sw.x, dy = e.touches[0].clientY - sw.y;
    if (!sw.on) {
      if (Math.abs(dy) > 12 && Math.abs(dy) > Math.abs(dx)) { sw = null; return; }
      if (Math.abs(dx) < 12) return;
      sw.on = true;
    }
    sw.dx = $(dx < 0 ? "dlb-next" : "dlb-prev").href ? dx : dx / 4;  /* rien de ce côté : résistance */
    wrap.style.transition = "none";
    wrap.style.transform = "translateX(" + sw.dx + "px)";
    wrap.style.opacity = 1 - Math.min(Math.abs(sw.dx) / innerWidth, 0.5);
  }, { passive: true });
  wrap.addEventListener("touchend", function () {
    if (!sw || !sw.on) { sw = null; return; }
    var t = $(sw.dx < 0 ? "dlb-next" : "dlb-prev"), dir = sw.dx < 0 ? -1 : 1;
    wrap.style.transition = "transform .22s ease, opacity .22s ease";
    if (t.href && Math.abs(sw.dx) > innerWidth * 0.22) {
      wrap.style.transform = "translateX(" + dir * innerWidth + "px)";
      wrap.style.opacity = 0;
      try { sessionStorage.setItem("dlb.flip", dir < 0 ? "next" : "prev"); } catch (e) {}
      setTimeout(function () { location.href = t.href; }, 200);
    } else settle();
    sw = null;
  });
  window.addEventListener("pageshow", function () { wrap.style.transition = "none"; settle(); });
  try {
    var flip = sessionStorage.getItem("dlb.flip");
    sessionStorage.removeItem("dlb.flip");
    if (flip) {
      wrap.style.transform = "translateX(" + (flip === "next" ? 48 : -48) + "px)";
      wrap.style.opacity = 0;
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        wrap.style.transition = "transform .26s ease, opacity .26s ease"; settle();
      }); });
    }
  } catch (e) {}

  /* ------------------------------------------------ clavier */
  document.addEventListener("keydown", function (e) {
    if (e.target.closest && e.target.closest("input,textarea,select")) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (viewer.open) return;
    if (e.key === "+" || e.key === "=") zoom(0.1);
    else if (e.key === "-") zoom(-0.1);
    else if (e.key === "0") { S.zoom = 1; apply(); }
    else if (e.key === "l" || e.key === "L") { S.loupe = !S.loupe; apply(); }
    else if (e.key === "/") { e.preventDefault(); bar.querySelector(".dlb-search input").focus(); }
    else if (e.key === "ArrowLeft" && $("dlb-prev").href) location.href = $("dlb-prev").href;
    else if (e.key === "ArrowRight" && $("dlb-next").href) location.href = $("dlb-next").href;
  });

  /* ------------------------------------------------ loupe */
  var lens = document.createElement("div");
  lens.id = "dlb-lens";
  document.body.appendChild(lens);
  var LZ = 2.6, LR = 120;
  function big(img) { return img.naturalWidth >= 120 && img.naturalHeight >= 120; }
  document.addEventListener("mousemove", function (e) {
    var img = S.loupe && e.target.tagName === "IMG" && big(e.target) ? e.target : null;
    if (!img) { lens.style.display = "none"; return; }
    var r = img.getBoundingClientRect();
    var x = e.clientX - r.left, y = e.clientY - r.top;
    lens.style.display = "block";
    lens.style.left = e.clientX - LR + "px";
    lens.style.top = e.clientY - LR + "px";
    lens.style.backgroundImage = 'url("' + img.currentSrc + '")';
    lens.style.backgroundSize = r.width * LZ + "px " + r.height * LZ + "px";
    lens.style.backgroundPosition = (LR - x * LZ) + "px " + (LR - y * LZ) + "px";
  });

  /* ------------------------------------------------ visionneuse des planches */
  var viewer = { open: false };
  var ov = document.createElement("div");
  ov.id = "dlb-view";
  ov.innerHTML = '<img alt=""><span class="dlb-vinfo"></span>' +
    '<button class="dlb-vx" title="Fermer (Échap)">×</button>';
  document.body.appendChild(ov);
  var vimg = ov.querySelector("img"), vinfo = ov.querySelector(".dlb-vinfo");
  var plates = [], vi = 0, vs = 1, vx = 0, vy = 0;
  function show(i) {
    vi = (i + plates.length) % plates.length;
    vimg.src = plates[vi].currentSrc; vs = 1; vx = vy = 0; tf();
    vinfo.textContent = (vi + 1) + " / " + plates.length + " · " + decodeURIComponent(plates[vi].currentSrc.split("/").pop());
  }
  function tf() { vimg.style.transform = "translate(" + vx + "px," + vy + "px) scale(" + vs + ")"; }
  wrap.addEventListener("click", function (e) {
    var img = e.target.tagName === "IMG" ? e.target : null;
    if (!img || !big(img) || e.target.closest("a")) return;
    plates = [].filter.call(wrap.querySelectorAll("img"), big);
    viewer.open = true; ov.classList.add("open"); show(plates.indexOf(img));
  });
  function close() { viewer.open = false; ov.classList.remove("open"); }
  ov.querySelector(".dlb-vx").onclick = close;
  ov.addEventListener("click", function (e) { if (e.target === ov) close(); });
  ov.addEventListener("wheel", function (e) { e.preventDefault(); vs = Math.min(8, Math.max(1, vs * (e.deltaY < 0 ? 1.15 : 1 / 1.15))); if (vs === 1) vx = vy = 0; tf(); }, { passive: false });
  var drag = null;
  vimg.addEventListener("mousedown", function (e) { e.preventDefault(); drag = [e.clientX - vx, e.clientY - vy]; });
  window.addEventListener("mousemove", function (e) { if (drag) { vx = e.clientX - drag[0]; vy = e.clientY - drag[1]; tf(); } });
  window.addEventListener("mouseup", function () { drag = null; });
  vimg.addEventListener("dblclick", function () { vs = vs > 1 ? 1 : 2.5; vx = vy = 0; tf(); });
  document.addEventListener("keydown", function (e) {
    if (!viewer.open) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") show(vi + 1);
    else if (e.key === "ArrowLeft") show(vi - 1);
    else if (e.key === "+" || e.key === "=") { vs = Math.min(8, vs * 1.25); tf(); }
    else if (e.key === "-") { vs = Math.max(1, vs / 1.25); if (vs === 1) vx = vy = 0; tf(); }
  });

  /* ------------------------------------------------ passage cité (#passage=…) */
  var m = location.hash.match(/^#passage=(.+)$/);
  if (m) {
    var want = decodeURIComponent(m[1]).replace(/\s+/g, " ").trim().toLowerCase();
    var find = function () {
      var w = document.createTreeWalker(wrap, NodeFilter.SHOW_TEXT, null), n, buf = "", map = [];
      while ((n = w.nextNode())) {
        if (n.parentNode.closest && n.parentNode.closest("script,style")) continue;
        var s = n.nodeValue;
        for (var i = 0; i < s.length; i++) {
          var c = /\s/.test(s[i]) ? " " : s[i].toLowerCase();
          if (c === " " && buf.slice(-1) === " ") continue;
          buf += c; map.push([n, i]);
        }
      }
      var k = buf.indexOf(want);
      if (k < 0) return;
      var a = map[k], z = map[Math.min(k + want.length - 1, map.length - 1)];
      var r = document.createRange();
      r.setStart(a[0], a[1]); r.setEnd(z[0], z[1] + 1);
      a[0].parentNode.scrollIntoView({ block: "center" });
      if (window.CSS && CSS.highlights && window.Highlight) CSS.highlights.set("passage", new Highlight(r));
      else a[0].parentNode.style.background = "#fff1a8";
    };
    if (document.readyState === "complete") find(); else window.addEventListener("load", find);
  }

  /* ------------------------------------------------ texte de la page, à plat */
  /* Une seule chaîne (espaces réduits) et, pour chaque caractère, son nœud et
     sa position : sert à la lecture à voix haute et aux surlignages, qu'on
     dessine avec l'API CSS Highlight sans toucher au markup de l'auteur. */
  var TM = null;
  function textMap() {
    if (TM) return TM;
    var w = document.createTreeWalker(wrap, NodeFilter.SHOW_TEXT, null), n, buf = [], len = 0, map = [], start = new Map(), last = " ";
    while ((n = w.nextNode())) {
      if (n.parentNode.closest && n.parentNode.closest("script,style")) continue;
      var s = n.nodeValue;
      start.set(n, len);
      for (var i = 0; i < s.length; i++) {
        var c = /\s/.test(s[i]) ? " " : s[i];
        if (c === " " && last === " ") continue;
        buf.push(c); map.push([n, i]); len++; last = c;
      }
    }
    TM = { buf: buf.join(""), map: map, start: start };
    return TM;
  }
  function locate(r) {  /* position approchée du début d'une sélection */
    var T = textMap(), n = r.startContainer;
    if (T.start.has(n)) return T.start.get(n) + r.startOffset;
    var w = document.createTreeWalker(n, NodeFilter.SHOW_TEXT, null), t = w.nextNode();
    return t && T.start.has(t) ? T.start.get(t) : 0;
  }
  function rangeOf(a, b) {
    var T = textMap(), s = T.map[a], e = T.map[Math.max(a, b - 1)];
    var r = document.createRange();
    r.setStart(s[0], s[1]); r.setEnd(e[0], e[1] + 1);
    return r;
  }
  var HL = !!(window.CSS && CSS.highlights && window.Highlight);

  /* ------------------------------------------------ lecture à voix haute */
  var TTS = { on: false, chunks: [], voice: null };
  if (!("speechSynthesis" in window)) $("dlb-say").hidden = true;
  function frVoice() {
    var v = speechSynthesis.getVoices().filter(function (x) { return /^fr/i.test(x.lang); });
    return v.filter(function (x) { return /natural|online|google|amélie|thomas|audrey/i.test(x.name); })[0] || v[0] || null;
  }
  function firstVisible() {
    var T = textMap(), top = bar.getBoundingClientRect().bottom + 4, seen = null;
    for (var i = 0; i < T.map.length; i += 40) {
      var p = T.map[i][0].parentElement;
      if (p === seen) continue;
      seen = p;
      if (p.getBoundingClientRect().bottom > top) return i;
    }
    return 0;
  }
  function sayStop() {
    TTS.on = false;
    try { speechSynthesis.cancel(); } catch (e) {}
    if (HL) CSS.highlights.delete("dlb-lecture");
    $("dlb-say").classList.remove("on"); $("dlb-say").setAttribute("aria-pressed", "false");
  }
  function sayFrom(at) {
    sayStop();
    var T = textMap(), re = /[^.!?;:…]+[.!?;:…»"”)]*\s*/g, m, cur = null;
    TTS.chunks = [];
    re.lastIndex = at;
    while ((m = re.exec(T.buf))) {  /* phrases, regroupées jusqu'à ~220 caractères */
      var a = m.index, b = m.index + m[0].length;
      if (cur && b - cur[0] < 220) cur[1] = b; else { if (cur) TTS.chunks.push(cur); cur = [a, b]; }
    }
    if (cur) TTS.chunks.push(cur);
    if (!TTS.chunks.length) return;
    TTS.voice = TTS.voice || frVoice();
    TTS.on = true;
    $("dlb-say").classList.add("on"); $("dlb-say").setAttribute("aria-pressed", "true");
    sayNext(0);
  }
  function sayNext(i) {
    if (!TTS.on) return;
    if (i >= TTS.chunks.length) { sayStop(); return; }
    var c = TTS.chunks[i], T = textMap();
    var u = new SpeechSynthesisUtterance(T.buf.slice(c[0], c[1]));
    u.lang = "fr-FR"; if (TTS.voice) u.voice = TTS.voice;
    u.onend = function () { sayNext(i + 1); };
    u.onerror = function (e) { if (e.error !== "interrupted" && e.error !== "canceled") sayStop(); };
    if (HL) {
      var r = rangeOf(c[0], c[1]);
      CSS.highlights.set("dlb-lecture", new Highlight(r));
      var rb = r.getBoundingClientRect();
      if (rb.top < bar.getBoundingClientRect().bottom || rb.bottom > innerHeight - 90)
        window.scrollBy({ top: rb.top - innerHeight / 3, behavior: "smooth" });
    }
    speechSynthesis.speak(u);
  }
  $("dlb-say").onclick = function () {
    if (TTS.on) { sayStop(); return; }
    var si = selInfo();
    sayFrom(si ? si.p : firstVisible());
  };
  window.addEventListener("pagehide", sayStop);

  /* ------------------------------------------------ surlignages et notes */
  /* gardés dans ce navigateur : localStorage["dlb.notes"] = { page: [ {q, p, n, ti, t} ] } */
  var NK = "dlb.notes", PK = SLUG || path, marks = [];
  function allNotes() { try { return JSON.parse(localStorage.getItem(NK) || "{}") || {}; } catch (e) { return {}; } }
  function notes() { return allNotes()[PK] || []; }
  function setNotes(a) {
    var s = allNotes();
    if (a.length) s[PK] = a; else delete s[PK];
    try { localStorage.setItem(NK, JSON.stringify(s)); } catch (e) {}
    paint();
  }
  function findNote(it) {
    var T = textMap(), best = -1, k = T.buf.indexOf(it.q);
    while (k > -1) { if (best < 0 || Math.abs(k - it.p) < Math.abs(best - it.p)) best = k; k = T.buf.indexOf(it.q, k + 1); }
    return best;
  }
  function paint() {
    marks = [];
    var a = notes(), h1 = HL && new Highlight(), h2 = HL && new Highlight();
    a.forEach(function (it, i) {
      var k = findNote(it);
      if (k < 0) return;
      var r = rangeOf(k, k + it.q.length);
      marks.push({ i: i, r: r });
      if (HL) (it.n ? h2 : h1).add(r);
    });
    if (HL) { CSS.highlights.set("dlb-hl", h1); CSS.highlights.set("dlb-note", h2); }
    var c = $("dlb-notesb").querySelector(".dlb-cnt");
    c.textContent = a.length || ""; c.hidden = !a.length;
    if (!panel.hidden) renderPanel();
  }

  var pop = document.createElement("div");
  pop.id = "dlb-pop"; pop.hidden = true;
  document.body.appendChild(pop);
  function placePop(rect) {
    pop.hidden = false;
    var h = pop.offsetHeight, w = pop.offsetWidth;
    var top = rect.bottom + 10;
    if (top + h > innerHeight - 90) top = rect.top - h - 10;
    pop.style.top = Math.max(bar.getBoundingClientRect().bottom + 6, top) + "px";
    pop.style.left = Math.min(innerWidth - w - 8, Math.max(8, rect.left + rect.width / 2 - w / 2)) + "px";
  }
  function hidePop() { pop.hidden = true; pop.innerHTML = ""; pop.dataset.i = ""; }
  function selInfo() {
    var s = getSelection();
    if (!s.rangeCount || s.isCollapsed) return null;
    var r = s.getRangeAt(0);
    if (!wrap.contains(r.commonAncestorContainer)) return null;
    var q = s.toString().replace(/\s+/g, " ").trim();
    return q.length < 2 ? null : { r: r, q: q, p: locate(r) };
  }
  function editor(i, rect) {
    var it = notes()[i];
    if (!it) return;
    pop.dataset.i = i;
    pop.innerHTML = '<textarea rows="4" placeholder="Votre note…">' + esc(it.n || "") + "</textarea>" +
      '<div class="dlb-pact"><button data-a="save" class="dlb-pri">Enregistrer</button>' +
      '<button data-a="del">Retirer</button><button data-a="close">Fermer</button></div>';
    placePop(rect);
    pop.querySelector("textarea").focus();
  }
  function addNote(si) {
    var a = notes(), dup = -1;
    a.forEach(function (it, i) { if (it.q === si.q && Math.abs(it.p - si.p) < 40) dup = i; });
    if (dup < 0) { a.push({ q: si.q, p: si.p, n: "", ti: document.title, t: Date.now() }); dup = a.length - 1; setNotes(a); }
    return dup;
  }
  var selT = null, lastSi = null, touched = 0;
  document.addEventListener("selectionchange", function () {
    clearTimeout(selT);
    selT = setTimeout(function () {
      if (pop.contains(document.activeElement) || Date.now() - touched < 900) return;
      var si = selInfo();
      if (!si) { if (!pop.dataset.i) hidePop(); return; }
      lastSi = si;
      pop.dataset.i = "";
      pop.innerHTML = '<button data-a="hl">' + ic("mark") + "Surligner</button>" +
        '<button data-a="note">Note</button>' +
        ("speechSynthesis" in window ? '<button data-a="read">' + ic("say") + "Lire d'ici</button>" : "");
      placePop(si.r.getBoundingClientRect());
    }, 260);
  });
  pop.addEventListener("pointerdown", function () { touched = Date.now(); });
  pop.addEventListener("mousedown", function (e) { if (e.target.tagName !== "TEXTAREA") e.preventDefault(); });
  pop.addEventListener("click", function (e) {
    var b = e.target.closest("[data-a]");
    if (!b) return;
    var act = b.dataset.a, si = selInfo() || lastSi, a = notes(), i = +pop.dataset.i;
    lastSi = null;
    if (act === "hl" && si) { addNote(si); getSelection().removeAllRanges(); hidePop(); }
    else if (act === "note" && si) { var rect = si.r.getBoundingClientRect(); i = addNote(si); getSelection().removeAllRanges(); editor(i, rect); }
    else if (act === "read" && si) { var p = si.p; getSelection().removeAllRanges(); hidePop(); sayFrom(p); }
    else if (act === "save" && a[i]) { a[i].n = pop.querySelector("textarea").value.trim(); setNotes(a); hidePop(); }
    else if (act === "del" && a[i]) { a.splice(i, 1); setNotes(a); hidePop(); }
    else if (act === "close") hidePop();
  });
  /* un clic sur un passage surligné ouvre sa note */
  wrap.addEventListener("click", function (e) {
    if (!marks.length || !getSelection().isCollapsed || e.target.closest("a,img")) return;
    var c = document.caretRangeFromPoint ? document.caretRangeFromPoint(e.clientX, e.clientY)
      : document.caretPositionFromPoint && (function (p) { if (!p) return null; var r = document.createRange(); r.setStart(p.offsetNode, p.offset); return r; })(document.caretPositionFromPoint(e.clientX, e.clientY));
    if (!c) return;
    for (var k = 0; k < marks.length; k++) {
      if (marks[k].r.isPointInRange(c.startContainer, c.startOffset)) { editor(marks[k].i, marks[k].r.getBoundingClientRect()); return; }
    }
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !pop.hidden) hidePop(); });

  var panel = document.createElement("aside");
  panel.id = "dlb-notes"; panel.hidden = true;
  document.body.appendChild(panel);
  function renderPanel() {
    var a = notes();
    panel.innerHTML = '<header><b>Mes notes</b><span>' + (a.length ? a.length + " sur cette page" : "") + "</span>" +
      '<button data-a="close" title="Fermer">×</button></header>' +
      (a.length ? "<ol>" + a.map(function (it, i) {
        return '<li data-i="' + i + '"><q>' + esc(it.q.length > 280 ? it.q.slice(0, 280) + "…" : it.q) + "</q>" +
          (it.n ? "<p>" + esc(it.n) + "</p>" : "") +
          '<div><button data-a="go">Aller</button><button data-a="edit">' + (it.n ? "Modifier" : "Ajouter une note") + "</button>" +
          '<button data-a="del">Retirer</button></div></li>';
      }).join("") + "</ol>"
        : '<p class="dlb-empty">Sélectionnez un passage pour le surligner ou l\'annoter.<br>Vos notes restent dans ce navigateur, sur cet appareil.</p>') +
      '<footer><button data-a="exp">Exporter cette page</button><button data-a="expall">Exporter toutes mes notes</button></footer>';
  }
  function exportMd(all) {
    var s = allNotes(), keys = all ? Object.keys(s) : [PK], out = ["# Notes de lecture — Hervé Delboy, alchimie", ""];
    keys.forEach(function (k) {
      var a = s[k] || [];
      if (!a.length) return;
      out.push("## " + (a[0].ti || k), "", "Page : " + new URL(BASE + "original/" + k + ".html", location.href).href, "");
      a.forEach(function (it) { out.push("> " + it.q, ""); if (it.n) out.push(it.n, ""); });
    });
    var link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([out.join("\n")], { type: "text/markdown;charset=utf-8" }));
    link.download = all ? "notes-delboy.md" : "notes-" + PK + ".md";
    document.body.appendChild(link); link.click(); link.remove();
  }
  function togglePanel(open) {
    panel.hidden = !open;
    root.classList.toggle("dlb-panel", open);
    if (open) renderPanel();
    $("dlb-notesb").classList.toggle("on", open);
    $("dlb-notesb").setAttribute("aria-pressed", open ? "true" : "false");
  }
  $("dlb-notesb").onclick = function () { togglePanel(panel.hidden); };
  panel.addEventListener("click", function (e) {
    var b = e.target.closest("[data-a]");
    if (!b) return;
    var li = b.closest("li"), i = li ? +li.dataset.i : -1, a = notes();
    var m = marks.filter(function (x) { return x.i === i; })[0];
    if (b.dataset.a === "close") togglePanel(false);
    else if (b.dataset.a === "go" && m) {
      var rb = m.r.getBoundingClientRect();
      window.scrollBy({ top: rb.top - innerHeight / 3, behavior: "smooth" });
      if (HL) { CSS.highlights.set("dlb-lecture", new Highlight(m.r)); setTimeout(function () { if (!TTS.on) CSS.highlights.delete("dlb-lecture"); }, 1600); }
      if (innerWidth < 820) togglePanel(false);
    }
    else if (b.dataset.a === "edit" && m) { if (innerWidth < 820) togglePanel(false); setTimeout(function () { editor(i, m.r.getBoundingClientRect()); }, 50); }
    else if (b.dataset.a === "del" && a[i]) { a.splice(i, 1); setNotes(a); }
    else if (b.dataset.a === "exp") exportMd(false);
    else if (b.dataset.a === "expall") exportMd(true);
  });
  if (document.readyState === "complete") paint(); else window.addEventListener("load", paint);

  /* ------------------------------------------------ EPUB (zip sans compression) */
  var CRC = (function () { var t = [], c; for (var n = 0; n < 256; n++) { c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(b) { var c = 0xFFFFFFFF; for (var i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function zip(files) {
    var enc = new TextEncoder(), parts = [], cent = [], off = 0;
    function u16(v) { return [v & 255, (v >>> 8) & 255]; }
    function u32(v) { return [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255]; }
    files.forEach(function (f) {
      var name = enc.encode(f.name), data = typeof f.data === "string" ? enc.encode(f.data) : f.data, crc = crc32(data);
      var head = [].concat([0x50, 0x4b, 3, 4], u16(20), u16(0x0800), u16(0), u16(0), u16(0x21), u32(crc), u32(data.length), u32(data.length), u16(name.length), u16(0));
      parts.push(new Uint8Array(head), name, data);
      cent.push(new Uint8Array([].concat([0x50, 0x4b, 1, 2], u16(20), u16(20), u16(0x0800), u16(0), u16(0), u16(0x21), u32(crc), u32(data.length), u32(data.length), u16(name.length), u16(0), u16(0), u16(0), u16(0), u32(0), u32(off))), name);
      off += head.length + name.length + data.length;
    });
    var csize = cent.reduce(function (s, p) { return s + p.length; }, 0);
    var end = new Uint8Array([].concat([0x50, 0x4b, 5, 6], u16(0), u16(0), u16(files.length), u16(files.length), u32(csize), u32(off), u16(0)));
    return new Blob(parts.concat(cent, [end]), { type: "application/epub+zip" });
  }
  function epub(btn) {
    btn = btn.querySelector(".dlb-xl") || btn;
    var label = btn.textContent;
    var title = (document.title || SLUG).trim();
    var clone = wrap.cloneNode(true);
    [].forEach.call(clone.querySelectorAll("script,style,map,iframe,object,embed"), function (n) { n.remove(); });
    /* balises Word (o:p, st1:…) et attributs à préfixe : sans espace de noms en XHTML */
    [].slice.call(clone.querySelectorAll("*")).forEach(function (n) {
      if (n.tagName.indexOf(":") > -1) { while (n.firstChild) n.parentNode.insertBefore(n.firstChild, n); n.remove(); return; }
      [].slice.call(n.attributes).forEach(function (a) { if (a.name.indexOf(":") > -1 || !/^[a-zA-Z_][\w.\-]*$/.test(a.name)) n.removeAttribute(a.name); });
    });
    var imgs = [].slice.call(clone.querySelectorAll("img")), files = [], seen = {}, done = 0;
    btn.textContent = "EPUB : 0 / " + imgs.length;
    var jobs = imgs.map(function (im, i) {
      var src = im.getAttribute("src") || "";
      var abs = new URL(src, location.href).href;
      var name = "img/" + decodeURIComponent(abs.split("/").pop()).replace(/[^\w.\-]/g, "_");
      im.setAttribute("src", name);
      [].slice.call(im.attributes).forEach(function (a) { if (!/^(src|alt|width|height)$/.test(a.name)) im.removeAttribute(a.name); });
      if (!im.hasAttribute("alt")) im.setAttribute("alt", "");
      if (seen[name]) return Promise.resolve();
      seen[name] = 1;
      return fetch(abs).then(function (r) { return r.ok ? r.arrayBuffer() : null; }).then(function (b) {
        if (b) files.push({ name: "OEBPS/" + name, data: new Uint8Array(b), type: /\.png$/i.test(name) ? "image/png" : /\.gif$/i.test(name) ? "image/gif" : "image/jpeg", id: "i" + i });
        btn.textContent = "EPUB : " + (++done) + " / " + imgs.length;
      }).catch(function () {});
    });
    [].forEach.call(clone.querySelectorAll("a[href]"), function (a) { var h = a.getAttribute("href"); if (h.charAt(0) !== "#") a.setAttribute("href", new URL(h, location.href).href); });
    Promise.all(jobs).then(function () {
      var doc = document.implementation.createDocument("http://www.w3.org/1999/xhtml", "html", null);
      var h = doc.documentElement;
      h.setAttribute("xml:lang", "fr");
      var head = doc.createElementNS("http://www.w3.org/1999/xhtml", "head");
      var t = doc.createElementNS("http://www.w3.org/1999/xhtml", "title"); t.textContent = title; head.appendChild(t);
      var body = doc.createElementNS("http://www.w3.org/1999/xhtml", "body");
      body.appendChild(doc.importNode(clone, true));
      h.appendChild(head); h.appendChild(body);
      var xhtml = '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n' + new XMLSerializer().serializeToString(doc);
      var id = "urn:delboy:" + SLUG;
      var manifest = files.map(function (f) { return '<item id="' + f.id + '" href="' + f.name.slice(6) + '" media-type="' + f.type + '"/>'; }).join("");
      var opf = '<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">' + id + '</dc:identifier><dc:title>' + esc(title) + '</dc:title><dc:creator>Hervé Delboy</dc:creator><dc:language>fr</dc:language><dc:rights>© Hervé Delboy et ayants droit. Tous droits réservés.</dc:rights><meta property="dcterms:modified">' + new Date().toISOString().slice(0, 19) + 'Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="page" href="page.xhtml" media-type="application/xhtml+xml"/>' + manifest + '</manifest><spine><itemref idref="page"/></spine></package>';
      var nav = '<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>' + esc(title) + '</title></head><body><nav epub:type="toc"><ol><li><a href="page.xhtml">' + esc(title) + "</a></li></ol></nav></body></html>";
      var blob = zip([
        { name: "mimetype", data: "application/epub+zip" },
        { name: "META-INF/container.xml", data: '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>' },
        { name: "OEBPS/content.opf", data: opf },
        { name: "OEBPS/nav.xhtml", data: nav },
        { name: "OEBPS/page.xhtml", data: xhtml }
      ].concat(files));
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = SLUG + ".epub";
      document.body.appendChild(a); a.click(); a.remove();
      btn.textContent = label;
    });
  }
})();
