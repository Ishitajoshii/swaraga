"""Launch the local demo: python scripts/run_demo.py --port 8765."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.demo import DemoService


def create_server(port=8765, root=ROOT):
    service = DemoService(root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, body, content_type, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, value, status=200):
            self.send(json.dumps(value).encode(), "application/json; charset=utf-8", status)

        def do_GET(self):
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            get = lambda key, default=None: params.get(key, [default])[0]
            try:
                if url.path == "/api/state":
                    return self.send_json(service.state())
                if url.path == "/api/rank":
                    return self.send_json(service.bank.rank(get("id")))
                if url.path == "/api/audio":
                    audio = service.audio(get("kind"), get("id"), get("part"), get("mode", "prepared"), get("response"))
                    return self.send(audio, "audio/wav")
                assets = {"/": ("index.html", "text/html; charset=utf-8"),
                          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                          "/style.css": ("style.css", "text/css; charset=utf-8")}
                if url.path in assets:
                    file, content_type = assets[url.path]
                    return self.send((root / "demo" / file).read_bytes(), content_type)
                self.send_json({"error": "Not found"}, 404)
            except (ValueError, KeyError, TypeError) as exc:
                self.send_json({"error": str(exc)}, 400)
            except OSError:
                self.send_json({"error": "A local asset is unavailable. Check the terminal and repository files."}, 500)
    class LocalServer(ThreadingHTTPServer):
        # Windows otherwise permits a second reuse-address server to bind the
        # same port, which can leave browsers seeing an older demo process.
        allow_reuse_address = False
        allow_reuse_port = False

        def server_bind(self):
            if sys.platform == "win32":
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()

    server = LocalServer(("127.0.0.1", port), Handler)
    server.service = service
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        server = create_server(args.port)
    except OSError as exc:
        parser.exit(1, f"Cannot start on port {args.port}: {exc}. Stop the previous demo or use --port 8766.\n")
    print(f"Swaraga is ready at http://127.0.0.1:{server.server_port} - Ctrl+C to stop.", flush=True)
    print("Restart after editing the catalog, annotations, or friend files.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
