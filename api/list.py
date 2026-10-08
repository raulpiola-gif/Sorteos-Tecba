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


def _blob_headers():
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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/list":
            self.send_response(404)
            self.end_headers()
            return

        if not _blob_configured():
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": []}).encode())
            return

        try:
            raffles = _blob_read_index()

            summaries = []
            for r in raffles:
                participants = r.get("participants", [])
                summaries.append({
                    "id": r["id"],
                    "name": r["name"],
                    "participantCount": len(participants),
                    "numberOfWinners": r.get("numberOfWinners", 1),
                    "createdAt": r.get("createdAt", 0),
                })

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": summaries}).encode())

        except Exception as e:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": [], "error": str(e)}).encode())
