from functools import lru_cache

from app.config import settings
from app.core.keys import get_jwks, load_public_key


@lru_cache(maxsize=1)
def get_jwks_document() -> dict:
    public_pem = load_public_key(settings.public_key_path)
    return get_jwks(public_pem)
