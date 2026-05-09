import os
import json
import base64
from pathlib import Path
from typing import Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def _ensure_keys(private_path: str, public_path: str) -> Tuple[bytes, bytes]:
    priv = Path(private_path)
    pub = Path(public_path)

    if priv.exists() and pub.exists():
        return priv.read_bytes(), pub.read_bytes()

    priv.parent.mkdir(parents=True, exist_ok=True)
    pub.parent.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv.write_bytes(private_pem)
    pub.write_bytes(public_pem)

    return private_pem, public_pem


def load_private_key(path: str) -> str:
    pem, _ = _ensure_keys(path, path.replace("private", "public"))
    return pem.decode()


def load_public_key(path: str) -> str:
    _, pem = _ensure_keys(path.replace("public", "private"), path)
    return pem.decode()


def get_jwks(public_key_pem: str) -> dict:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

    pub = load_pem_public_key(public_key_pem.encode())
    assert isinstance(pub, RSAPublicKey)
    nums = pub.public_key().public_numbers() if hasattr(pub, "public_key") else pub.public_numbers()

    def _b64(n: int, length: int) -> str:
        return base64.urlsafe_b64encode(
            n.to_bytes(length, byteorder="big")
        ).rstrip(b"=").decode()

    key_size = pub.key_size // 8
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "sso-key-1",
                "n": _b64(nums.n, key_size),
                "e": _b64(nums.e, 3),
            }
        ]
    }
