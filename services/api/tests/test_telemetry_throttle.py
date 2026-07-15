"""Throttle helper tests."""

from telemetry.throttle import should_emit_login_failed


def test_login_failed_throttle_allows_first_emit_and_blocks_repeat():
    ip_hash = "abc123"

    assert should_emit_login_failed(ip_hash) is True
    assert should_emit_login_failed(ip_hash) is False
