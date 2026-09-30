from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        supabase_url = os.environ.get("SUPABASE_URL", "")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")

        result = {
            "url_set": bool(supabase_url),
            "key_set": bool(supabase_key),
            "url_preview": supabase_url[:30] + "..." if supabase_url else "MISSING",
            "key_preview": supabase_key[:20] + "..." if supabase_key else "MISSING",
        }

        if supabase_url and supabase_key:
            try:
                req = urllib.request.Request(
                    f"{supabase_url}/rest/v1/sorteos?select=count&limit=1",
                    headers={
                        "apikey": supabase_key,
                        "Authorization": f"Bearer {supabase_key}",
                        "Prefer": "count=exact",
                    },
                )
                resp = urllib.request.urlopen(req)
                result["db_status"] = "OK"
                result["response_code"] = resp.status
            except urllib.error.HTTPError as e:
                result["db_status"] = "ERROR"
                result["error_code"] = e.code
                result["error_body"] = e.read().decode()[:500]
            except Exception as e:
                result["db_status"] = "ERROR"
                result["error"] = str(e)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode())
