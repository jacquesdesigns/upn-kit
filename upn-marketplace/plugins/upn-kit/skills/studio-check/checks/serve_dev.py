"""Dev server for any studio job (6 Oct 2026): no-cache headers, plus a real-device recorder at /_devcheck/.

python3's http.server sends no cache headers, so a browser can keep an old script beside a new page while files change.
/_devcheck/ is a page you open on a REAL phone (the Wi-Fi twin URL): it records the touch and wheel event streams your
finger actually produces, and any scrolling that carries on after the finger lifts (iOS momentum), and POSTs them back
here, to <out>/devcheck-<time>.json. Summarise with devcheck_summary.py; inputs.py can then be tuned to the real shape.

python3 serve_dev.py <port> <bind address> <directory> [--out <folder for devcheck json>]
"""
import sys, os, json, time, http.server, functools
port, bind, directory = int(sys.argv[1]), sys.argv[2], sys.argv[3]
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(directory, "..", "evidence", "devcheck")
PAGE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "devcheck.html"), "rb").read()
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0"); self.send_header("Pragma", "no-cache"); super().end_headers()
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.split("?")[0].rstrip("/") == "/_devcheck":
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(PAGE); return
        super().do_GET()
    def do_POST(self):
        if self.path.startswith("/_devcheck/save"):
            n = int(self.headers.get("Content-Length", 0)); body = self.rfile.read(n); os.makedirs(out, exist_ok=True)
            f = os.path.join(out, "devcheck-%s.json" % time.strftime("%Y%m%d-%H%M%S")); open(f, "wb").write(body)
            self.send_response(200); self.end_headers(); self.wfile.write(b"saved " + os.path.basename(f).encode()); return
        self.send_response(404); self.end_headers()
http.server.ThreadingHTTPServer((bind, port), functools.partial(H, directory=directory)).serve_forever()
