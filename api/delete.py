from http.server import BaseHTTPRequestHandler
import json
import os

import redis

INDEX_KEY = "sorteos:index"


def _r():
    url = os.environ.get("REDIS_URL", "")
    if not url:
        return None
    return redis.Redis.from_url(url, decode_responses=True, socket_timeout=10)


def _read_index(r):
    raw = r.get(INDEX_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _write_index(r, raffles):
    r.set(INDEX_KEY, json.dumps(raffles))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/delete":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        raffle_id = data.get("id", "")

        if not raffle_id:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": "Se requiere un id"}).encode())
            return

        r = _r()
        if r is None:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": "Redis no configurado"}).encode())
            return

        try:
            raffles = _read_index(r)
            raffles = [x for x in raffles if x.get("id") != raffle_id]
            _write_index(r, raffles)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": f"Error: {str(e)}"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
