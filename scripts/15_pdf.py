"""Étape 15 : les dix livres PDF, imprimés depuis les pages de l'auteur.

Chaque section du plan devient un livre : une page de titre avec le sommaire
(titre de chaque pièce et sa première page), puis chaque page de l'auteur
imprimée par Chromium telle qu'elle s'affiche, en mode original, sans la
barre de lecture ni le papier peint de fond. Les signets du PDF reprennent les
titres. Pied de page : titre de la pièce et date de la capture.

À lancer depuis la racine du dépôt : python scripts/15_pdf.py [section ...]
"""
from __future__ import annotations

import functools
import html
import io
import json
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
PORT = 8793
PRINT_CSS = """@media print{body{background-image:none!important;margin:0!important}}"""
SETTINGS = '{"zoom":1,"mode":"orig","font":"orig","col":false,"loupe":false}'


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def serve() -> ThreadingHTTPServer:
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Quiet, directory=SITE)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def footer(title: str, cap: str) -> str:
    return ('<div style="font:7px Georgia,serif;color:#777;width:100%;padding:0 14mm;'
            'display:flex;justify-content:space-between"><span>Hervé Delboy — '
            f'{esc(title)}</span><span>{esc(cap)}</span></div>')


def cover(label: str, rows: list[tuple[str, int]], n_pages: int) -> str:
    items = "".join(f'<tr><td>{esc(t)}</td><td class="n">{p}</td></tr>' for t, p in rows)
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>
@page{{size:A4;margin:22mm 20mm}}
body{{font:11pt/1.5 Georgia,"Times New Roman",serif;color:#1c1a17}}
h1{{font-weight:normal;font-size:26pt;margin:40mm 0 4mm}}
.who{{font-size:13pt;color:#6f675c;margin:0 0 30mm}}
table{{width:100%;border-collapse:collapse;font-size:9.5pt}}
td{{padding:1.6mm 0;border-bottom:.3pt solid #ccc;vertical-align:top}}
td.n{{text-align:right;width:14mm;color:#6f675c}}
.facts{{font-size:8.5pt;color:#6f675c;margin-top:8mm}}
</style></head><body>
<h1>{esc(label)}</h1>
<p class="who">Hervé Delboy — alchimie</p>
<table>{items}</table>
<p class="facts">{len(rows)} pages de l'auteur · {n_pages} pages imprimées · https://mauktenieb.github.io/alchimie-delboy/ · © Hervé Delboy</p>
</body></html>"""


def main() -> None:
    nav = json.load(open(os.path.join(SITE, "data", "nav.json"), encoding="utf-8"))
    pages = json.load(open(os.path.join(SITE, "data", "pages.json"), encoding="utf-8"))
    order = list(nav["sections"])
    want = sys.argv[1:] or order
    srv = serve()
    os.makedirs(os.path.join(SITE, "pdf"), exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context()
        ctx.add_init_script(f"try{{localStorage.setItem('dlb.liseuse',{json.dumps(SETTINGS)})}}catch(e){{}}")
        pg = ctx.new_page()
        for sid in want:
            label = nav["sections"][sid][0]
            slugs = [s for s, v in nav["pages"].items() if v[1] == sid]
            slugs.sort(key=lambda s: list(nav["pages"]).index(s))
            parts = []
            for s in slugs:
                pg.goto(f"http://127.0.0.1:{PORT}/original/{s}.html", wait_until="load", timeout=180000)
                pg.add_style_tag(content=PRINT_CSS)
                pg.wait_for_timeout(300)
                ts = pages.get(s, {}).get("ts", "")
                cap = f"capture du {ts[6:8]}/{ts[4:6]}/{ts[:4]}" if len(ts) >= 8 else ""
                pdf = pg.pdf(format="A4", print_background=True, display_header_footer=True,
                             header_template="<span></span>", footer_template=footer(nav["pages"][s][0], cap),
                             margin={"top": "14mm", "bottom": "16mm", "left": "12mm", "right": "12mm"})
                parts.append((s, PdfReader(io.BytesIO(pdf))))
                print(sid, s, len(parts[-1][1].pages), flush=True)
            # sommaire : première page de chaque pièce (titre et sommaire sur une page, puis +1 par page en trop)
            n_body = sum(len(r.pages) for _, r in parts)
            cov_pages = 1
            for _ in range(3):
                start, rows = cov_pages + 1, []
                for s, r in parts:
                    rows.append((nav["pages"][s][0], start))
                    start += len(r.pages)
                pg.set_content(cover(label, rows, n_body + cov_pages))
                cov = PdfReader(io.BytesIO(pg.pdf(format="A4", print_background=True)))
                if len(cov.pages) == cov_pages:
                    break
                cov_pages = len(cov.pages)
            w = PdfWriter()
            for page in cov.pages:
                w.add_page(page)
            for (s, r), (title, first) in zip(parts, rows):
                for page in r.pages:
                    w.add_page(page)
                w.add_outline_item(title, first - 1)
            w.add_metadata({"/Title": f"{label} — Hervé Delboy, alchimie", "/Author": "Hervé Delboy"})
            out = os.path.join(SITE, "pdf", f"section-{sid}.pdf")
            with open(out, "wb") as f:
                w.write(f)
            print("==", sid, out, len(w.pages), "pages", round(os.path.getsize(out) / 1e6, 1), "Mo", flush=True)
        b.close()
    srv.shutdown()


if __name__ == "__main__":
    main()
