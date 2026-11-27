"""Vercel Serverless Function entrypoint for ClaimBack."""
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

# Ensure src/ is in sys.path
SRC_DIR = Path(__file__).parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from claimback.pipeline import analyze_claim
from claimback.letters import generate_grievance_letter, generate_ombudsman_complaint


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/api/health", "/health"):
            self._send_json(200, {"status": "ok", "app": "ClaimBack", "deployed_on": "Vercel"})
            return
        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))

        if content_length > 10 * 1024 * 1024:
            self._send_json(413, {"error": "Payload exceeds 10MB limit."})
            return

        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON format."})
            return

        if parsed.path == "/api/analyze":
            res = analyze_claim(
                rejection_text=req_data.get("rejection_text", ""),
                policy_text=req_data.get("policy_text", ""),
                discharge_summary=req_data.get("discharge_summary", ""),
                policy_start_date=req_data.get("policy_start_date"),
                admission_date=req_data.get("admission_date"),
                is_accident=bool(req_data.get("is_accident", False)),
                continuous_coverage_years=float(req_data.get("continuous_coverage_years", 0.0)),
            )
            self._send_json(200, res)
            return

        if parsed.path == "/api/letter":
            case_summary = req_data.get("case_summary", {})
            user_inputs = req_data.get("user_inputs", {})
            self._send_json(200, {
                "grievance": generate_grievance_letter(case_summary, user_inputs),
                "ombudsman": generate_ombudsman_complaint(case_summary, user_inputs),
            })
            return

        self.send_error(404, "Endpoint not found")
