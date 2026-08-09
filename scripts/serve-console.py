#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the built SCI Workflow Research Console.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    project = Path(__file__).resolve().parents[1]
    console = project / "console" / "dist"
    if not (console / "index.html").is_file():
        raise SystemExit("Built console not found. Run: cd console && npm install && npm run build")

    handler = partial(SimpleHTTPRequestHandler, directory=os.fspath(console))
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
