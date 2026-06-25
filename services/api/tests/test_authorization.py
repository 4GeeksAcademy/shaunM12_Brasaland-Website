"""Access-control & token-confusion tests for the auth-enforced routes.

These probe for broken-access-control and token-misuse bugs — the class of
regression this ticket guards against. They assert on the *authorization
decision* (who is allowed to do what), not on response shape.
"""

from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient


def _register_and_token(client: TestClient, email: str, password: str = "supersecret"):
    client.post("/auth/register", json={"email": email, "password": password})
    token = client.post(
        "/auth/login", data={"username": email, "password": password}
    ).json()["access_token"]
    user_id = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).json()["id"]
    return user_id, token


# --- Privilege escalation ----------------------------------------------------


def test_user_cannot_escalate_self_to_admin(anon_client: TestClient):
    """A non-admin must not be able to grant themselves admin via self-update."""
    user_id, token = _register_and_token(anon_client, "sneaky@brasaland.com")

    anon_client.put(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_admin": True},
    )

    me = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["is_admin"] is False


def test_user_cannot_reactivate_or_deactivate_via_self_update(anon_client: TestClient):
    """A non-admin must not be able to flip the privileged ``is_active`` flag."""
    user_id, token = _register_and_token(anon_client, "flip@brasaland.com")

    resp = anon_client.put(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )
    # Either rejected outright, or the privileged change is ignored — but the
    # account must remain usable (the user cannot lock the field via self-update).
    still_me = anon_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert still_me.status_code == 200
    assert still_me.json()["is_active"] is True
    assert resp.status_code in (200, 403)


# --- Broken object-level authorization (delete) ------------------------------


def test_non_admin_cannot_delete_another_user(anon_client: TestClient):
    """Authentication alone must not authorize deleting an arbitrary account."""
    _, token_a = _register_and_token(anon_client, "alice@brasaland.com")
    bob_id, bob_token = _register_and_token(anon_client, "bob@brasaland.com")

    resp = anon_client.delete(
        f"/users/{bob_id}", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp.status_code == 403

    # Bob's account must still exist and work.
    assert (
        anon_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {bob_token}"}
        ).status_code
        == 200
    )


# --- Token-type confusion ----------------------------------------------------


def test_password_reset_token_cannot_authenticate(anon_client: TestClient):
    """A password-reset JWT must not be accepted as an access (bearer) token."""
    user_id, _ = _register_and_token(anon_client, "confuse@brasaland.com")
    from auth.security import create_password_reset_token

    reset = create_password_reset_token(user_id, "some-jti")
    resp = anon_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {reset}"}
    )
    assert resp.status_code == 401


# --- Algorithm confusion -----------------------------------------------------


def _b64url(data: dict) -> str:
    raw = json.dumps(data).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def test_unsigned_alg_none_token_is_rejected(anon_client: TestClient):
    """A forged ``alg: none`` token (no signature) must never authenticate."""
    header = _b64url({"alg": "none", "typ": "JWT"})
    payload = _b64url({"sub": "1"})
    forged = f"{header}.{payload}."  # empty signature

    resp = anon_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {forged}"}
    )
    assert resp.status_code == 401
