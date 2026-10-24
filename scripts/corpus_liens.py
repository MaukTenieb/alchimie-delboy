"""Contrôle des liens du corpus : chaque URL de corpus/corpus.json, une requête GET.
Sortie : tableau Markdown (résumé du job GitHub Actions) ; code 1 si un lien répond 404 ou 410."""
import json, os, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(open(os.path.join(ROOT, "corpus", "corpus.json"), encoding="utf-8"))
urls = sorted({c["url"] for t in data for c in (t.get("copies") or []) + (t.get("traductions_fr_anciennes") or []) if c.get("url")})
rows, dead = [], 0
for u in urls:
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (corpus-liens; https://github.com/MaukTenieb/alchimie-delboy)", "Range": "bytes=0-2047"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = type(e).__name__
    if code in (404, 410):
        dead += 1
    if code not in (200, 206):
        rows.append(f"| {code} | {u} |")
    time.sleep(1)
out = [f"Liens contrôlés : {len(urls)} · morts (404, 410) : {dead} · autres réponses : {len(rows) - dead}", ""]
if rows:
    out += ["| réponse | lien |", "|---|---|"] + rows
text = "\n".join(out) + "\n"
print(text)
s = os.environ.get("GITHUB_STEP_SUMMARY")
if s:
    open(s, "a", encoding="utf-8").write(text)
sys.exit(1 if dead else 0)
