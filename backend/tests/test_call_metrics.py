"""
Unit tests for CallMetrics dataclass.

Tests the accumulation logic, derived statistics, and serialisation
used before persisting to model_metrics table.
"""

import pytest
from app.modules.analysis.call_metrics import CallMetrics


class TestCallMetricsInitial:
    def test_zero_state(self):
        m = CallMetrics()
        assert m.total_sentences == 0
        assert m.llm_calls == 0
        assert m.llm_successes == 0
        assert m.llm_errors == 0
        assert m.llm_timeouts == 0
        assert m.circuit_breaker_trips == 0

    def test_derived_stats_empty(self):
        m = CallMetrics()
        assert m.avg_latency_ms() is None
        assert m.min_latency_ms() is None
        assert m.max_latency_ms() is None


class TestCallMetricsRecordSuccess:
    def test_success_increments_calls_and_successes(self):
        m = CallMetrics()
        m.record_call(100.0, success=True)
        assert m.llm_calls == 1
        assert m.llm_successes == 1
        assert m.llm_errors == 0

    def test_success_appends_latency(self):
        m = CallMetrics()
        m.record_call(200.0, success=True)
        assert m.avg_latency_ms() == pytest.approx(200.0)
        assert m.min_latency_ms() == pytest.approx(200.0)
        assert m.max_latency_ms() == pytest.approx(200.0)

    def test_multiple_successes_aggregate_latency(self):
        m = CallMetrics()
        m.record_call(100.0, success=True)
        m.record_call(300.0, success=True)
        assert m.avg_latency_ms() == pytest.approx(200.0)
        assert m.min_latency_ms() == pytest.approx(100.0)
        assert m.max_latency_ms() == pytest.approx(300.0)


class TestCallMetricsRecordErrors:
    def test_generic_error_increments_errors_not_subtypes(self):
        m = CallMetrics()
        m.record_call(0.0, success=False)
        assert m.llm_calls == 1
        assert m.llm_errors == 1
        assert m.llm_timeouts == 0
        assert m.circuit_breaker_trips == 0

    def test_timeout_increments_both_errors_and_timeouts(self):
        m = CallMetrics()
        m.record_call(5000.0, success=False, error_type="timeout")
        assert m.llm_errors == 1
        assert m.llm_timeouts == 1
        assert m.circuit_breaker_trips == 0

    def test_circuit_breaker_increments_correctly(self):
        m = CallMetrics()
        m.record_call(0.0, success=False, error_type="circuit_breaker")
        assert m.llm_errors == 1
        assert m.circuit_breaker_trips == 1
        assert m.llm_timeouts == 0

    def test_error_latency_not_included_in_avg(self):
        """Latency on errors should not pollute the success latency avg."""
        m = CallMetrics()
        m.record_call(100.0, success=True)
        m.record_call(9999.0, success=False, error_type="timeout")
        assert m.avg_latency_ms() == pytest.approx(100.0)

    def test_http_error_type(self):
        m = CallMetrics()
        m.record_call(50.0, success=False, error_type="http_error")
        assert m.llm_errors == 1
        assert m.llm_timeouts == 0
        assert m.circuit_breaker_trips == 0


class TestCallMetricsMixed:
    def test_mixed_calls(self):
        m = CallMetrics()
        m.record_call(100.0, success=True)
        m.record_call(200.0, success=True)
        m.record_call(0.0, success=False, error_type="circuit_breaker")
        m.record_call(3000.0, success=False, error_type="timeout")

        assert m.llm_calls == 4
        assert m.llm_successes == 2
        assert m.llm_errors == 2
        assert m.llm_timeouts == 1
        assert m.circuit_breaker_trips == 1
        assert m.avg_latency_ms() == pytest.approx(150.0)


class TestCallMetricsToInsertDict:
    def test_basic_serialisation(self):
        m = CallMetrics(total_sentences=5)
        m.record_call(100.0, success=True)
        m.record_call(200.0, success=True)
        m.record_call(0.0, success=False, error_type="timeout")

        d = m.to_insert_dict(analysis_mode="hybrid", total_runtime_ms=1500)

        assert d["analysis_mode"] == "hybrid"
        assert d["total_sentences"] == 5
        assert d["llm_calls"] == 3
        assert d["llm_successes"] == 2
        assert d["llm_errors"] == 1
        assert d["llm_timeouts"] == 1
        assert d["circuit_breaker_trips"] == 0
        assert d["avg_latency_ms"] == pytest.approx(150.0)
        assert d["min_latency_ms"] == pytest.approx(100.0)
        assert d["max_latency_ms"] == pytest.approx(200.0)
        assert d["total_runtime_ms"] == 1500

    def test_no_llm_calls_serialises_none_latency(self):
        m = CallMetrics(total_sentences=3)
        d = m.to_insert_dict(analysis_mode="rules_only", total_runtime_ms=50)

        assert d["llm_calls"] == 0
        assert d["avg_latency_ms"] is None
        assert d["min_latency_ms"] is None
        assert d["max_latency_ms"] is None

    def test_all_modes_accepted(self):
        for mode in ("llm", "hybrid", "rules_only"):
            m = CallMetrics()
            d = m.to_insert_dict(analysis_mode=mode, total_runtime_ms=0)
            assert d["analysis_mode"] == mode
