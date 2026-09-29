from http.server import BaseHTTPRequestHandler
import json
import os
import time
import base64
import urllib.request


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

        blob_token = get_blob_token()
        if not blob_token:
            self._send_error(500, "No se pudo obtener el token de autenticacion")
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
            store_url = get_store_url()
            put_data = json.dumps(raffle).encode()
            req = urllib.request.Request(
                f"{store_url}/raffles/{raffle_id}.json",
                data=put_data,
                headers={
                    "Authorization": f"Bearer {blob_token}",
                    "Content-Type": "application/json",
                    "x-api-blob-access": "public"
                },
                method="PUT"
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
