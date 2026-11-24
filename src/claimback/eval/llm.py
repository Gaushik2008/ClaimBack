"""ClaimBack LLM predictor: retrieved precedents + structured verdict + citation check.

Default backend: NVIDIA Nemotron 3 Ultra via the OpenAI-compatible NIM endpoint.
NOT YET RUN against a live model (no key / no network to NVIDIA in the authoring sandbox).
Run locally: export NVIDIA_API_KEY=...; python -m claimback.eval.run_llm
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from .baselines import TfidfKNN
from .bench import model_input

SYSTEM = (
    "You are an advisory assistant for Indian health-insurance claim disputes. "
    "Decide whether the Insurance Ombudsman would grant the complainant relief. "
    "Use ONLY the case facts and the numbered precedents provided. Cite precedents by their id. "
    "Never invent clauses or cases. If unsure, say so with low confidence. "
    'Reply with JSON only: {"verdict":"allowed"|"dismissed","confidence":0-1,'
    '"ground":"...","reasoning":"...","cited_precedents":["id",...]}'
)


def build_prompt(case: dict, precedents: list[dict]) -> str:
    prec = "\n".join(
        f"[{p['case_id']}] outcome={p['outcome']} | {model_input(p)[:600]}" for p in precedents
    )
    return f"PRECEDENTS:\n{prec}\n\nCASE FACTS:\n{model_input(case)}\n\nGive your JSON verdict."


def parse_reply(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        d = {}
    if d.get("verdict") not in ("allowed", "dismissed"):
        d["verdict"] = None
    return d


def verify_citations(reply: dict, precedents: list[dict]) -> dict:
    """Every cited id must be one of the retrieved precedents. Hallucination rate = invalid / cited."""
    valid = {p["case_id"] for p in precedents}
    cited = [str(x) for x in reply.get("cited_precedents", [])]
    bad = [c for c in cited if c not in valid]
    return {"cited": len(cited), "invalid": len(bad), "invalid_ids": bad}


NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"


def call_nvidia(prompt: str, system: str = SYSTEM, model: str | None = None) -> str:
    """OpenAI-compatible chat call. Reads the key from NVIDIA_API_KEY (never stored in the repo)."""
    body = json.dumps({"model": model or os.environ.get("NVIDIA_MODEL", NVIDIA_MODEL), "temperature": 0,
                       "max_tokens": 1500, "stream": False,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(NVIDIA_URL, body, {"Authorization": f"Bearer {os.environ['NVIDIA_API_KEY']}",
                                                    "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        msg = json.load(r)["choices"][0]["message"]
    return msg.get("content") or ""  # reasoning_content, if any, is ignored


class PlainLLM:
    """Single-prompt baseline: same model, no retrieval, no citation check."""
    name = "plain_llm"

    def __init__(self, client=call_nvidia):
        self.client = client

    def fit(self, train):
        return self

    def predict(self, case):
        p = f"CASE FACTS:\n{model_input(case)}\n\nGive your JSON verdict (cited_precedents must be empty)."
        return parse_reply(self.client(p))["verdict"] or "dismissed"


class ClaimBackLLM:
    name = "claimback_llm_rag"

    def __init__(self, k: int = 5, client=call_nvidia):
        self.k, self.client = k, client
        self.audit: list[dict] = []

    def fit(self, train):
        self.retriever = TfidfKNN(k=self.k).fit(train)
        return self

    def predict(self, case):
        prec = [c for _, c in self.retriever.neighbours(case, self.k)]
        reply = parse_reply(self.client(build_prompt(case, prec)))
        self.audit.append({"case_id": case["case_id"], **verify_citations(reply, prec)})
        return reply["verdict"] or "dismissed"
