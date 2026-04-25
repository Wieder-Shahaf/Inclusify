"""Tests for admin WebSocket endpoint (D-05)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from jose import jwt
from app.modules.admin.router import AdminWSManager


# JWT config matching project's auth/deps.py
JWT_SECRET = "test-secret"
JWT_ALG = "HS256"
JWT_AUDIENCE = "fastapi-users:auth"


def _make_token(role: str) -> str:
    return jwt.encode(
        {"sub": "user1", "role": role, "aud": JWT_AUDIENCE},
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


@pytest.mark.asyncio
async def test_broadcast_sends_to_all_connections():
    mgr = AdminWSManager()
    ws1 = MagicMock()
    ws1.send_json = AsyncMock()
    ws2 = MagicMock()
    ws2.send_json = AsyncMock()
    mgr.connections.extend([ws1, ws2])
    await mgr.broadcast({"event": "new_analysis"})
    ws1.send_json.assert_awaited_once_with({"event": "new_analysis"})
    ws2.send_json.assert_awaited_once_with({"event": "new_analysis"})


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections():
    mgr = AdminWSManager()
    good = MagicMock()
    good.send_json = AsyncMock()
    bad = MagicMock()
    bad.send_json = AsyncMock(side_effect=RuntimeError("dead"))
    mgr.connections.extend([good, bad])
    await mgr.broadcast({"event": "x"})
    assert good in mgr.connections
    assert bad not in mgr.connections


@pytest.mark.asyncio
async def test_ws_closes_4001_when_token_missing(monkeypatch):
    """WS endpoint closes with 4001 when no token provided."""
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr("app.modules.admin.router.settings", MagicMock(JWT_SECRET=JWT_SECRET))
    client = TestClient(app)
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect("/api/v1/admin/ws"):
            pass
    assert getattr(exc_info.value, "code", None) == 4001 or "4001" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_closes_4001_when_token_invalid(monkeypatch):
    """WS endpoint closes with 4001 when JWT is malformed."""
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr("app.modules.admin.router.settings", MagicMock(JWT_SECRET=JWT_SECRET))
    client = TestClient(app)
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect("/api/v1/admin/ws?token=garbage"):
            pass
    assert getattr(exc_info.value, "code", None) == 4001 or "4001" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_closes_4003_when_non_admin(monkeypatch):
    """WS endpoint closes with 4003 when role is not site_admin."""
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr("app.modules.admin.router.settings", MagicMock(JWT_SECRET=JWT_SECRET))
    token = _make_token("user")
    client = TestClient(app)
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect(f"/api/v1/admin/ws?token={token}"):
            pass
    assert getattr(exc_info.value, "code", None) == 4003 or "4003" in str(exc_info.value)
