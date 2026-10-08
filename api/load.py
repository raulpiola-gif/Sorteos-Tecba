from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.parse
import urllib.request
from urllib.parse import urlparse, parse_qs

BLOB_API = "https://vercel.com/api/blob"
BLOB_VERSION = "12"
INDEX_PATH = "sorteos/index.json"


def _blob_token():
    return os.environ.get("BLOB_READ_WRITE_TOKEN", "")


def _blob_headers():
    return {
        "authorization": f"Bearer {_blob_token()}",
        "x-api-version": BLOB_VERSION,
    }


def _blob_read_index():
    """Lee sorteos/index.json. Devuelve [] si no existe todavía."""
    list_url = BLOB_API + "?prefix=" + urllib.parse.quote(INDEX_PATH, safe="") + "&limit=1"
    req = urllib.request.Request(list_url, headers=_blob_headers())
    data = json.loads(urllib.request.urlopen(req, timeout=20).read())
    blobs = data.get("blobs", [])
    url = next((b["url"] for b in blobs if b.get("pathname") == INDEX_PATH), None)
    if not url:
        return []
    req2 = urllib.request.Request(url, headers=_blob_headers())
    return json.loads(urllib.request.urlopen(req2, timeout=20).read())


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

        if not _blob_token():
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": "Blob no configurado"}).encode())
            return

        try:
            raffles = _blob_read_index()
            raffle = next((r for r in raffles if r.get("id") == raffle_id), None)

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
