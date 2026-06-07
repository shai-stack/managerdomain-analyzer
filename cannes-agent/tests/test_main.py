from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    with patch("main.cal_client", None):
        from main import app
        return TestClient(app)

def test_webhook_returns_twiml(client):
    with patch("main.agent.run", return_value="Here are your adtech events!"):
        with patch("main.validate_twilio_signature", return_value=True):
            resp = client.post(
                "/webhook",
                data={"From": "whatsapp:+972501234567", "Body": "What events are on Tuesday?"},
                headers={"X-Twilio-Signature": "fake"},
            )
    assert resp.status_code == 200
    assert "Here are your adtech events!" in resp.text
    assert "<Response>" in resp.text

def test_webhook_missing_body_returns_422(client):
    with patch("main.validate_twilio_signature", return_value=True):
        resp = client.post("/webhook", data={"From": "whatsapp:+972501234567"})
    assert resp.status_code == 422

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
