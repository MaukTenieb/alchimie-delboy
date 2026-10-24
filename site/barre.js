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
  var KEY = "dlb.liseuse";
  var S = { zoom: 1, mode: "orig", font: "orig", col: false, loupe: false };
  try { Object.assign(S, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} }

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
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>'
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
    '<span class="dlb-where"><a href="' + BASE + 'sommaire.html">Sommaire</a><span class="dlb-sec"></span></span>' +
    '<span class="dlb-tools">' +
      '<a class="dlb-b" id="dlb-prev" title="Page précédente (←)">' + ic("prev") + "</a>" +
      '<a class="dlb-b" id="dlb-next" title="Page suivante (→)">' + ic("next") + "</a>" +
      '<span class="dlb-sep"></span>' +
      '<button class="dlb-b" id="dlb-minus" title="Réduire (−)">' + ic("minus") + "</button>" +
      '<button class="dlb-z" id="dlb-zoom" title="Taille d\'origine (0)">100 %</button>' +
      '<button class="dlb-b" id="dlb-plus" title="Agrandir (+)">' + ic("plus") + "</button>" +
      '<span class="dlb-sep"></span>' +
      '<button class="dlb-b" id="dlb-font" title="Police : originale, sérif, sans sérif">' + ic("font") + "</button>" +
      '<button class="dlb-b" id="dlb-col" title="Colonne de lecture">' + ic("col") + "</button>" +
      '<button class="dlb-b" id="dlb-mode" title="Affichage : original, noir et blanc, nuit">' + ic("mode") + "</button>" +
      '<button class="dlb-b" id="dlb-loupe" title="Loupe sur les planches (L)">' + ic("loupe") + "</button>" +
      '<span class="dlb-sep"></span>' +
      '<span class="dlb-menuw"><button class="dlb-b" id="dlb-out" title="Exporter">' + ic("down") + "</button>" +
      '<span class="dlb-menu" id="dlb-menu" hidden>' +
        '<button data-out="pdf">PDF de la page</button>' +
        '<button data-out="epub">EPUB de la page</button>' +
        '<a id="dlb-secpdf" hidden>PDF de la section</a>' +
        '<a href="' + BASE + 'recherche.html">Recherche</a>' +
        '<a href="' + BASE + 'notice.html">Notice</a>' +
      "</span></span>" +
    "</span>";

  function $(id) { return document.getElementById(id); }
  var root = document.documentElement;

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
  $("dlb-menu").onclick = function (e) {
    var b = e.target.closest("[data-out]");
    if (!b) return;
    if (b.dataset.out === "pdf") window.print();
    if (b.dataset.out === "epub") epub(b);
  };
  apply();

  /* ------------------------------------------------ ordre du plan */
  fetch(BASE + "data/nav.json").then(function (r) { return r.json(); }).then(function (N) {
    var p = SLUG && N.pages[SLUG];
    if (!p) { $("dlb-prev").classList.add("off"); $("dlb-next").classList.add("off"); return; }
    var sec = N.sections[p[1]];
    document.querySelector(".dlb-sec").innerHTML = ' <i>›</i> <a href="' + BASE + "sections/" + p[1] + '.html">' + esc(sec[0]) + "</a>";
    function link(id, s) {
      var a = $(id);
      if (s && N.pages[s]) { a.href = BASE + "original/" + s + ".html"; a.title += " — " + N.pages[s][0]; }
      else a.classList.add("off");
    }
    link("dlb-prev", p[2]); link("dlb-next", p[3]);
    if (sec[1]) { var sp = $("dlb-secpdf"); sp.hidden = false; sp.href = BASE + sec[1]; sp.textContent = "PDF de la section, " + sec[2]; }
    document.title = document.title || p[0];
  }).catch(function () {});

  /* ------------------------------------------------ clavier */
  document.addEventListener("keydown", function (e) {
    if (e.target.closest && e.target.closest("input,textarea,select")) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (viewer.open) return;
    if (e.key === "+" || e.key === "=") zoom(0.1);
    else if (e.key === "-") zoom(-0.1);
    else if (e.key === "0") { S.zoom = 1; apply(); }
    else if (e.key === "l" || e.key === "L") { S.loupe = !S.loupe; apply(); }
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
