import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from sentry_adapter.api.auth import AuthMiddleware
from sentry_adapter.api.context import get_auth
from sentry_adapter.config import AuthKeyConfig


def _make_app(key_index: dict) -> Starlette:
    async def endpoint(request: Request) -> PlainTextResponse:
        auth = get_auth()
        return PlainTextResponse(f"{auth.key_id}:{auth.user_id}")

    app = Starlette(routes=[Route("/test", endpoint)])
    app.add_middleware(AuthMiddleware, key_index=key_index)
    return app


def test_valid_key_passes():
    key_index = {
        "sk-abc": AuthKeyConfig(id="k1", key="sk-abc", user_id="alice", team_id="eng")
    }
    client = TestClient(_make_app(key_index), raise_server_exceptions=True)
    r = client.get("/test", headers={"X-API-Key": "sk-abc"})
    assert r.status_code == 200
    assert r.text == "k1:alice"


def test_missing_key_returns_401():
    client = TestClient(_make_app({}), raise_server_exceptions=False)
    r = client.get("/test")
    assert r.status_code == 401
    assert r.json() == {"error": "unauthorized"}


def test_wrong_key_returns_401():
    key_index = {
        "sk-abc": AuthKeyConfig(id="k1", key="sk-abc", user_id="alice", team_id="eng")
    }
    client = TestClient(_make_app(key_index), raise_server_exceptions=False)
    r = client.get("/test", headers={"X-API-Key": "sk-wrong"})
    assert r.status_code == 401


def test_key_with_null_user():
    key_index = {
        "sk-anon": AuthKeyConfig(id="k2", key="sk-anon", user_id=None, team_id=None)
    }
    tc = TestClient(_make_app(key_index), raise_server_exceptions=True)
    r = tc.get("/test", headers={"X-API-Key": "sk-anon"})
    assert r.status_code == 200
    assert r.text == "k2:None"
