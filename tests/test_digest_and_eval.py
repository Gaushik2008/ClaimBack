from claimback.awards.digest import build_digest
from claimback.eval.bench import metrics, model_input, split
from claimback.eval.baselines import CentreOnly, TfidfKNN
from claimback.eval.llm import ClaimBackLLM, build_prompt, parse_reply, verify_citations

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
