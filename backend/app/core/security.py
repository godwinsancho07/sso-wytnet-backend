import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
import bcrypt as _bcrypt

from app.config import settings
from app.core.keys import load_private_key, load_public_key

# ── Password ─────────────────────────────────────────────────────────────────
# Uses bcrypt directly — passlib is incompatible with bcrypt 4.x.

def hash_password(password: str) -> str:
    """Hash a password using bcrypt. Truncates to 72 bytes (bcrypt limit)."""
    pwd_bytes = password.encode("utf-8")[:72]
    return _bcrypt.hashpw(pwd_bytes, _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        return _bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


# ── Tokens ────────────────────────────────────────────────────────────────────

def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    scopes: list[str],
    client_id: str,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": generate_token(16),
        "scope": " ".join(scopes),
        "client_id": client_id,
        "token_type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(
        payload,
        load_private_key(settings.private_key_path),
        algorithm=settings.jwt_algorithm,
        headers={"kid": "sso-key-1"},
    )


def create_id_token(
    subject: str,
    audience: str,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    email_verified: bool = False,
    nonce: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.id_token_expire_minutes)
    payload: Dict[str, Any] = {
        "iss": settings.oidc_issuer,
        "sub": subject,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": generate_token(16),
    }
    if email:
        payload["email"] = email
        payload["email_verified"] = email_verified
    if full_name:
        payload["name"] = full_name
    if avatar_url:
        payload["picture"] = avatar_url
    if nonce:
        payload["nonce"] = nonce
    return jwt.encode(
        payload,
        load_private_key(settings.private_key_path),
        algorithm=settings.jwt_algorithm,
        headers={"kid": "sso-key-1"},
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token,
        load_public_key(settings.public_key_path),
        algorithms=[settings.jwt_algorithm],
    )


def decode_token_unverified(token: str) -> Dict[str, Any]:
    return jwt.get_unverified_claims(token)


# ── PKCE ──────────────────────────────────────────────────────────────────────

def verify_code_challenge(verifier: str, challenge: str, method: str) -> bool:
    if method == "S256":
        import base64
        digest = hashlib.sha256(verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return hmac.compare_digest(computed, challenge)
    if method == "plain":
        return hmac.compare_digest(verifier, challenge)
    return False
