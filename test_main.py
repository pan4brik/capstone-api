import httpx
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


class FakeResponse:
    """Stand-in for an httpx.Response, so /rates tests never touch the network."""

    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else []

    def json(self):
        return self._payload


def test_get_health():
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_notes():
    response = client.get('/notes')

    assert response.status_code == 200
    assert type(response.json()) is list


def test_get_exchange_rates(monkeypatch):
    async def fake_get(self, url):
        return FakeResponse(status_code=200, payload=[{"base": "EUR", "rate": 1.0}])

    monkeypatch.setattr(main.AsyncClient, "get", fake_get)

    response = client.get('/rates')

    assert response.status_code == 200
    assert type(response.json()) is list


def test_get_exchange_rates_upstream_error(monkeypatch):
    async def fake_get(self, url):
        return FakeResponse(status_code=500)

    monkeypatch.setattr(main.AsyncClient, "get", fake_get)

    response = client.get('/rates')

    assert response.status_code == 200
    assert response.json() == {"status": "external api failure"}


def test_get_exchange_rates_unreachable(monkeypatch):
    async def fake_get(self, url):
        raise httpx.RequestError("simulated network failure")

    monkeypatch.setattr(main.AsyncClient, "get", fake_get)

    response = client.get('/rates')

    assert response.status_code == 200
    assert response.json() == {"status": "cannot reach external api"}


def test_create_note():
    test_note = {"title": "My test title"}

    create_note_response = client.post('/notes', json=test_note)
    get_notes_response = client.get('/notes')

    assert create_note_response.status_code == 200
    assert get_notes_response.status_code == 200
    assert create_note_response.json() in get_notes_response.json()
