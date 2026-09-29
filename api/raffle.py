from http.server import BaseHTTPRequestHandler
import json
import random


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/raffle":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        participants = data.get("participants", [])
        number_of_winners = data.get("numberOfWinners", 1)

        if not participants:
            self._send_error(400, "Debe haber al menos un participante")
            return
        if number_of_winners <= 0:
            self._send_error(400, "El numero de ganadores debe ser mayor a 0")
            return
        if number_of_winners > len(participants):
            self._send_error(
                400,
                f"No se pueden sortear {number_of_winners} ganadores "
                f"con solo {len(participants)} participantes",
            )
            return

        shuffled = participants[:]
        random.shuffle(shuffled)
        winners = shuffled[:number_of_winners]

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"winners": winners}).encode())

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
