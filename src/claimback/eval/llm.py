"""ClaimBack LLM predictor: retrieved precedents + structured verdict + citation check.

NOT YET RUN against a live model (no API key was available when this was written).
Set ANTHROPIC_API_KEY and ANTHROPIC_MODEL, then: python -m claimback.eval.llm --chennai
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


def call_anthropic(prompt: str, model: str | None = None) -> str:
    key = os.environ["ANTHROPIC_API_KEY"]
    body = json.dumps({"model": model or os.environ["ANTHROPIC_MODEL"], "max_tokens": 700,
                       "system": SYSTEM, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
                                 {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["content"][0]["text"]


class ClaimBackLLM:
    name = "claimback_llm_rag"

    def __init__(self, k: int = 5, client=call_anthropic):
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
