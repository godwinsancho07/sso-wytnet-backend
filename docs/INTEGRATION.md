# Integrating with the SSO Identity Provider

> Complete guide for client applications that want to use this SSO as their identity provider.

This document walks you through registering an OAuth client, implementing the **Authorization Code flow with PKCE**, verifying tokens, refreshing them, and handling logout.

---

## 1. What this SSO provides

| Capability | Endpoint | Notes |
|---|---|---|
| OIDC Discovery | `GET /.well-known/openid-configuration` | Auto-config |
| JWKS (public keys) | `GET /.well-known/jwks.json` | RS256, kid `sso-key-1` |
| Authorize | `GET /oauth/authorize` | Browser-redirect; user logs in here |
| Token | `POST /oauth/token` | Exchange code or refresh |
| UserInfo | `GET /oauth/userinfo` | OIDC standard |
| Revoke | `POST /oauth/revoke` | RFC 7009 |

**Token format:** RS256-signed JWT. Public key at `/.well-known/jwks.json`.
**Issuer (iss claim):** `<BACKEND_URL>` (e.g. `http://localhost:8000`).

---

## 2. Register your app

A super_admin creates an OAuth client for your app via:

```
POST /v1/clients
{
  "app_name": "My App",
  "redirect_uris": ["https://myapp.com/callback"],
  "allowed_scopes": ["openid", "profile", "email"],
  "is_confidential": true,
  "require_pkce": true
}
```

You'll receive:
- `client_id` — public, embed in your app
- `client_secret` — **shown ONCE**, store as a secret in your backend (not in your frontend!)

> **Public clients** (SPAs, mobile apps) should set `is_confidential: false` and rely on PKCE only — no client secret.

---

## 3. The flow (Authorization Code with PKCE)

```
   ┌────────────┐                                     ┌─────────────┐
   │ Your App   │                                     │ SSO Provider │
   └────────────┘                                     └─────────────┘
        │                                                    │
        │ 1. User clicks "Sign in"                           │
        │    → generate code_verifier + code_challenge       │
        │    → save verifier in sessionStorage               │
        │                                                    │
        │ 2. Redirect: GET /oauth/authorize                  │
        │    ?response_type=code                             │
        │    &client_id=YOUR_CLIENT_ID                       │
        │    &redirect_uri=https://myapp.com/callback        │
        │    &scope=openid+profile+email                     │
        │    &state=RANDOM_CSRF_TOKEN                        │
        │    &code_challenge=BASE64URL(SHA256(verifier))     │
        │    &code_challenge_method=S256                     │
        │ ──────────────────────────────────────────────────►│
        │                                                    │
        │              User logs in / consents               │
        │                                                    │
        │ 3. ◄────────── 302 Redirect ──────────────────────│
        │    https://myapp.com/callback?code=AUTH_CODE       │
        │    &state=RANDOM_CSRF_TOKEN                        │
        │                                                    │
        │ 4. Verify state matches what you stored            │
        │                                                    │
        │ 5. POST /oauth/token (form-encoded)                │
        │    grant_type=authorization_code                   │
        │    code=AUTH_CODE                                  │
        │    redirect_uri=https://myapp.com/callback         │
        │    client_id=YOUR_CLIENT_ID                        │
        │    client_secret=YOUR_CLIENT_SECRET (if confidential)│
        │    code_verifier=ORIGINAL_VERIFIER                 │
        │ ──────────────────────────────────────────────────►│
        │                                                    │
        │ 6. ◄──────────────────────────────────────────────│
        │    {                                               │
        │      "access_token": "eyJ…",       (JWT, 15 min)   │
        │      "refresh_token": "abc…",       (30 days)      │
        │      "id_token": "eyJ…",             (OIDC, 1 hour)│
        │      "token_type": "Bearer",                       │
        │      "expires_in": 900,                            │
        │      "scope": "openid profile email"               │
        │    }                                               │
        │                                                    │
        │ 7. Use access_token in Authorization: Bearer …     │
        │    on every API call to your backend.              │
        │                                                    │
        │ 8. Verify the JWT signature against /jwks.json     │
        │    (your backend caches this).                     │
```

---

## 4. Implementation — JavaScript (browser SPA)

### 4.1 Generate PKCE verifier + challenge

```js
async function createPKCE() {
  const arr = new Uint8Array(48);
  crypto.getRandomValues(arr);
  const verifier = Array.from(arr, b => b.toString(16).padStart(2, '0')).join('');

  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  const challenge = btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  return { verifier, challenge };
}
```

### 4.2 Start sign-in

```js
async function signIn() {
  const { verifier, challenge } = await createPKCE();
  const state = crypto.randomUUID();

  sessionStorage.setItem('pkce_verifier', verifier);
  sessionStorage.setItem('oauth_state', state);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: '__CLIENT_ID__',
    redirect_uri: '__REDIRECT_URI__',
    scope: 'openid profile email',
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  });

  window.location.href = `__BACKEND_URL__/oauth/authorize?${params}`;
}
```

### 4.3 Handle the callback

```js
async function handleCallback() {
  const params = new URLSearchParams(window.location.search);
  const code  = params.get('code');
  const state = params.get('state');

  if (state !== sessionStorage.getItem('oauth_state')) {
    throw new Error('Invalid state — possible CSRF attack');
  }

  const verifier = sessionStorage.getItem('pkce_verifier');
  sessionStorage.removeItem('oauth_state');
  sessionStorage.removeItem('pkce_verifier');

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: '__REDIRECT_URI__',
    client_id: '__CLIENT_ID__',
    code_verifier: verifier,
    // For confidential clients only — DO NOT ship client_secret in browser code
    // client_secret: '__CLIENT_SECRET__',
  });

  const resp = await fetch('__BACKEND_URL__/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  const tokens = await resp.json();

  localStorage.setItem('access_token',  tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  localStorage.setItem('id_token',      tokens.id_token);

  return tokens;
}
```

### 4.4 Refresh

```js
async function refresh() {
  const refreshToken = localStorage.getItem('refresh_token');
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: '__CLIENT_ID__',
  });
  const resp = await fetch('__BACKEND_URL__/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!resp.ok) { window.location.href = '/login'; return; }
  const tokens = await resp.json();
  localStorage.setItem('access_token',  tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
}
```

### 4.5 Sign out (revoke)

```js
async function signOut() {
  const token = localStorage.getItem('refresh_token');
  await fetch('__BACKEND_URL__/oauth/revoke', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, token_type_hint: 'refresh_token' }),
  });
  localStorage.clear();
  window.location.href = '/';
}
```

---

## 5. Implementation — Python (backend, confidential client)

```python
import base64, hashlib, secrets, requests, urllib.parse

BACKEND_URL   = "__BACKEND_URL__"
CLIENT_ID     = "__CLIENT_ID__"
CLIENT_SECRET = "__CLIENT_SECRET__"
REDIRECT_URI  = "__REDIRECT_URI__"

def make_pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge

def authorize_url(state, challenge):
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{BACKEND_URL}/oauth/authorize?{urllib.parse.urlencode(params)}"

def exchange_code(code, verifier):
    resp = requests.post(f"{BACKEND_URL}/oauth/token", data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code_verifier": verifier,
    })
    resp.raise_for_status()
    return resp.json()

def refresh(refresh_token):
    resp = requests.post(f"{BACKEND_URL}/oauth/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()
```

---

## 6. Verifying tokens (your backend)

Your API backend must **verify the JWT signature** before trusting the user identity.

### Python (PyJWT + httpx)

```python
import jwt, httpx
from functools import lru_cache

ISSUER = "__BACKEND_URL__"
AUDIENCE = "__CLIENT_ID__"

@lru_cache
def get_jwks():
    return httpx.get(f"{ISSUER}/.well-known/jwks.json").json()

def verify_access_token(token: str) -> dict:
    headers = jwt.get_unverified_header(token)
    kid = headers["kid"]
    key = next(k for k in get_jwks()["keys"] if k["kid"] == kid)
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
    return jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        issuer=ISSUER,
        # access_token has no aud claim by default (only id_token does)
        options={"verify_aud": False},
    )

# In a FastAPI dep:
def current_user(authorization: str = Header(...)):
    scheme, token = authorization.split()
    return verify_access_token(token)  # returns {sub, email, scope, ...}
```

### Node.js (jose)

```js
import { createRemoteJWKSet, jwtVerify } from 'jose';

const JWKS = createRemoteJWKSet(new URL('__BACKEND_URL__/.well-known/jwks.json'));

export async function verifyToken(token) {
  const { payload } = await jwtVerify(token, JWKS, {
    issuer: '__BACKEND_URL__',
    algorithms: ['RS256'],
  });
  return payload;   // { sub, email, scope, ... }
}
```

---

## 7. Token claims you'll receive

### Access token (RS256 JWT)
```json
{
  "iss": "__BACKEND_URL__",
  "sub": "user-uuid",
  "iat": 1700000000,
  "exp": 1700000900,
  "jti": "unique-token-id",
  "scope": "openid profile email",
  "client_id": "__CLIENT_ID__",
  "token_type": "access",
  "email": "user@example.com"
}
```

### ID token (OIDC, RS256 JWT)
```json
{
  "iss": "__BACKEND_URL__",
  "sub": "user-uuid",
  "aud": "__CLIENT_ID__",
  "iat": 1700000000,
  "exp": 1700003600,
  "email": "user@example.com",
  "email_verified": true,
  "name": "Jane Doe",
  "picture": "https://...",
  "nonce": "your-nonce"
}
```

---

## 8. Scopes

| Scope | Grants access to |
|---|---|
| `openid` | Required for OIDC. ID token issued. |
| `profile` | `name`, `picture` claims |
| `email`   | `email`, `email_verified` claims |
| `offline_access` | Refresh token (always issued by this IdP) |

---

## 9. Security checklist

- ✅ **Always use PKCE** — required for public clients, recommended for confidential
- ✅ **Always validate `state`** on the callback to prevent CSRF
- ✅ **Always verify JWT signature** on your backend with the JWKS public key
- ✅ **Verify `iss` and `aud` claims** on the ID token
- ✅ Rotate refresh tokens (this IdP rotates automatically — old token is invalidated when used)
- ✅ Don't store tokens in localStorage if you can avoid it (httpOnly cookie is safer; this IdP supports cookie-based session via the same login flow)
- ❌ Don't ship `client_secret` to a browser/mobile app — use PKCE-only public client
- ❌ Don't log tokens or include them in URL paths (use Authorization header)

---

## 10. Logout

### Local sign-out (your app only)
Clear local tokens. The user is still logged in at the IdP.

### Single sign-out (everywhere)
Call `POST /auth/logout/all` with the user's bearer token — revokes all sessions and refresh tokens for that user across **all** apps.

### Revoke a single refresh token
```
POST /oauth/revoke
Content-Type: application/json
Authorization: Bearer <access_token>

{ "token": "<refresh_token>", "token_type_hint": "refresh_token" }
```

---

## 11. Error responses

OAuth errors follow RFC 6749:

```json
{ "error": "invalid_grant", "error_description": "..." }
```

Common errors:
| Error | Meaning |
|---|---|
| `invalid_client` | Wrong client_id or client_secret |
| `invalid_grant` | Code expired, already used, or PKCE verification failed |
| `invalid_redirect_uri` | redirect_uri doesn't match what's registered |
| `invalid_scope` | Requested scope not allowed for this client |

---

## 12. Useful links

- **OIDC Discovery** → `__BACKEND_URL__/.well-known/openid-configuration`
- **JWKS** → `__BACKEND_URL__/.well-known/jwks.json`
- **Backend API docs** → `__BACKEND_URL__/docs` (when DEBUG=true)
