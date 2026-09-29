from http.server import BaseHTTPRequestHandler
import json
import os
import base64
import urllib.request
from urllib.parse import urlparse, parse_qs


def get_blob_token():
    oidc_token = os.environ.get("VERCEL_OIDC_TOKEN")
    if not oidc_token:
        return None
    creds = base64.b64encode(b"vercel-blob:").decode()
    data = json.dumps({
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": oidc_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
        "audience": "https://blob.vercel-storage.com"
    }).encode()
    req = urllib.request.Request(
        "https://api.vercel.com/v2/oauth/token",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {creds}"
        },
        method="POST"
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read()).get("access_token")


def get_store_url():
    store_id = os.environ.get("BLOB_STORE_ID", "")
    return f"https://{store_id}.blob.vercel-storage.com"


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

        blob_token = get_blob_token()
        if not blob_token:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"No se pudo obtener el token")
            return

        try:
            store_url = get_store_url()
            req = urllib.request.Request(
                f"{store_url}/raffles/{raffle_id}.json",
                headers={"Authorization": f"Bearer {blob_token}"},
                method="GET"
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
