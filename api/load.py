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

        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")

        if not kv_url or not kv_token:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"Base de datos no configurada")
            return

        try:
            req = urllib.request.Request(
                f"{kv_url}/get/raffle:{raffle_id}",
                headers={"Authorization": f"Bearer {kv_token}"},
            )
            resp = urllib.request.urlopen(req)
            raffle = json.loads(resp.read())

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
