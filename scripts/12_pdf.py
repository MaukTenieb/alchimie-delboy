"""Étape 12 : livres PDF, un par section.

Chaque section du plan devient un livre imprimable : couverture, sommaire des
pièces, puis les textes dans l'ordre, avec leurs illustrations et la référence
de la capture d'archive. Les fiches d'autorité existent aussi en PDF.

Les polices sont embarquées (Georgia, Times ou DejaVu) : les caractères
français, œ compris, sont rendus correctement.
"""
from __future__ import annotations

import html
import json
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                PageTemplate, Paragraph, Spacer)

from common import DATA, SITE, log, read_json, slugify

FONTS = [
    ("Georgia", "/c/Windows/Fonts/georgia.ttf", "/c/Windows/Fonts/georgiab.ttf",
     "/c/Windows/Fonts/georgiai.ttf", "/c/Windows/Fonts/georgiaz.ttf"),
    ("DejaVu", "/c/Windows/Fonts/DejaVuSerif.ttf",
     "/c/Windows/Fonts/DejaVuSerif-Bold.ttf", None, None),
    ("Vera", None, None, None, None),
]


def register_fonts():
    for name, reg, bold, ital, boldital in FONTS:
        if not reg or not os.path.exists(reg):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, reg))
            if bold and os.path.exists(bold):
                pdfmetrics.registerFont(TTFont(name + "-Bold", bold))
            if ital and os.path.exists(ital):
                pdfmetrics.registerFont(TTFont(name + "-Italic", ital))
            return name
        except Exception:
            continue
    return "Helvetica"


def esc(s: str) -> str:
    s = html.escape(str(s), quote=False)
    return s.replace("&lt;", "‹").replace("&gt;", "›")


def build(book, font, path, meta):
    pw, ph = A5
    doc = BaseDocTemplate(
        path, pagesize=A5, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=meta["title"], author="Hervé Delboy",
        subject=meta.get("subject", ""), creator="delboy-alchimie")

    def footer(canv, d):
        canv.saveState()
        canv.setFont(font, 7.5)
        canv.setFillColor(colors.HexColor("#6b5d4b"))
        canv.drawString(18 * mm, 10 * mm, "Hervé Delboy — alchimie")
        canv.drawRightString(pw - 18 * mm, 10 * mm, str(canv.getPageNumber()))
        canv.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="body")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame],
                                       onPage=footer)])

    S = {
        "title": ParagraphStyle("t", fontName=font, fontSize=21, leading=25,
                                spaceAfter=10, textColor=colors.HexColor("#7b2d1c")),
        "sub": ParagraphStyle("s", fontName=font, fontSize=10, leading=14,
                              textColor=colors.HexColor("#544a3c")),
        "h1": ParagraphStyle("h1", fontName=font, fontSize=15, leading=19,
                             spaceBefore=6, spaceAfter=8,
                             textColor=colors.HexColor("#7b2d1c")),
        "h2": ParagraphStyle("h2", fontName=font, fontSize=11.5, leading=15,
                             spaceBefore=8, spaceAfter=4),
        "body": ParagraphStyle("b", fontName=font, fontSize=9.6, leading=14,
                               alignment=TA_JUSTIFY, spaceAfter=5),
        "src": ParagraphStyle("src", fontName=font, fontSize=7.4, leading=10,
                              textColor=colors.HexColor("#6b5d4b"),
                              spaceAfter=8),
        "cap": ParagraphStyle("cap", fontName=font, fontSize=7, leading=9,
                              textColor=colors.HexColor("#6b5d4b")),
        "toc": ParagraphStyle("toc", fontName=font, fontSize=9, leading=13),
    }

    story = [Paragraph(esc(meta["title"]), S["title"]),
             Paragraph(esc(meta["sub"]), S["sub"]), Spacer(1, 10 * mm),
             Paragraph("Sommaire", S["h2"])]
    for i, (title, n) in enumerate(meta["toc"], 1):
        story.append(Paragraph(f"{i}. {esc(title)}", S["toc"]))
    story.append(Spacer(1, 6 * mm))

    for item in book:
        flow = [Paragraph(esc(item["title"]), S["h1"])]
        if item.get("source"):
            flow.append(Paragraph(esc(item["source"]), S["src"]))
        for kind, text in item["paras"]:
            if len(text.strip()) < 3:
                continue
            style = S["h2"] if kind.startswith("h") else S["body"]
            flow.append(Paragraph(esc(text), style))
        for loc, alt in item.get("images", [])[:12]:
            try:
                img = Image(loc)
                ratio = img.imageHeight / float(img.imageWidth or 1)
                w = 70 * mm
                img.drawWidth = w
                img.drawHeight = w * ratio
                if img.drawHeight > 90 * mm:
                    img.drawHeight = 90 * mm
                    img.drawWidth = 90 * mm / ratio
                cap = Paragraph(esc(alt), S["cap"]) if alt else Spacer(1, 2)
                flow.append(KeepTogether([Spacer(1, 3), img, cap]))
            except Exception:
                pass
        flow.append(Spacer(1, 6 * mm))
        story.extend(flow)

    doc.build(story)


def main() -> None:
    font = register_fonts()
    sel = read_json(os.path.join(DATA, "selection.json"))
    docs = {d["key"]: d for d in
            (json.loads(l) for l in
             open(os.path.join(DATA, "docs.jsonl"), encoding="utf-8"))}
    kept = [r for r in sel["kept"] if r["key"] in docs]
    kept.sort(key=lambda r: (r["section"], -r["chars"], r["key"]))

    from common import slugify as slugify_key
    out = os.path.join(SITE, "pdf")
    os.makedirs(out, exist_ok=True)

    # slug des articles, identique au site
    slug, used = {}, set()
    for r in kept:
        base, i = slugify_key(os.path.splitext(r["key"])[0], 70), 2
        s = base
        while s in used:
            s = f"{base}-{i}"
            i += 1
        used.add(s)
        slug[r["key"]] = s

    SECTIONS = {
        "1": "Collection des grands traités",
        "2": "Gravures et emblèmes",
        "3": "Symboles et spagyrie",
        "4": "L’idée alchimique",
        "5": "Précis de symbolisme",
        "6": "L’arsenal hermétique",
        "7": "Le laboratoire légendaire",
        "8": "Les textes",
        "DC": "Les Douze Clefs de philosophie",
        "9": "Études et annexes",
    }
    assets = {}
    adir = os.path.join(SITE, "assets")
    if os.path.isdir(adir):
        for f in os.listdir(adir):
            assets[f.lower()] = f

    total = 0
    for sid, label in SECTIONS.items():
        items = [r for r in kept if r["section"] == sid]
        if not items:
            continue
        book = []
        for r in items:
            d = docs[r["key"]]
            imgs = []
            for im in d["images"]:
                name = im["src"].split("/")[-1].lower()
                loc = assets.get(name)
                if loc and loc.lower().endswith((".jpg", ".jpeg", ".png")):
                    imgs.append((os.path.join(SITE, "assets", loc), im["alt"]))
            book.append({
                "title": r["title"],
                "source": f"Capture du {d['ts'][:4]}-{d['ts'][4:6]}-{d['ts'][6:8]}"
                          f" — {d['url']}",
                "paras": d["paras"],
                "images": imgs,
            })
        meta = {"title": label,
                "sub": f"Partie alchimique du site d’Hervé Delboy — {len(items)} pièces",
                "subject": "alchimie",
                "toc": [(r["title"], r["chars"]) for r in items]}
        path = os.path.join(out, f"section-{sid.lower()}.pdf")
        build(book, font, path, meta)
        size = os.path.getsize(path)
        total += size
        log(f"  section {sid:<2} {label[:34]:<34} {size/1e6:5.1f} Mo")
    log(f"PDF : {total/1e6:.1f} Mo dans site/pdf/")


if __name__ == "__main__":
    main()
