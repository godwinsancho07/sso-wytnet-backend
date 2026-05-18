from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class OAuthAuthorizeRequest(BaseModel):
    response_type: str = "code"
    client_id: str
    redirect_uri: str
    scope: str = "openid"
    state: Optional[str] = None
    nonce: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None

    @property
    def scopes_list(self) -> List[str]:
        return [s.strip() for s in self.scope.split() if s.strip()]


class OAuthTokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None


class OAuthUserInfo(BaseModel):
    sub: str
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None


class OAuthRevokeRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = None


class OAuthClientCreate(BaseModel):
    app_name: str = Field(max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    redirect_uris: List[str] = Field(min_length=1)
    allowed_scopes: List[str] = Field(default=["openid", "profile", "email"])
    is_confidential: bool = True
    require_pkce: bool = True
    initial_admin_id: Optional[str] = None


class OAuthClientUpdate(BaseModel):
    app_name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    redirect_uris: Optional[List[str]] = None
    allowed_scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None
    require_pkce: Optional[bool] = None


class OAuthClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: str
    app_name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    redirect_uris: List[str]
    allowed_scopes: List[str]
    is_active: bool
    is_confidential: bool
    require_pkce: bool
    created_at: datetime
    admin_emails: List[str] = []
    user_count: int = 0
    plan_id: Optional[str] = None
    credits_used: int = 0
    credits_limit: Optional[int] = None


class OAuthClientPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: str
    app_name: str
    logo_url: Optional[str] = None
    allowed_scopes: List[str]


class OAuthClientWithSecret(OAuthClientRead):
    client_secret: str


class ConsentRequest(BaseModel):
    client_id: str
    scopes: List[str]
    approved: bool
