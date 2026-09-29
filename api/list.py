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

        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY")

        if not supabase_url or not supabase_key:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": []}).encode())
            return

        try:
            req = urllib.request.Request(
                f"{supabase_url}/rest/v1/sorteos?select=id,name,participants,number_of_winners,created_at&order=created_at.desc",
                headers={
                    "apikey": supabase_key,
                    "Authorization": f"Bearer {supabase_key}",
                },
            )
            resp = urllib.request.urlopen(req)
            rows = json.loads(resp.read())

            raffles = []
            for r in rows:
                participants = r.get("participants", "[]")
                if isinstance(participants, str):
                    participants = json.loads(participants)
                raffles.append({
                    "id": r["id"],
                    "name": r["name"],
                    "participantCount": len(participants),
                    "numberOfWinners": r.get("number_of_winners", 1),
                    "createdAt": r.get("created_at", 0),
                })

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": raffles}).encode())

        except Exception as e:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"raffles": [], "error": str(e)}).encode())
