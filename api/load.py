from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
from urllib.parse import urlparse, parse_qs


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
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"Se requiere un id")
            return

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")

        if not supabase_url or not supabase_key:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"Supabase no configurado")
            return

        try:
            req = urllib.request.Request(
                f"{supabase_url}/rest/v1/sorteos?id=eq.{raffle_id}&select=*",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                },
            )
            resp = urllib.request.urlopen(req)
            rows = json.loads(resp.read())

            if not rows:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b"Sorteo no encontrado")
                return

            r = rows[0]
            participants = r.get("participants", "[]")
            if isinstance(participants, str):
                participants = json.loads(participants)

            raffle = {
                "id": r["id"],
                "name": r["name"],
                "participants": participants,
                "numberOfWinners": r.get("number_of_winners", 1),
                "createdAt": r.get("created_at", 0),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(raffle).encode())

        except urllib.error.HTTPError:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"Sorteo no encontrado")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
