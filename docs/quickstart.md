# Quick Start

## 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — at minimum set a strong SECRET_KEY
```

## 2. Docker Compose (recommended)

```bash
docker-compose up --build
```

Services:
- Backend API: http://localhost:8000
- Frontend:    http://localhost:3000
- Mailhog UI:  http://localhost:8025
- PostgreSQL:  localhost:5432

## 3. Run migrations

```bash
docker-compose exec backend alembic upgrade head
```

## 4. Seed the database

```bash
docker-compose exec backend python -m scripts.seed
```

Default admin credentials:
- Email:    `admin@sso.local`
- Password: `Admin123!@#`

Change these immediately via `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` env vars.

## 5. Access the app

Open http://localhost:3000 and sign in with the admin credentials.

---

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Generate RSA keys
python -m scripts.generate_keys

# Start PostgreSQL separately, then:
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs (debug mode only).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Running tests

```bash
cd backend
pytest tests/ -v --cov=app
```

---

## OAuth2 Authorization Code Flow (example)

```
# Step 1: Redirect user to authorization endpoint
GET /oauth/authorize
  ?response_type=code
  &client_id=YOUR_CLIENT_ID
  &redirect_uri=http://yourapp.com/callback
  &scope=openid+profile+email
  &state=random_csrf_token
  &code_challenge=BASE64URL(SHA256(code_verifier))
  &code_challenge_method=S256

# Step 2: Exchange code for tokens
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=AUTH_CODE_FROM_REDIRECT
&redirect_uri=http://yourapp.com/callback
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&code_verifier=YOUR_PKCE_VERIFIER

# Step 3: Get user info
GET /oauth/userinfo
Authorization: Bearer ACCESS_TOKEN

# Step 4: Refresh tokens
POST /oauth/token
grant_type=refresh_token&refresh_token=YOUR_REFRESH_TOKEN&client_id=...
```

---

## OIDC Discovery

```
GET /.well-known/openid-configuration
GET /.well-known/jwks.json
```
