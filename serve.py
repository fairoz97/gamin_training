#!/usr/bin/env python3
"""Serve commander.html locally and let its REFRESH button re-run pull.py.

    python serve.py                                   # http://127.0.0.1:8765
    python serve.py --race 2027-03-14 --race-name "My Race"

POST /refresh runs pull.py, then build_commander.py, then the page reloads.
Only commander.html is served (never .env or data/), and only to this machine.
"""
import argparse
import json
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
lock = threading.Lock()
ARGS = None


def run(cmd, timeout):
    p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def refresh():
    code, log = run([sys.executable, "pull.py"], timeout=900)
    if code != 0:
        return False, log or f"pull.py exited with {code}"
    build = [sys.executable, "build_commander.py"]
    if ARGS.race:
        build += ["--race", ARGS.race]
    if ARGS.race_name:
        build += ["--race-name", ARGS.race_name]
    code2, log2 = run(build, timeout=120)
    if code2 != 0:
        return False, log2 or f"build_commander.py exited with {code2}"
    return True, log + "\n" + log2


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _local_origin_ok(self):
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in hosts:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{h}" for h in hosts}

    def do_GET(self):
        if self.path.split("?")[0] in ("/", "/commander.html"):
            self._send(200, (HERE / "commander.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path != "/refresh":
            return self._send(404, json.dumps({"ok": False, "log": "not found"}))
        if not self._local_origin_ok() or self.headers.get("X-Commander") != "1":
            return self._send(403, json.dumps({"ok": False, "log": "forbidden"}))
        if not lock.acquire(blocking=False):
            return self._send(409, json.dumps({"ok": False, "log": "a refresh is already running"}))
        try:
            try:
                ok, log = refresh()
            except subprocess.TimeoutExpired:
                ok, log = False, "timed out"
            self._send(200, json.dumps({"ok": ok, "log": log[-2000:]}))
        finally:
            lock.release()


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--race", help="goal race date, YYYY-MM-DD")
    ap.add_argument("--race-name")
    ap.add_argument("--no-open", action="store_true")
    ARGS = ap.parse_args()

    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.port), Handler)
    url = f"http://127.0.0.1:{ARGS.port}/"
    print(f"Commander on {url}  (Ctrl+C to stop)")
    if not ARGS.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
