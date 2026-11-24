"""Lightweight ClaimBack standalone web server using Python's standard library.

Provides:
- GET / : Static responsive web UI
- GET /health : Health status check
- POST /api/analyze : Core analysis pipeline (PII masking, date rules, clause check, precedents)
- POST /api/letter : Generates Grievance Officer and Insurance Ombudsman appeal letters
"""
from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from claimback.pipeline import analyze_claim
from claimback.letters import generate_grievance_letter, generate_ombudsman_complaint

STATIC_DIR = Path(__file__).parent / "static"


class ClaimBackHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "app": "ClaimBack", "version": "0.0.1"})
            return

        if parsed.path in ("/", "/index.html"):
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                content = index_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))

        # Size limit (10MB)
        if content_length > 10 * 1024 * 1024:
            self._send_json(413, {"error": "Payload exceeds 10MB limit."})
            return

        body = self.rfile.read(content_length).decode("utf-8")
        try:
            req_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON format."})
            return

        if parsed.path == "/api/analyze":
            rejection_text = req_data.get("rejection_text", "")
            policy_text = req_data.get("policy_text", "")
            discharge_summary = req_data.get("discharge_summary", "")
            policy_start_date = req_data.get("policy_start_date")
            admission_date = req_data.get("admission_date")
            is_accident = bool(req_data.get("is_accident", False))
            continuity_years = float(req_data.get("continuous_coverage_years", 0.0))

            res = analyze_claim(
                rejection_text=rejection_text,
                policy_text=policy_text,
                discharge_summary=discharge_summary,
                policy_start_date=policy_start_date,
                admission_date=admission_date,
                is_accident=is_accident,
                continuous_coverage_years=continuity_years,
                intake=req_data.get("intake") if isinstance(req_data.get("intake"), dict) else None,
            )
            self._send_json(200, res)
            return

        if parsed.path == "/api/letter":
            case_summary = req_data.get("case_summary", {})
            user_inputs = req_data.get("user_inputs", {})

            gro_letter = generate_grievance_letter(case_summary, user_inputs)
            ombudsman_letter = generate_ombudsman_complaint(case_summary, user_inputs)

            self._send_json(200, {
                "grievance": gro_letter,
                "ombudsman": ombudsman_letter,
            })
            return

        self.send_error(404, "Endpoint not found")


def run_server(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), ClaimBackHandler)
    print(f"ClaimBack web server listening on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
