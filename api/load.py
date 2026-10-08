from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.parse import urlparse, parse_qs

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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/load":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        raffle_id = params.get("id", [None])[0]

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
            raffle = next((x for x in raffles if x.get("id") == raffle_id), None)

            if not raffle:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Sorteo no encontrado"}).encode())
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "id": raffle["id"],
                "name": raffle["name"],
                "participants": raffle.get("participants", []),
                "numberOfWinners": raffle.get("numberOfWinners", 1),
                "createdAt": raffle.get("createdAt", 0),
            }).encode())

        except Exception:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": "Sorteo no encontrado"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
