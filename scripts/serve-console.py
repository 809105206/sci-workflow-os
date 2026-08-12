#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parents[1]


def _resume_report() -> dict[str, object]:
    source = str(PROJECT / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from sciops.onboarding import build_resume_report

    return build_resume_report(include_environment=False)


class ResearchConsoleHandler(SimpleHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlsplit(self.path).path == "/api/resume":
            try:
                self._send_json(200, _resume_report())
            except (OSError, RuntimeError, ValueError) as exc:
                self._send_json(500, {"status": "error", "message": str(exc)})
            return
        super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the built SCI Workflow Research Console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    console = PROJECT / "console" / "dist"
    if not (console / "index.html").is_file():
        raise SystemExit("Built console not found. Run: cd console && npm install && npm run build")

    handler = partial(ResearchConsoleHandler, directory=os.fspath(console))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"SCI Workflow Research Console: {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
