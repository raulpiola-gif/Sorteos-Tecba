from http.server import BaseHTTPRequestHandler
import json
import os
import time

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
        if self.path != "/api/save":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        name = data.get("name", "").strip()
        participants = data.get("participants", [])
        number_of_winners = data.get("numberOfWinners", 1)

        if not name:
            self._send_error(400, "Se requiere un nombre para el sorteo")
            return
        if not participants:
            self._send_error(400, "Debe haber al menos un participante")
            return

        r = _r()
        if r is None:
            self._send_error(500, "Redis no configurado (falta REDIS_URL)")
            return

        slug = name.lower().replace(" ", "-").replace("/", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        raffle_id = f"{slug}-{int(time.time())}"

        raffle = {
            "id": raffle_id,
            "name": name,
            "participants": participants,
            "numberOfWinners": number_of_winners,
            "createdAt": int(time.time() * 1000),
        }

        try:
            raffles = _read_index(r)
            raffles.insert(0, raffle)
            _write_index(r, raffles)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "id": raffle_id}).encode())

        except Exception as e:
            self._send_error(500, f"Error guardando: {str(e)}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_error(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": False, "error": message}).encode())
