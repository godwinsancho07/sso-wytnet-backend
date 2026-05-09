from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str = "error"):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


# ── Auth ──────────────────────────────────────────────────────────────────────

class InvalidCredentialsError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Invalid email or password", "invalid_credentials")


class UserNotFoundError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_404_NOT_FOUND, "User not found", "user_not_found")


class UserAlreadyExistsError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_409_CONFLICT, "Email already registered", "email_exists")


class UserInactiveError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_403_FORBIDDEN, "Account is deactivated", "account_inactive")


class EmailNotVerifiedError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_403_FORBIDDEN, "Email address not verified", "email_not_verified")


class InvalidTokenError(AppException):
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, "invalid_token")


class TokenExpiredError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Token has expired", "token_expired")


# ── OAuth ─────────────────────────────────────────────────────────────────────

class OAuthError(AppException):
    def __init__(self, error: str, description: str = "", status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code, description or error, error)
        self.oauth_error = error
        self.oauth_description = description


class InvalidClientError(OAuthError):
    def __init__(self):
        super().__init__("invalid_client", "Client authentication failed")


class InvalidGrantError(OAuthError):
    def __init__(self, detail: str = "The authorization code is invalid or expired"):
        super().__init__("invalid_grant", detail)


class InvalidScopeError(OAuthError):
    def __init__(self):
        super().__init__("invalid_scope", "Requested scope is not allowed")


class UnauthorizedClientError(OAuthError):
    def __init__(self):
        super().__init__("unauthorized_client", "Client is not authorized for this grant type")


class InvalidRedirectUriError(OAuthError):
    def __init__(self):
        super().__init__("invalid_request", "redirect_uri does not match registered URIs")


class PKCERequiredError(OAuthError):
    def __init__(self):
        super().__init__("invalid_request", "PKCE is required for this client")


class PKCEVerificationError(OAuthError):
    def __init__(self):
        super().__init__("invalid_grant", "Code verifier does not match code challenge")


# ── Social ────────────────────────────────────────────────────────────────────

class SocialProviderError(AppException):
    def __init__(self, provider: str, detail: str = "Social provider error"):
        super().__init__(status.HTTP_502_BAD_GATEWAY, f"{provider}: {detail}", "social_provider_error")


class SocialStateError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_400_BAD_REQUEST, "Invalid or missing OAuth state parameter", "invalid_state")


# ── RBAC ──────────────────────────────────────────────────────────────────────

class PermissionDeniedError(AppException):
    def __init__(self, permission: str = ""):
        detail = f"Permission denied: {permission}" if permission else "Permission denied"
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "permission_denied")


class RoleNotFoundError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_404_NOT_FOUND, "Role not found", "role_not_found")


# ── Session ───────────────────────────────────────────────────────────────────

class SessionExpiredError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Session has expired", "session_expired")


class SessionInvalidError(AppException):
    def __init__(self):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Session is invalid", "session_invalid")
