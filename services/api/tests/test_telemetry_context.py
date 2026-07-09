"""EmitContext correlation tests."""

from telemetry.context import EmitContext


def test_for_user_honors_request_id_from_client_header():
    ctx = EmitContext.for_user(42, request_id="req_client_action")

    assert ctx.user_id == "42"
    assert ctx.request_id == "req_client_action"
