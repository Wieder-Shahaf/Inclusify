import pytest


@pytest.mark.asyncio
async def test_health_returns_200_with_db_connected(test_client):
    """Health endpoint returns 200 when DB is reachable"""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_includes_pool_stats(test_client):
    """Health response includes pool statistics"""
    response = await test_client.get("/health")
    data = response.json()
    assert "pool" in data
    assert "size" in data["pool"]
    assert "free" in data["pool"]
    assert "min" in data["pool"]
    assert "max" in data["pool"]


@pytest.mark.asyncio
async def test_health_includes_version(test_client):
    """Health response includes version information"""
    response = await test_client.get("/health")
    data = response.json()
    assert "version" in data
    assert "commit" in data["version"]
    assert "build_time" in data["version"]


@pytest.mark.asyncio
async def test_health_db_latency_present(test_client):
    """Health response includes DB latency measurement"""
    response = await test_client.get("/health")
    data = response.json()
    assert "components" in data
    assert "database" in data["components"]
    assert "latency_ms" in data["components"]["database"]
