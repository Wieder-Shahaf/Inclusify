"""
Unit tests for PR #68 — Guest user support & DB persistence.

Tests cover:
- _persist_results: guest run (user=None) persists with user_id=NULL
- _persist_results: authenticated run persists with correct user_id
- _persist_results: no DB pool → silently returns, never crashes
- _persist_results: findings failure → transaction rollback + run marked failed
- _persist_results: success → finish_run("succeeded") called inside transaction
- analyze_text endpoint: private_mode=True skips persistence entirely
- analyze_text endpoint: private_mode=False + no auth → persists as guest
- _map_severity_to_db: all severity levels map correctly
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, call


# ─── Helpers ────────────────────────────────────────────────────────────────

def _make_pool(conn):
    """Build a mock asyncpg pool whose acquire() yields `conn`."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.acquire.return_value = ctx
    return pool


def _make_conn():
    """Build a mock asyncpg connection with a working transaction() ctx manager."""
    txn_ctx = MagicMock()
    txn_ctx.__aenter__ = AsyncMock(return_value=None)
    txn_ctx.__aexit__ = AsyncMock(return_value=None)

    conn = MagicMock()
    conn.transaction.return_value = txn_ctx
    return conn


def _make_request(pool):
    """Build a mock FastAPI Request whose app.state.db_pool is `pool`."""
    state = MagicMock()
    state.db_pool = pool

    app = MagicMock()
    app.state = state

    request = MagicMock()
    request.app = app
    return request


def _make_issue(flagged_text="homosexual", severity="outdated", suggestion=None):
    from app.modules.analysis.router import Issue
    return Issue(
        flagged_text=flagged_text,
        severity=severity,
        type="Outdated Terminology",
        description="Test explanation",
        suggestion=suggestion,
        start=0,
        end=len(flagged_text),
        confidence=0.9,
    )


def _make_user(uid=None):
    user = MagicMock()
    user.id = uid or uuid.uuid4()
    return user


# ─── _persist_results ────────────────────────────────────────────────────────

class TestPersistResultsGuestRun:
    """Guest run (user=None) must persist with user_id=None."""

    @pytest.mark.asyncio
    async def test_guest_run_passes_null_user_id(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        doc_id = uuid.uuid4()
        run_id = uuid.uuid4()

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=doc_id)
            mock_repo.create_run = AsyncMock(return_value=run_id)
            mock_repo.insert_finding = AsyncMock(return_value=uuid.uuid4())
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=None,
                text="The homosexual patient.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue()],
                runtime_ms=100,
            )

        mock_repo.create_document.assert_called_once()
        call_kwargs = mock_repo.create_document.call_args.kwargs
        assert call_kwargs["user_id"] is None

    @pytest.mark.asyncio
    async def test_guest_run_still_creates_run_and_findings(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        doc_id = uuid.uuid4()
        run_id = uuid.uuid4()

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=doc_id)
            mock_repo.create_run = AsyncMock(return_value=run_id)
            mock_repo.insert_finding = AsyncMock(return_value=uuid.uuid4())
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=None,
                text="The homosexual patient.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue()],
                runtime_ms=100,
            )

        mock_repo.create_run.assert_called_once()
        mock_repo.insert_finding.assert_called_once()
        mock_repo.finish_run.assert_called_once()


class TestPersistResultsAuthenticatedRun:
    """Authenticated run must persist with the correct user_id."""

    @pytest.mark.asyncio
    async def test_authenticated_run_passes_user_id(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        user = _make_user()
        doc_id = uuid.uuid4()
        run_id = uuid.uuid4()

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=doc_id)
            mock_repo.create_run = AsyncMock(return_value=run_id)
            mock_repo.insert_finding = AsyncMock(return_value=uuid.uuid4())
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=user,
                text="The homosexual patient.",
                language="en",
                private_mode=False,
                analysis_mode="llm",
                issues=[_make_issue()],
                runtime_ms=200,
            )

        call_kwargs = mock_repo.create_document.call_args.kwargs
        assert call_kwargs["user_id"] == user.id


class TestPersistResultsNoPool:
    """When DB pool is unavailable, persist silently returns without error."""

    @pytest.mark.asyncio
    async def test_no_pool_returns_silently(self):
        state = MagicMock()
        state.db_pool = None
        app = MagicMock()
        app.state = state
        request = MagicMock()
        request.app = app

        with patch("app.modules.analysis.router.repo") as mock_repo:
            from app.modules.analysis.router import _persist_results
            # Should not raise
            await _persist_results(
                request=request,
                user=None,
                text="Some text.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue()],
                runtime_ms=50,
            )

        mock_repo.create_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_pool_attribute_returns_silently(self):
        """app.state has no db_pool attribute — getattr default kicks in."""
        state = MagicMock(spec=[])  # state has no attributes → getattr returns None
        app = MagicMock()
        app.state = state
        request = MagicMock()
        request.app = app

        with patch("app.modules.analysis.router.repo") as mock_repo:
            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=None,
                text="Some text.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[],
                runtime_ms=50,
            )

        mock_repo.create_document.assert_not_called()


class TestPersistResultsTransactionBoundary:
    """finish_run(succeeded) must be inside the transaction; findings failure marks run as failed."""

    @pytest.mark.asyncio
    async def test_finish_run_succeeded_called_on_success(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        run_id = uuid.uuid4()

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=uuid.uuid4())
            mock_repo.create_run = AsyncMock(return_value=run_id)
            mock_repo.insert_finding = AsyncMock(return_value=uuid.uuid4())
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=None,
                text="Test text.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue()],
                runtime_ms=100,
            )

        mock_repo.finish_run.assert_called_once()
        call_kwargs = mock_repo.finish_run.call_args.kwargs
        assert call_kwargs["status"] == "succeeded"
        assert call_kwargs["run_id"] == run_id

    @pytest.mark.asyncio
    async def test_findings_failure_marks_run_as_failed(self):
        """If insert_finding raises, the run is marked failed (not succeeded)."""
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        run_id = uuid.uuid4()

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=uuid.uuid4())
            mock_repo.create_run = AsyncMock(return_value=run_id)
            mock_repo.insert_finding = AsyncMock(side_effect=Exception("DB constraint violation"))
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=None,
                text="Test text.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue()],
                runtime_ms=100,
            )

        mock_repo.finish_run.assert_called_once()
        call_kwargs = mock_repo.finish_run.call_args.kwargs
        assert call_kwargs["status"] == "failed"

    @pytest.mark.asyncio
    async def test_findings_failure_does_not_raise_to_caller(self):
        """Findings failure is caught — analysis response is never blocked."""
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=uuid.uuid4())
            mock_repo.create_run = AsyncMock(return_value=uuid.uuid4())
            mock_repo.insert_finding = AsyncMock(side_effect=RuntimeError("unexpected"))
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            # Must not raise
            await _persist_results(
                request=request,
                user=None,
                text="Test.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue()],
                runtime_ms=50,
            )

    @pytest.mark.asyncio
    async def test_suggestion_persisted_when_issue_has_one(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        finding_id = uuid.uuid4()

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=uuid.uuid4())
            mock_repo.create_run = AsyncMock(return_value=uuid.uuid4())
            mock_repo.insert_finding = AsyncMock(return_value=finding_id)
            mock_repo.insert_suggestion = AsyncMock()
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=None,
                text="The homosexual patient.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue(suggestion="Use 'gay' or 'lesbian'")],
                runtime_ms=100,
            )

        mock_repo.insert_suggestion.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_suggestion_skips_insert_suggestion(self):
        conn = _make_conn()
        pool = _make_pool(conn)
        request = _make_request(pool)

        with patch("app.modules.analysis.router.repo") as mock_repo:
            mock_repo.create_document = AsyncMock(return_value=uuid.uuid4())
            mock_repo.create_run = AsyncMock(return_value=uuid.uuid4())
            mock_repo.insert_finding = AsyncMock(return_value=uuid.uuid4())
            mock_repo.insert_suggestion = AsyncMock()
            mock_repo.finish_run = AsyncMock()

            from app.modules.analysis.router import _persist_results
            await _persist_results(
                request=request,
                user=None,
                text="The homosexual patient.",
                language="en",
                private_mode=False,
                analysis_mode="rules_only",
                issues=[_make_issue(suggestion=None)],
                runtime_ms=100,
            )

        mock_repo.insert_suggestion.assert_not_called()


# ─── Private mode gate ───────────────────────────────────────────────────────

class TestPrivateModeGate:
    """private_mode=True must skip _persist_results entirely."""

    @pytest.mark.asyncio
    async def test_private_mode_skips_persist_results(self):
        with patch("app.modules.analysis.router._persist_results", new_callable=AsyncMock) as mock_persist, \
             patch("app.modules.analysis.router._persist_metrics", new_callable=AsyncMock), \
             patch("app.modules.analysis.router._hybrid_detector") as mock_detector:

            mock_detector.analyze = AsyncMock(return_value=([], "rules_only", MagicMock()))

            from httpx import AsyncClient, ASGITransport
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/analysis/analyze",
                    json={"text": "The homosexual patient.", "language": "en", "private_mode": True},
                )

            assert response.status_code == 200
            mock_persist.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_private_mode_calls_persist_results(self):
        with patch("app.modules.analysis.router._persist_results", new_callable=AsyncMock) as mock_persist, \
             patch("app.modules.analysis.router._persist_metrics", new_callable=AsyncMock), \
             patch("app.modules.analysis.router._hybrid_detector") as mock_detector:

            mock_detector.analyze = AsyncMock(return_value=([], "rules_only", MagicMock()))

            from httpx import AsyncClient, ASGITransport
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/analysis/analyze",
                    json={"text": "The homosexual patient.", "language": "en", "private_mode": False},
                )

            assert response.status_code == 200
            mock_persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_private_mode_omitted_defaults_to_false_and_persists(self):
        """Omitting private_mode uses Pydantic default (False) → persistence IS called.
        Note: body.private_mode=False (not None), so the `if not None` branch
        in the endpoint keeps False, meaning private_mode=False → persist.
        """
        with patch("app.modules.analysis.router._persist_results", new_callable=AsyncMock) as mock_persist, \
             patch("app.modules.analysis.router._persist_metrics", new_callable=AsyncMock), \
             patch("app.modules.analysis.router._hybrid_detector") as mock_detector:

            mock_detector.analyze = AsyncMock(return_value=([], "rules_only", MagicMock()))

            from httpx import AsyncClient, ASGITransport
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/analysis/analyze",
                    json={"text": "Some text.", "language": "en"},
                )

            assert response.status_code == 200
            # Pydantic default is False → persistence fires
            mock_persist.assert_called_once()


# ─── _map_severity_to_db ─────────────────────────────────────────────────────

class TestMapSeverityToDb:
    """All API severity labels must map to valid DB values."""

    def test_outdated_maps_to_low(self):
        from app.modules.analysis.router import _map_severity_to_db
        assert _map_severity_to_db("outdated") == "low"

    def test_biased_maps_to_medium(self):
        from app.modules.analysis.router import _map_severity_to_db
        assert _map_severity_to_db("biased") == "medium"

    def test_potentially_offensive_maps_to_high(self):
        from app.modules.analysis.router import _map_severity_to_db
        assert _map_severity_to_db("potentially_offensive") == "high"

    def test_factually_incorrect_maps_to_medium(self):
        from app.modules.analysis.router import _map_severity_to_db
        assert _map_severity_to_db("factually_incorrect") == "medium"

    def test_pathologizing_maps_to_medium(self):
        """pathologizing not in map → falls back to default 'medium'."""
        from app.modules.analysis.router import _map_severity_to_db
        assert _map_severity_to_db("pathologizing") == "medium"

    def test_unknown_severity_defaults_to_medium(self):
        from app.modules.analysis.router import _map_severity_to_db
        assert _map_severity_to_db("unknown_severity") == "medium"
        assert _map_severity_to_db("") == "medium"
