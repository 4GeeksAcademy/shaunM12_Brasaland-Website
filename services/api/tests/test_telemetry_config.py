"""Telemetry configuration defaults."""

from __future__ import annotations

from config import resolve_telemetry_enabled, resolve_telemetry_sink


def test_telemetry_defaults_follow_explicit_env():
    assert (
        resolve_telemetry_enabled(
            env_value="false",
            is_dev=True,
            database_url="postgresql://example",
        )
        is False
    )
    assert (
        resolve_telemetry_sink(
            env_value="stdout",
            is_dev=True,
            database_url="postgresql://example",
        )
        == "stdout"
    )


def test_telemetry_auto_enables_in_dev_when_database_is_configured():
    assert (
        resolve_telemetry_enabled(
            env_value=None,
            is_dev=True,
            database_url="postgresql://example",
        )
        is True
    )
    assert (
        resolve_telemetry_sink(
            env_value=None,
            is_dev=True,
            database_url="postgresql://example",
        )
        == "both"
    )


def test_telemetry_stays_off_without_database_even_in_dev():
    assert (
        resolve_telemetry_enabled(
            env_value=None,
            is_dev=True,
            database_url=None,
        )
        is False
    )
    assert (
        resolve_telemetry_sink(
            env_value=None,
            is_dev=True,
            database_url=None,
        )
        == "stdout"
    )
