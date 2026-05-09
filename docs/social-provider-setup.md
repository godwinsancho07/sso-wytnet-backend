# Social Provider Setup Guide

## Google

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google+ API** and **People API**
4. Navigate to **APIs & Services → Credentials**
5. Click **Create Credentials → OAuth 2.0 Client IDs**
6. Set Application type: **Web application**
7. Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
8. Copy **Client ID** and **Client Secret** to `.env`:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

---

## GitHub

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Set:
   - Homepage URL: `http://localhost:3000`
   - Authorization callback URL: `http://localhost:8000/auth/github/callback`
4. Copy **Client ID** and generate a **Client Secret** to `.env`:
   ```
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ```

---

## Microsoft

1. Go to [Azure Portal → App registrations](https://portal.azure.com/#blade/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps)
2. Click **New registration**
3. Set Redirect URI (Web): `http://localhost:8000/auth/microsoft/callback`
4. After creation, go to **Certificates & secrets → New client secret**
5. Copy to `.env`:
   ```
   MICROSOFT_CLIENT_ID=your_application_id
   MICROSOFT_CLIENT_SECRET=your_client_secret
   MICROSOFT_TENANT_ID=common  # or your specific tenant ID
   ```

---

## LinkedIn

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
2. Create a new app
3. Under **Auth** tab, add redirect URL: `http://localhost:8000/auth/linkedin/callback`
4. Request products: **Sign In with LinkedIn using OpenID Connect**
5. Copy to `.env`:
   ```
   LINKEDIN_CLIENT_ID=your_client_id
   LINKEDIN_CLIENT_SECRET=your_client_secret
   ```

---

## Production Redirect URIs

Replace `http://localhost:8000` with your actual backend URL.

| Provider  | Variable               | Redirect URI pattern              |
|-----------|------------------------|-----------------------------------|
| Google    | GOOGLE_REDIRECT_URI    | `https://api.yourdomain.com/auth/google/callback`    |
| GitHub    | GITHUB_REDIRECT_URI    | `https://api.yourdomain.com/auth/github/callback`    |
| Microsoft | MICROSOFT_REDIRECT_URI | `https://api.yourdomain.com/auth/microsoft/callback` |
| LinkedIn  | LINKEDIN_REDIRECT_URI  | `https://api.yourdomain.com/auth/linkedin/callback`  |
