import os

# Settings are loaded when the application modules are imported.
os.environ.setdefault("GROQ_API_KEY", "test-key")

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.market import BitcoinMarketData
from backend.app import main as main_module


client = TestClient(app)

SAMPLE_MARKET_DATA = BitcoinMarketData(
    symbol="BTC",
    price_usd=65000.0,
    price_inr=5400000.0,
    change_24h_percent=1.25,
    volume_24h_usd=25000000000.0,
    market_cap_usd=1280000000000.0,
)


def test_ask_bitcoin_returns_answer_and_market_snapshot(monkeypatch):
    async def fake_get_bitcoin_price():
        return SAMPLE_MARKET_DATA

    async def fake_answer_bitcoin_question(question, market_data):
        assert question == "What is Bitcoin's current price?"
        assert market_data == SAMPLE_MARKET_DATA
        return "Bitcoin is currently quoted at $65,000 in this test snapshot."

    monkeypatch.setattr(main_module, "get_bitcoin_price", fake_get_bitcoin_price)
    monkeypatch.setattr(
        main_module,
        "answer_bitcoin_question",
        fake_answer_bitcoin_question,
    )

    response = client.post(
        "/api/v1/bitcoin/ask",
        json={"question": "What is Bitcoin's current price?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "What is Bitcoin's current price?"
    assert "$65,000" in body["answer"]
    assert body["market_data"]["price_usd"] == 65000.0


def test_ask_bitcoin_rejects_short_question():
    response = client.post(
        "/api/v1/bitcoin/ask",
        json={"question": "hi"},
    )

    assert response.status_code == 422


def test_ask_bitcoin_returns_503_when_market_data_unavailable(monkeypatch):
    async def fake_get_bitcoin_price():
        raise RuntimeError("Bitcoin market API request timed out")

    monkeypatch.setattr(main_module, "get_bitcoin_price", fake_get_bitcoin_price)

    response = client.post(
        "/api/v1/bitcoin/ask",
        json={"question": "Explain Bitcoin's latest market movement"},
    )

    assert response.status_code == 503
