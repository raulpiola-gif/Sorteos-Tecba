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

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")

        if not supabase_url or not supabase_key:
            self._send_error(500, "Supabase no configurado")
            return

        slug = name.lower().replace(" ", "-").replace("/", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        raffle_id = f"{slug}-{int(time.time())}"

        raffle = {
            "id": raffle_id,
            "name": name,
            "participants": json.dumps(participants),
            "number_of_winners": number_of_winners,
            "created_at": int(time.time() * 1000),
        }

        try:
            req = urllib.request.Request(
                f"{supabase_url}/rest/v1/sorteos",
                data=json.dumps(raffle).encode(),
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                method="POST",
            )
            urllib.request.urlopen(req)

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
