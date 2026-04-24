"""
Unit tests for the admin model-metrics endpoint and its DB query layer.
No real DB needed — asyncpg connection is mocked.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


def _admin_token() -> str:
    from jose import jwt
    from app.core.config import settings
    return jwt.encode(
        {"sub": str(uuid4()), "role": "site_admin", "aud": ["fastapi-users:auth"]},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


class TestGetModelMetricsKpis:
    """Test the raw SQL query helper."""

    @pytest.mark.asyncio
    async def test_returns_zeros_when_no_data(self):
        from app.modules.admin.queries import get_model_metrics_kpis

        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "total_analyses": 0,
            "total_llm_calls": 0,
            "total_errors": 0,
            "error_rate": 0,
            "fallback_rate": 0,
            "avg_latency_ms": None,
            "min_latency_ms": None,
            "max_latency_ms": None,
            "mode_llm": 0,
        })

        result = await get_model_metrics_kpis(mock_conn, days=30)

        assert result["total_analyses"] == 0
        assert result["total_llm_calls"] == 0
        assert result["error_rate"] == 0.0
        assert result["fallback_rate"] == 0.0
        assert result["avg_latency_ms"] is None

    @pytest.mark.asyncio
    async def test_returns_correct_values(self):
        from app.modules.admin.queries import get_model_metrics_kpis

        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "total_analyses": 10,
            "total_llm_calls": 80,
            "total_errors": 4,
            "error_rate": 5.0,
            "fallback_rate": 20.0,
            "avg_latency_ms": 234.5,
            "min_latency_ms": 100.0,
            "max_latency_ms": 890.0,
            "mode_llm": 10,
        })

        result = await get_model_metrics_kpis(mock_conn, days=7)

        assert result["total_analyses"] == 10
        assert result["total_llm_calls"] == 80
        assert result["error_rate"] == pytest.approx(5.0)
        assert result["fallback_rate"] == pytest.approx(20.0)
        assert result["avg_latency_ms"] == pytest.approx(234.5)
        assert result["mode_llm"] == 10


class TestInsertModelMetric:
    """Test the repository insert function."""

    @pytest.mark.asyncio
    async def test_executes_insert_with_correct_params(self):
        from app.db.repository import insert_model_metric

        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        data = {
            "analysis_mode": "llm",
            "total_sentences": 5,
            "llm_calls": 4,
            "llm_successes": 3,
            "llm_errors": 1,
            "llm_timeouts": 1,
            "circuit_breaker_trips": 0,
            "avg_latency_ms": 150.0,
            "min_latency_ms": 100.0,
            "max_latency_ms": 200.0,
            "total_runtime_ms": 800,
        }

        await insert_model_metric(mock_conn, data)

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        # First arg is the SQL string
        assert "INSERT INTO model_metrics" in call_args[0]
        # Positional params match our data values
        assert "llm" in call_args
        assert 5 in call_args
        assert 4 in call_args

    @pytest.mark.asyncio
    async def test_handles_none_latency_values(self):
        from app.db.repository import insert_model_metric

        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        data = {
            "analysis_mode": "llm",
            "total_sentences": 3,
            "llm_calls": 0,
            "llm_successes": 0,
            "llm_errors": 0,
            "llm_timeouts": 0,
            "circuit_breaker_trips": 0,
            "avg_latency_ms": None,
            "min_latency_ms": None,
            "max_latency_ms": None,
            "total_runtime_ms": 10,
        }

        # Should not raise
        await insert_model_metric(mock_conn, data)
        mock_conn.execute.assert_called_once()


class TestAdminModelMetricsEndpoint:
    """Test the HTTP endpoint via test client."""

    @pytest.mark.asyncio
    async def test_endpoint_requires_admin(self, test_client):
        response = await test_client.get("/api/v1/admin/model-metrics")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_endpoint_returns_schema(self, test_client, mock_pool):
        """Admin token returns valid ModelMetricsResponse shape."""
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={
            "total_analyses": 5,
            "total_llm_calls": 40,
            "total_errors": 2,
            "error_rate": 5.0,
            "fallback_rate": 0.0,
            "avg_latency_ms": 200.0,
            "min_latency_ms": 100.0,
            "max_latency_ms": 300.0,
            "mode_llm": 5,
        })
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = ctx

        response = await test_client.get(
            "/api/v1/admin/model-metrics",
            headers={"Authorization": f"Bearer {_admin_token()}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "total_analyses" in body
        assert "error_rate" in body
        assert "fallback_rate" in body
        assert "avg_latency_ms" in body
        assert "mode_llm" in body
