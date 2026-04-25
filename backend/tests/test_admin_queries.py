"""Tests for admin.queries.get_label_frequency_trends (D-05)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from app.modules.admin.queries import get_label_frequency_trends


def _mock_conn(rows):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows)
    return conn


@pytest.mark.asyncio
async def test_frequency_trends_empty():
    conn = _mock_conn([])
    result = await get_label_frequency_trends(conn, days=30)
    assert result == []


@pytest.mark.asyncio
async def test_frequency_trends_shape():
    rows = [
        {"category": "Biased", "total_count": 3, "all_excerpts": ["x", "x", "y"]},
        {"category": "Outdated Terminology", "total_count": 1, "all_excerpts": ["z"]},
    ]
    conn = _mock_conn(rows)
    result = await get_label_frequency_trends(conn, days=30)
    assert len(result) == 2
    assert result[0]["category"] == "Biased"
    assert result[0]["count"] == 3
    assert {"phrase": "x", "count": 2} in result[0]["top_phrases"]
    assert {"phrase": "y", "count": 1} in result[0]["top_phrases"]


@pytest.mark.asyncio
async def test_top_phrases_limited_to_five_and_sorted():
    excerpts = ["a"] * 5 + ["b"] * 4 + ["c"] * 3 + ["d"] * 2 + ["e"] * 1 + ["f"] * 1
    rows = [{"category": "Biased", "total_count": len(excerpts), "all_excerpts": excerpts}]
    conn = _mock_conn(rows)
    result = await get_label_frequency_trends(conn, days=30)
    top = result[0]["top_phrases"]
    assert len(top) == 5
    # Sorted descending by count
    assert [t["phrase"] for t in top[:5]] == ["a", "b", "c", "d", "e"]


@pytest.mark.asyncio
async def test_cutoff_parameter_passed():
    conn = _mock_conn([])
    await get_label_frequency_trends(conn, days=7)
    # Inspect the SQL call's second argument
    call_args = conn.fetch.await_args
    cutoff_arg = call_args[0][1]
    expected = datetime.utcnow() - timedelta(days=7)
    # Within 10s tolerance
    assert abs((cutoff_arg - expected).total_seconds()) < 10
