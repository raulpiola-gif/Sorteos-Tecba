from http.server import BaseHTTPRequestHandler
import json
import os
import time
import urllib.request


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

        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")

        if not kv_url or not kv_token:
            self._send_error(500, "Base de datos no configurada. Agrega las variables KV_REST_API_URL y KV_REST_API_TOKEN en Vercel.")
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
            req = urllib.request.Request(
                f"{kv_url}/set/raffle:{raffle_id}",
                data=json.dumps(raffle).encode(),
                headers={
                    "Authorization": f"Bearer {kv_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            urllib.request.urlopen(req)

            # Add to index
            req2 = urllib.request.Request(
                f"{kv_url}/get/raffle:index",
                headers={"Authorization": f"Bearer {kv_token}"},
            )
            try:
                resp = urllib.request.urlopen(req2)
                index = json.loads(resp.read())
            except Exception:
                index = []

            if raffle_id not in index:
                index.append(raffle_id)
                req3 = urllib.request.Request(
                    f"{kv_url}/set/raffle:index",
                    data=json.dumps(index).encode(),
                    headers={
                        "Authorization": f"Bearer {kv_token}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                urllib.request.urlopen(req3)

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
        self.send_header("Content-Type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(message.encode())
