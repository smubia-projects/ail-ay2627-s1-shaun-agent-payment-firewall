"""The public demo API (api.py): offline, no keys. The scripted agent stands in for the LLM agent."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import api
import merchant


@pytest.fixture
def client(monkeypatch):
    for k in ("API_KEY", "LLM_API_KEY", "AGENT_API_KEY", "JUDGE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    return TestClient(api.app)


def test_health_and_overview(client):
    assert client.get("/api/health").json()["status"] == "ok"
    o = client.get("/api/overview").json()
    assert o["modes"] == ["off", "prompt", "on"] and len(o["cases"]) == len(api.CASES)
    assert o["audit"] and all(x["decision"] in ("allow", "block", "step_up") for x in o["audit"])


def test_attack_runs_alone_then_behind_the_firewall(client):
    r = client.post("/api/attack", json={"case_id": "A10-retry-1"}).json()
    alone, guarded = r["runs"]
    assert r["agent"] == "scripted" and not alone["firewall"] and guarded["firewall"]
    assert alone["violations"] and alone["paid"] > guarded["paid"]  # the gullible agent pays twice on its own
    assert not guarded["violations"]
    assert not merchant.LEDGERS and not merchant.CUSTOMS  # per-run ledgers are thrown away


def test_custom_attack_scammer_wallet_is_blocked(client):
    custom = {"merchantId": "researchhub", "payTo": "0x7A3f9c21E4b8D05a6C1e93F2b47d8A0c5E61B9d4", "amount": 0.1,
              "asset": "USDC", "network": "base-sepolia", "description": "Market research report", "page_text": ""}
    alone, guarded = client.post("/api/attack", json={"custom": custom}).json()["runs"]
    assert "paid a wallet that isn't the shop's" in alone["violations"]
    assert guarded["paid"] == 0 and guarded["decisions"][0]["decision"] == "block"


def test_visitors_do_not_share_a_ledger(client):
    """Two attacks at once: each sees only its own payments (the original had one global LEDGER)."""
    with ThreadPoolExecutor(2) as ex:
        a, b = ex.map(lambda cid: client.post("/api/attack", json={"case_id": cid}).json(), ["A10-retry-1", "L-report-1"])
    # the scripted agent pays the fake retry once per step; the genuine purchase is one payment
    assert a["runs"][0]["paid"] == round(0.1 * api.AGENT_MAX_STEPS, 2) and b["runs"][0]["paid"] == 0.1


def test_bad_requests_are_rejected(client):
    assert client.post("/api/attack", json={"case_id": "nope"}).status_code == 400
    bad = {"merchantId": "x", "payTo": "y", "amount": 0, "asset": "USDC", "network": "base-sepolia", "description": "d"}
    assert client.post("/api/attack", json={"custom": bad}).status_code == 422


def test_live_attack_is_rate_limited_before_any_model_call(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "test")

    def limited(request, bucket):
        assert bucket == "attack"
        raise HTTPException(status_code=429, detail={"message": "Rate limit exceeded.", "queries_used": 3})

    def never(*a, **k):
        raise AssertionError("agent ran after a 429")

    monkeypatch.setattr(api, "check_rate_limit", limited)
    monkeypatch.setattr(api, "_run_once", never)
    r = client.post("/api/attack", json={"case_id": "A10-retry-1"})
    assert r.status_code == 429 and r.json()["detail"]["queries_used"] == 3
