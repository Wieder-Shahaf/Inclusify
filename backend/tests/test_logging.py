"""Logging is stream-split so Railway's severity filter works: INFO/DEBUG to
stdout (tagged 'info'), WARNING+ to stderr (tagged 'error')."""
import logging


def _rec(level):
    return logging.LogRecord("x", level, "f.py", 1, "msg", None, None)


def test_max_level_filter_splits_at_warning():
    from app.main import _MaxLevelFilter
    f = _MaxLevelFilter(logging.WARNING)
    assert f.filter(_rec(logging.DEBUG)) is True
    assert f.filter(_rec(logging.INFO)) is True
    assert f.filter(_rec(logging.WARNING)) is False
    assert f.filter(_rec(logging.ERROR)) is False


def test_configured_root_routes_streams(capsys):
    from app.main import _configure_logging
    _configure_logging()
    log = logging.getLogger("app.test")
    log.info("hello-info")
    log.warning("hello-warning")
    out, err = capsys.readouterr()
    assert "hello-info" in out and "hello-info" not in err
    assert "hello-warning" in err and "hello-warning" not in out
