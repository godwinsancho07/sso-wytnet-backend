"""
Regenerate RSA key pair. Run this before first deployment.
Usage: python -m scripts.generate_keys
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate():
    priv_path = Path(settings.private_key_path)
    pub_path = Path(settings.public_key_path)
    priv_path.parent.mkdir(parents=True, exist_ok=True)

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
    priv_path.write_bytes(private_pem)
    pub_path.write_bytes(public_pem)
    print(f"✓ Private key: {priv_path}")
    print(f"✓ Public key:  {pub_path}")
    print("\nKeep private.pem secret. Distribute public.pem to client applications for JWT verification.")


if __name__ == "__main__":
    generate()
