from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/debug":
            self.send_response(404)
            self.end_headers()
            return

        info = {
            "VERCEL_OIDC_TOKEN": "SET" if os.environ.get("VERCEL_OIDC_TOKEN") else "MISSING",
            "BLOB_STORE_ID": "SET" if os.environ.get("BLOB_STORE_ID") else "MISSING",
            "BLOB_READ_WRITE_TOKEN": "SET" if os.environ.get("BLOB_READ_WRITE_TOKEN") else "MISSING",
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(info).encode())
