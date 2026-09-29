from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request


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
                f"{kv_url}/del/raffle:{raffle_id}",
                headers={"Authorization": f"Bearer {kv_token}"},
                method="POST",
            )
            urllib.request.urlopen(req)

            # Remove from index
            try:
                req2 = urllib.request.Request(
                    f"{kv_url}/get/raffle:index",
                    headers={"Authorization": f"Bearer {kv_token}"},
                )
                resp = urllib.request.urlopen(req2)
                index = json.loads(resp.read())
                if raffle_id in index:
                    index.remove(raffle_id)
                    req3 = urllib.request.Request(
                        f"{kv_url}/set/raffle:index",
                        data=json.dumps(index).encode(),
                        headers={
                            "Authorization": f"Bearer {kv_token}",
                            "Content-Type": "application/json",
                        },
                        method="POST",
                    )
                    urllib.request.urlopen(req3)
            except Exception:
                pass

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
