from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/list":
            self.send_response(404)
            self.end_headers()
            return

        kv_url = os.environ.get("KV_REST_API_URL")
        kv_token = os.environ.get("KV_REST_API_TOKEN")

        if not kv_url or not kv_token:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": []}).encode())
            return

        try:
            req = urllib.request.Request(
                f"{kv_url}/get/raffle:index",
                headers={"Authorization": f"Bearer {kv_token}"},
            )
            resp = urllib.request.urlopen(req)
            index = json.loads(resp.read())
        except Exception:
            index = []

        raffles = []
        for raffle_id in index:
            try:
                req = urllib.request.Request(
                    f"{kv_url}/get/raffle:{raffle_id}",
                    headers={"Authorization": f"Bearer {kv_token}"},
                )
                resp = urllib.request.urlopen(req)
                r = json.loads(resp.read())
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
