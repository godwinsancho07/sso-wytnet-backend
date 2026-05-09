import pytest
from app.core.security import (
    hash_password, verify_password, generate_token,
    verify_code_challenge, create_access_token, decode_access_token,
)
import base64
import hashlib


def test_password_hash_and_verify():
    plain = "MySecurePassword123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_generate_token_uniqueness():
    tokens = {generate_token() for _ in range(100)}
    assert len(tokens) == 100


def test_pkce_s256_valid():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    assert verify_code_challenge(verifier, challenge, "S256")


def test_pkce_s256_invalid():
    assert not verify_code_challenge("wrong_verifier", "fake_challenge", "S256")


def test_pkce_plain():
    verifier = "my_plain_verifier"
    assert verify_code_challenge(verifier, verifier, "plain")


def test_access_token_encode_decode():
    token = create_access_token(
        subject="user-123",
        scopes=["openid", "email"],
        client_id="test-client",
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["token_type"] == "access"
    assert "openid" in payload["scope"]
