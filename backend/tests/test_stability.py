import asyncio
import os
from types import SimpleNamespace

os.environ.setdefault("GROQ_API_KEY", "test-key")

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.data_pipeline.fetchers import bitcoin_fetcher
from backend.app.main import app
from backend.app.schemas.market import BitcoinMarketData
from backend.app.services import llm_service

client = TestClient(app)

SAMPLE = BitcoinMarketData(
    symbol="BTC",
    price_usd=65000.0,
    price_inr=5400000.0,
    change_24h_percent=1.25,
    volume_24h_usd=25000000000.0,
    market_cap_usd=1280000000000.0,
)

GOOD_PAYLOAD = {
    "bitcoin": {
        "usd": 65000,
        "inr": 5400000,
        "usd_24h_change": 1.25,
        "usd_24h_vol": 2.5e10,
        "usd_market_cap": 1.28e12,
    }
}


REAL_ASYNC_CLIENT = httpx.AsyncClient


def _patch_http(monkeypatch, handler):
    real = REAL_ASYNC_CLIENT
    monkeypatch.setattr(
        bitcoin_fetcher.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )


def test_health_and_root():
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/").json()["status"] == "running"


def test_price_endpoint_ok_and_503(monkeypatch):
    async def ok():
        return SAMPLE

    monkeypatch.setattr(main_module, "get_bitcoin_price", ok)
    r = client.get("/api/v1/market/bitcoin/price")
    assert r.status_code == 200 and r.json()["price_usd"] == 65000.0

    async def fail():
        raise RuntimeError("down")

    monkeypatch.setattr(main_module, "get_bitcoin_price", fail)
    assert client.get("/api/v1/market/bitcoin/price").status_code == 503


def test_ask_returns_502_when_llm_fails(monkeypatch):
    async def price():
        return SAMPLE

    async def boom(question, market_data):
        raise RuntimeError("secret provider detail")

    monkeypatch.setattr(main_module, "get_bitcoin_price", price)
    monkeypatch.setattr(main_module, "answer_bitcoin_question", boom)
    r = client.post("/api/v1/bitcoin/ask", json={"question": "Is BTC up today?"})
    assert r.status_code == 502
    assert "secret" not in r.text


@pytest.mark.parametrize("q", ["   ", "  hi  ", ""])
def test_ask_rejects_blank_or_too_short_after_strip(q):
    assert client.post("/api/v1/bitcoin/ask", json={"question": q}).status_code == 422


def test_ask_rejects_too_long_question():
    r = client.post("/api/v1/bitcoin/ask", json={"question": "x" * 1001})
    assert r.status_code == 422


def test_fetcher_success(monkeypatch):
    _patch_http(monkeypatch, lambda req: httpx.Response(200, json=GOOD_PAYLOAD))
    assert asyncio.run(bitcoin_fetcher.get_bitcoin_price()).price_usd == 65000.0


@pytest.mark.parametrize(
    "handler,msg",
    [
        (lambda req: httpx.Response(429, json={}), "HTTP 429"),
        (lambda req: httpx.Response(200, json={"bitcoin": {"usd": 1}}), "Invalid"),
        (lambda req: httpx.Response(200, json={"bitcoin": {**GOOD_PAYLOAD["bitcoin"], "usd_24h_change": None}}), "Invalid"),
        (lambda req: httpx.Response(200, content=b"not json"), "Invalid"),
        (lambda req: httpx.Response(200, json=[]), "Invalid"),
    ],
)
def test_fetcher_errors_map_to_runtime_error(monkeypatch, handler, msg):
    _patch_http(monkeypatch, handler)
    with pytest.raises(RuntimeError, match=msg):
        asyncio.run(bitcoin_fetcher.get_bitcoin_price())


def test_fetcher_timeout_and_connect_errors(monkeypatch):
    def timeout(req):
        raise httpx.ReadTimeout("t", request=req)

    def conn(req):
        raise httpx.ConnectError("c", request=req)

    _patch_http(monkeypatch, timeout)
    with pytest.raises(RuntimeError, match="timed out"):
        asyncio.run(bitcoin_fetcher.get_bitcoin_price())
    _patch_http(monkeypatch, conn)
    with pytest.raises(RuntimeError, match="Unable to connect"):
        asyncio.run(bitcoin_fetcher.get_bitcoin_price())


class _FakeClient:
    def __init__(self, result=None, exc=None):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._result, self._exc = result, exc

    async def _create(self, **kwargs):
        if self._exc:
            raise self._exc
        return self._result


def _resp(content):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.mark.parametrize(
    "client_obj",
    [
        _FakeClient(exc=ValueError("api down")),
        _FakeClient(result=_resp("   ")),
        _FakeClient(result=_resp(None)),
        _FakeClient(result=SimpleNamespace(choices=[])),
    ],
)
def test_llm_failures_raise_runtime_error(monkeypatch, client_obj):
    monkeypatch.setattr(llm_service, "_client", client_obj)
    with pytest.raises(RuntimeError):
        asyncio.run(llm_service.answer_bitcoin_question("What is BTC?", SAMPLE))


def test_llm_success_strips(monkeypatch):
    monkeypatch.setattr(llm_service, "_client", _FakeClient(result=_resp("  hello  ")))
    assert asyncio.run(llm_service.answer_bitcoin_question("What is BTC?", SAMPLE)) == "hello"


@pytest.mark.parametrize("content", [123, ["x"], {"a": 1}, True, b"bytes"])
def test_llm_non_string_content_raises_runtime_error(monkeypatch, content):
    monkeypatch.setattr(llm_service, "_client", _FakeClient(result=_resp(content)))
    with pytest.raises(RuntimeError):
        asyncio.run(llm_service.answer_bitcoin_question("What is BTC?", SAMPLE))


def test_non_string_llm_content_returns_502_not_500(monkeypatch):
    async def price():
        return SAMPLE

    monkeypatch.setattr(main_module, "get_bitcoin_price", price)
    monkeypatch.setattr(llm_service, "_client", _FakeClient(result=_resp(["x"])))
    r = client.post("/api/v1/bitcoin/ask", json={"question": "Is BTC up today?"})
    assert r.status_code == 502


def test_question_length_boundaries(monkeypatch):
    async def price():
        return SAMPLE

    async def ok(question, market_data):
        return "fine"

    monkeypatch.setattr(main_module, "get_bitcoin_price", price)
    monkeypatch.setattr(main_module, "answer_bitcoin_question", ok)
    for q, code in [("x" * 2, 422), ("x" * 3, 200), ("x" * 1000, 200), ("x" * 1001, 422)]:
        r = client.post("/api/v1/bitcoin/ask", json={"question": q})
        assert r.status_code == code, (len(q), r.status_code)
    # whitespace is stripped before the length check
    assert client.post("/api/v1/bitcoin/ask", json={"question": " " * 5 + "x" * 1000 + " " * 5}).status_code == 200
