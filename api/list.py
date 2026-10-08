from http.server import BaseHTTPRequestHandler
import json
import os

import redis

INDEX_KEY = "sorteos:index"


def _r():
    url = os.environ.get("REDIS_URL", "")
    if not url:
        return None
    return redis.Redis.from_url(url, decode_responses=True, socket_timeout=10)


def _read_index(r):
    raw = r.get(INDEX_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return data if isinstance(data, list) else []


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/list":
            self.send_response(404)
            self.end_headers()
            return

        r = _r()
        if r is None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": []}).encode())
            return

        try:
            raffles = _read_index(r)

            summaries = []
            for item in raffles:
                participants = item.get("participants", [])
                summaries.append({
                    "id": item["id"],
                    "name": item["name"],
                    "participantCount": len(participants),
                    "numberOfWinners": item.get("numberOfWinners", 1),
                    "createdAt": item.get("createdAt", 0),
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
