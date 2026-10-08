from http.server import BaseHTTPRequestHandler
import json
import os
import time
import urllib.parse
import urllib.request

BLOB_API = "https://vercel.com/api/blob"
BLOB_VERSION = "12"
INDEX_PATH = "sorteos/index.json"


def _blob_token():
    return os.environ.get("BLOB_READ_WRITE_TOKEN", "")


def _blob_headers(extra=None):
    headers = {
        "authorization": f"Bearer {_blob_token()}",
        "x-api-version": BLOB_VERSION,
    }
    if extra:
        headers.update(extra)
    return headers


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


def _blob_write_index(raffles):
    raw = json.dumps(raffles).encode()
    put_url = BLOB_API + "/?pathname=" + urllib.parse.quote(INDEX_PATH, safe="")
    req = urllib.request.Request(
        put_url,
        data=raw,
        method="PUT",
        headers=_blob_headers({
            "x-vercel-blob-access": "private",
            "x-content-type": "application/json",
            "x-allow-overwrite": "1",
            "x-add-random-suffix": "0",
        }),
    )
    urllib.request.urlopen(req, timeout=20).read()


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

        if not _blob_token():
            self._send_error(500, "Blob no configurado (falta BLOB_READ_WRITE_TOKEN)")
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
            raffles = _blob_read_index()
            raffles.insert(0, raffle)
            _blob_write_index(raffles)

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
