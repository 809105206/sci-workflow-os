#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
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


def _credential_status() -> dict[str, object]:
    source = str(PROJECT / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from sciops.credentials import credential_status, load_runtime_credentials

    load_runtime_credentials()
    return credential_status()


class ResearchConsoleHandler(SimpleHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_download(self, payload: dict[str, object]) -> None:
        body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header(
            "Content-Disposition", 'attachment; filename="sciops-credentials.private.json"'
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _local_same_origin(self) -> bool:
        try:
            peer = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin", "")
        custom_header = self.headers.get("X-Sciops-Local", "")
        if not peer.is_loopback or not host or custom_header != "1":
            return False
        try:
            host_name = urlsplit(f"//{host}").hostname or ""
            if not ipaddress.ip_address(host_name).is_loopback:
                return False
        except ValueError:
            if host_name != "localhost":
                return False
        return origin.rstrip("/") == f"http://{host}"

    def _read_json_body(self) -> object:
        from sciops.credentials import MAX_CREDENTIAL_FILE_BYTES

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("无效 Content-Length") from exc
        if length < 1 or length > MAX_CREDENTIAL_FILE_BYTES:
            raise ValueError("凭据请求体必须在 1 B 到 64 KiB 之间")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求体不是有效 UTF-8 JSON") from exc

    def do_GET(self) -> None:  # noqa: N802
        if urlsplit(self.path).path == "/api/resume":
            try:
                self._send_json(200, _resume_report())
            except (OSError, RuntimeError, ValueError) as exc:
                self._send_json(500, {"status": "error", "message": str(exc)})
            return
        if urlsplit(self.path).path == "/api/credentials/status":
            try:
                self._send_json(200, _credential_status())
            except (OSError, RuntimeError, ValueError) as exc:
                self._send_json(500, {"status": "error", "message": str(exc)})
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path not in {"/api/credentials/export", "/api/credentials/import"}:
            self._send_json(404, {"status": "error", "message": "未找到接口"})
            return
        if not self._local_same_origin():
            self._send_json(403, {"status": "error", "message": "仅允许本机同源前端操作"})
            return
        try:
            from sciops.credentials import (
                export_runtime_to_json,
                import_credential_payload,
                read_credential_payload,
            )

            if path == "/api/credentials/export":
                export_runtime_to_json()
                self._send_download(read_credential_payload())
                return
            payload = self._read_json_body()
            import_credential_payload(payload, merge=True)
            self._send_json(
                200,
                {
                    "status": "ok",
                    "message": "凭据包已验证并保存到本机",
                    "credentials": _credential_status(),
                },
            )
        except (OSError, RuntimeError, ValueError) as exc:
            self._send_json(400, {"status": "error", "message": str(exc)})


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
