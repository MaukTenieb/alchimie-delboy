"""Serveur local du site (stdlib uniquement).

Sert le dossier site/ avec compression gzip des données JSON — l'index pèse
43 Mo à cru, ~10 Mo compressé. Indispensable : l'ouverture directe des pages
par file:// empêche le navigateur de charger l'index.

    python serve.py [port]
"""
from __future__ import annotations

import gzip
import http.server
import io
import os
import socketserver
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
GZIP_EXT = {".json", ".html", ".css", ".js", ".svg", ".txt"}
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8788


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        if self.path.startswith("/assets/") or self.path.startswith("/style.css"):
            self.send_header("Cache-Control", "public, max-age=86400")
        elif self.path.startswith("/data/"):
            # court : l'index est régénéré à chaque reconstruction
            self.send_header("Cache-Control", "public, max-age=60")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().do_GET()
        if not os.path.exists(path):
            self.send_error(404, "Page absente de la reconstitution")
            return
        ext = os.path.splitext(path)[1].lower()
        accepts = "gzip" in self.headers.get("Accept-Encoding", "")
        if ext in GZIP_EXT and accepts and os.path.getsize(path) > 1024:
            with open(path, "rb") as f:
                raw = f.read()
            body = gzip.compress(raw, 6)
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return
        return super().do_GET()

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith("4"):
            sys.stderr.write("  %s\n" % (fmt % args))


if __name__ == "__main__":
    os.chdir(ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Site sur http://127.0.0.1:{PORT}/  (Ctrl+C pour arrêter)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
