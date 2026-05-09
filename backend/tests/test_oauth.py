import base64
import hashlib
import secrets
import pytest
from httpx import AsyncClient


def _make_pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


async def _create_client_and_user(client: AsyncClient):
    """Helper: create superuser, login, create OAuth client."""
    # Register + promote to superuser is done via direct DB manipulation in real tests.
    # Here we test the public OAuth endpoints that don't require superuser.
    pass


@pytest.mark.asyncio
async def test_openid_configuration(client: AsyncClient):
    resp = await client.get("/.well-known/openid-configuration")
    assert resp.status_code == 200
    data = resp.json()
    assert "issuer" in data
    assert "authorization_endpoint" in data
    assert "token_endpoint" in data
    assert "jwks_uri" in data


@pytest.mark.asyncio
async def test_jwks_endpoint(client: AsyncClient):
    resp = await client.get("/.well-known/jwks.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
    assert len(data["keys"]) > 0
    key = data["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert "n" in key
    assert "e" in key


@pytest.mark.asyncio
async def test_token_invalid_grant(client: AsyncClient):
    resp = await client.post("/oauth/token", data={
        "grant_type": "authorization_code",
        "code": "invalid_code_xyz",
        "client_id": "nonexistent_client",
        "redirect_uri": "http://localhost:3000/callback",
    })
    assert resp.status_code in (400, 401)


@pytest.mark.asyncio
async def test_userinfo_unauthenticated(client: AsyncClient):
    resp = await client.get("/oauth/userinfo")
    assert resp.status_code == 401
