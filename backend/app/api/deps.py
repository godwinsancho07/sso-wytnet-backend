from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidTokenError, UserInactiveError, UserNotFoundError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.token import AccessTokenRepository
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Also check cookie for browser-based flows
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise InvalidTokenError()

    user_id: str = payload.get("sub")
    if not user_id:
        raise InvalidTokenError()

    # Check token is not revoked in DB
    token_repo = AccessTokenRepository(db)
    token_obj = await token_repo.get_by_token(token)
    if token_obj and (token_obj.is_revoked or token_obj.is_expired):
        raise InvalidTokenError("Token has been revoked")

    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    if not user:
        raise UserNotFoundError()
    if not user.is_active:
        raise UserInactiveError()

    return user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


def get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


CurrentUser = Annotated[User, Depends(get_current_user)]
SuperUser = Annotated[User, Depends(get_current_superuser)]
DB = Annotated[AsyncSession, Depends(get_db)]
