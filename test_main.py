import httpx
from fastapi.testclient import TestClient

import main
from conftest import TEST_BFF_SECRET
from main import app

client = TestClient(app, headers={'x-bff-secret': TEST_BFF_SECRET})


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

    created = create_note_response.json()
    assert set(created) == {"id", "title", "body"}
    assert created["id"]
    assert created["body"] == ""


def test_create_note_with_body():
    test_note = {"title": "Has a body", "body": "some detail"}

    response = client.post('/notes', json=test_note)

    assert response.status_code == 200
    assert response.json()["body"] == "some detail"


def test_create_note_rejects_empty_title():
    assert client.post('/notes', json={"title": ""}).status_code == 422
    assert client.post('/notes', json={"body": "no title"}).status_code == 422


def test_create_note_rejects_oversized_fields():
    assert client.post('/notes', json={"title": "x" * 201}).status_code == 422
    assert (
        client.post('/notes', json={"title": "ok", "body": "x" * 2001}).status_code
        == 422
    )


def test_create_note_rejects_missing_secret():
    anon_client = TestClient(app)

    response = anon_client.post('/notes', json={"title": "no secret"})

    assert response.status_code == 401


def test_create_note_rejects_wrong_secret():
    response = client.post(
        '/notes', json={"title": "wrong secret"}, headers={'x-bff-secret': 'nope'}
    )

    assert response.status_code == 401


def _fake_gemini_post(payload=None, status_code=200):
    async def fake_post(self, url, **kwargs):
        return FakeResponse(status_code=status_code, payload=payload)

    return fake_post


def _candidate(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_ask_returns_answer(monkeypatch):
    monkeypatch.setattr(
        main.AsyncClient, "post", _fake_gemini_post(_candidate("Dentist is Tuesday."))
    )

    response = client.post('/ask', json={"question": "When is the dentist?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "Dentist is Tuesday."}


def test_ask_answer_not_in_notes(monkeypatch):
    monkeypatch.setattr(
        main.AsyncClient, "post", _fake_gemini_post(_candidate("I don't know."))
    )

    response = client.post('/ask', json={"question": "What's the capital of Peru?"})

    assert response.status_code == 200
    assert response.json() == {"answer": "I don't know."}


def test_ask_upstream_error(monkeypatch):
    monkeypatch.setattr(main.AsyncClient, "post", _fake_gemini_post(status_code=500))

    response = client.post('/ask', json={"question": "hi"})

    assert response.status_code == 200
    assert response.json() == {"error": "llm api failure"}


def test_ask_unreachable(monkeypatch):
    async def fake_post(self, url, **kwargs):
        raise httpx.RequestError("simulated network failure")

    monkeypatch.setattr(main.AsyncClient, "post", fake_post)

    response = client.post('/ask', json={"question": "hi"})

    assert response.status_code == 200
    assert response.json() == {"error": "cannot reach llm api"}


def test_ask_safety_blocked(monkeypatch):
    monkeypatch.setattr(
        main.AsyncClient,
        "post",
        _fake_gemini_post({"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []}),
    )

    response = client.post('/ask', json={"question": "hi"})

    assert response.status_code == 200
    assert response.json() == {"error": "no answer produced"}


def test_ask_rejects_long_question():
    response = client.post('/ask', json={"question": "x" * 501})

    assert response.status_code == 422


def test_ask_is_rate_limited(monkeypatch):
    monkeypatch.setattr(
        main.AsyncClient, "post", _fake_gemini_post(_candidate("ok"))
    )
    main.limiter.enabled = True

    statuses = [
        client.post('/ask', json={"question": "hi"}).status_code for _ in range(11)
    ]

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429


def test_ask_rate_limit_is_scoped_per_bff_user(monkeypatch):
    monkeypatch.setattr(main.AsyncClient, "post", _fake_gemini_post(_candidate("ok")))
    main.limiter.enabled = True

    def ask_as(user_id):
        return client.post(
            '/ask', json={"question": "hi"}, headers={"x-bff-user-id": user_id}
        ).status_code

    statuses = [ask_as("user-a") for _ in range(11)]
    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429

    # a different forwarded end user has an independent budget
    assert ask_as("user-b") == 200
