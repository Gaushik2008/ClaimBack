from claimback.awards.digest import build_digest
from claimback.eval.bench import metrics, model_input, split
from claimback.eval.baselines import CentreOnly, TfidfKNN
from claimback.eval.llm import ClaimBackLLM, PlainLLM, build_prompt, parse_reply, verify_citations

SAMPLE = """
                    AHMEDABAD OMBUDSMAN CENTRE

                    Case No.11-004-0628-12

Shri Test Person V/s. United India Insurance Co. Ltd.

Award dated 4th April 2012

Repudiation of Mediclaim

      Complainant's ENT treatment expenses for Rs.35,112/- was rejected by the
Respondent invoking Policy Clause 4.3 i.e. some treatments are excluded for two years.

      In the result complaint fails to succeed without any relief to the complainant.
**********************************************
"""


def test_digest_parses_case_without_name():
    cs = build_digest(SAMPLE)
    assert len(cs) == 1
    c = cs[0]
    assert c.case_id == "11-004-0628-12" and c.centre == "Ahmedabad"
    assert c.insurer.startswith("United India") and c.year == 2012
    assert c.outcome == "dismissed" and 35112.0 in c.amounts and "4.3" in c.clauses
    assert "Test Person" not in str(c.to_dict())


def test_digest_parses_order_and_inline_case_headers():
    raw = """
                  BHOPAL OMBUDSMAN CENTRE

Order No.: BPL/GI/0910/002                         Case No.: GI/RSI /0209/103

Dated 6th May, 2009

Shri Complainant Name & others
                V/s
The Royal Sundaram Alliance Insurance Co. Ltd., Chennai

Brief Background
Hospital cash insurance claim was repudiated under clause 4.1.
The decision of the insurer is justified and complaint dismissed.
**********************************************
CASE NO. GIC/323/NIC/14/09

Manohar Lal Nagpal Vs. National Insurance Co. Ltd.

Order dated 07.11.08
Claim for Rs. 50,000 was repudiated on ground of pre-existing disease.
Hon'ble Ombudsman directed to pay within 30 days.
"""
    cs = build_digest(raw)
    assert len(cs) == 2
    c1 = cs[0]
    assert c1.case_id == "GI/RSI/0209/103"
    assert c1.centre in ("Bhopal", "Delhi")  # recognized centre
    assert "Royal Sundaram" in c1.insurer
    assert c1.year == 2009
    assert c1.outcome == "dismissed"
    assert "Complainant Name" not in str(c1.to_dict())

    c2 = cs[1]
    assert c2.case_id == "GIC/323/NIC/14/09"
    assert c2.centre == "Chandigarh"
    assert "National Insurance" in c2.insurer
    assert c2.year == 2008
    assert c2.outcome == "allowed"
    assert "Manohar Lal" not in str(c2.to_dict())


def _case(i, outcome, centre="Chennai", facts="Claim rejected for pre-existing disease."):
    return {"case_id": str(i), "centre": centre, "outcome": outcome, "facts": facts, "reasoning": ""}


def test_leak_sentences_removed():
    c = _case(1, "dismissed", facts="Claim was rejected. The decision is upheld without any relief.")
    assert "upheld" not in model_input(c)


def test_split_is_deterministic_and_disjoint():
    cs = [_case(i, "allowed" if i % 3 else "dismissed") for i in range(40)]
    a, b = split(cs), split(cs)
    assert a == b
    assert not {c["case_id"] for c in a[0]} & {c["case_id"] for c in a[1]}


def test_metrics_and_baselines():
    m = metrics(["allowed", "dismissed"], ["allowed", "allowed"], n_boot=50)
    assert m["accuracy"] == 0.5 and m["balanced_accuracy"] == 0.5
    tr = [_case(1, "allowed", "Delhi"), _case(2, "dismissed", "Ahmedabad")]
    assert CentreOnly().fit(tr).predict(_case(3, "x", "Delhi")) == "allowed"
    assert TfidfKNN(k=1).fit(tr).predict(_case(4, "x"))


def test_citation_verifier_flags_invented_ids():
    prec = [_case("A", "allowed")]
    r = verify_citations({"cited_precedents": ["A", "ZZZ"]}, prec)
    assert r == {"cited": 2, "invalid": 1, "invalid_ids": ["ZZZ"]}
    assert parse_reply("noise") ["verdict"] is None


def test_llm_wrapper_with_fake_client():
    tr = [_case("A", "allowed"), _case("B", "dismissed", facts="Waiting period applies to hernia.")]
    fake = lambda prompt: '{"verdict":"allowed","cited_precedents":["A","FAKE"]}'
    m = ClaimBackLLM(k=2, client=fake).fit(tr)
    assert m.predict(_case("Q", "x")) == "allowed"
    assert m.audit[0]["invalid"] == 1 and "[A]" in build_prompt(_case("Q", "x"), tr)


def test_plain_llm_with_fake_client():
    assert PlainLLM(client=lambda p: '{"verdict":"dismissed"}').predict(_case("Q", "x")) == "dismissed"
    assert PlainLLM(client=lambda p: "garbled").predict(_case("Q", "x")) == "dismissed"  # fallback
