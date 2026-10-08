from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.parse
import urllib.request

BLOB_API = "https://vercel.com/api/blob"
BLOB_VERSION = "12"
INDEX_PATH = "sorteos/index.json"


def _blob_store_id():
    sid = os.environ.get("BLOB_STORE_ID", "")
    if sid.startswith("store_"):
        sid = sid[len("store_"):]
    if sid:
        return sid
    rw = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    parts = rw.split("_")
    if len(parts) >= 4:
        return parts[3]
    return ""


def _blob_configured():
    oidc = os.environ.get("VERCEL_OIDC_TOKEN", "")
    rw = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    return bool((oidc and _blob_store_id()) or rw)


def _blob_headers(extra=None):
    headers = {"x-api-version": BLOB_VERSION}
    oidc = os.environ.get("VERCEL_OIDC_TOKEN", "")
    rw = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
    if oidc and _blob_store_id():
        headers["authorization"] = f"Bearer {oidc}"
    elif rw:
        headers["authorization"] = f"Bearer {rw}"
    sid = _blob_store_id()
    if sid:
        headers["x-vercel-blob-store-id"] = sid
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

        if not _blob_configured():
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": "Blob no configurado"}).encode())
            return

        try:
            raffles = _blob_read_index()
            raffles = [r for r in raffles if r.get("id") != raffle_id]
            _blob_write_index(raffles)

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
