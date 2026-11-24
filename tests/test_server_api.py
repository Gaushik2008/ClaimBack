import threading
import time
import urllib.request
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.server import run_server

_server_started = False

def start_server_once(port=8099):
    global _server_started
    if not _server_started:
        t = threading.Thread(target=run_server, args=(port,), daemon=True)
        t.start()
        time.sleep(0.5)
        _server_started = True


def test_api_health():
    start_server_once(8099)
    with urllib.request.urlopen("http://127.0.0.1:8099/health") as r:
        data = json.loads(r.read())
        assert data["status"] == "ok"
        assert data["app"] == "ClaimBack"


def test_api_analyze_and_letter():
    start_server_once(8099)
    analyze_req = urllib.request.Request(
        "http://127.0.0.1:8099/api/analyze",
        data=json.dumps({
            "rejection_text": "Claim repudiated under clause 4.1 for waiting period.",
            "policy_text": "Clause 4.1 Waiting Period: 30 days.",
            "policy_start_date": "2023-01-01",
            "admission_date": "2023-01-10",
            "is_accident": False
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(analyze_req) as r:
        res = json.loads(r.read())
        assert res["verdict"] in ("insurer_likely_right", "weak_appeal", "strong_appeal")
        assert res["clause_verified"] is True
        assert "disclaimer" in res

    letter_req = urllib.request.Request(
        "http://127.0.0.1:8099/api/letter",
        data=json.dumps({
            "case_summary": res,
            "user_inputs": {"complainant_name": "Test User"}
        }).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(letter_req) as r:
        letters = json.loads(r.read())
        assert "grievance" in letters
        assert "ombudsman" in letters
        assert "Test User" in letters["grievance"]
