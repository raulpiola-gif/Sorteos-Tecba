from http.server import BaseHTTPRequestHandler
import json
import os
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
    def do_GET(self):
        if self.path != "/api/list":
            self.send_response(404)
            self.end_headers()
            return

        blob_token = get_blob_token()
        if not blob_token:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": []}).encode())
            return

        try:
            store_url = get_store_url()
            req = urllib.request.Request(
                f"{store_url}/?prefix=raffles/",
                headers={
                    "Authorization": f"Bearer {blob_token}",
                },
                method="HEAD"
            )
            resp = urllib.request.urlopen(req)
            files = json.loads(resp.read()) if resp.read() else []
        except Exception:
            files = []

        raffles = []
        for f in files:
            try:
                pathname = f.get("pathname", "")
                if not pathname.endswith(".json"):
                    continue
                req2 = urllib.request.Request(
                    f"{store_url}/{pathname}",
                    headers={"Authorization": f"Bearer {blob_token}"},
                    method="GET"
                )
                resp2 = urllib.request.urlopen(req2)
                r = json.loads(resp2.read())
                raffles.append({
                    "id": r["id"],
                    "name": r["name"],
                    "participantCount": len(r["participants"]),
                    "numberOfWinners": r.get("numberOfWinners", 1),
                    "createdAt": r.get("createdAt", 0),
                })
            except Exception:
                continue

        raffles.sort(key=lambda x: x["createdAt"], reverse=True)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"raffles": raffles}).encode())
