/**
 * OAuth client helper — for use by frontend apps integrating with this SSO provider.
 * Stores PKCE verifier in sessionStorage between the redirect away and the callback.
 */
import { createPKCEPair } from './pkce';

const PKCE_VERIFIER_KEY = 'oauth_pkce_verifier';
const STATE_KEY = 'oauth_state';

export interface OAuthClientConfig {
  authorizationEndpoint: string;
  tokenEndpoint: string;
  clientId: string;
  redirectUri: string;
  scope: string;
}

export async function startAuthorizationFlow(cfg: OAuthClientConfig): Promise<void> {
  const { verifier, challenge, state } = await createPKCEPair();
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: cfg.clientId,
    redirect_uri: cfg.redirectUri,
    scope: cfg.scope,
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  });
  window.location.href = `${cfg.authorizationEndpoint}?${params}`;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  token_type: string;
  expires_in: number;
  scope?: string;
}

export async function exchangeCodeForTokens(
  cfg: OAuthClientConfig,
  code: string,
  state: string,
  clientSecret?: string,
): Promise<TokenResponse> {
  const expectedState = sessionStorage.getItem(STATE_KEY);
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);

  if (!expectedState || expectedState !== state) {
    throw new Error('Invalid OAuth state — possible CSRF attack');
  }
  if (!verifier) {
    throw new Error('Missing PKCE verifier');
  }

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    code,
    redirect_uri: cfg.redirectUri,
    client_id: cfg.clientId,
    code_verifier: verifier,
    ...(clientSecret && { client_secret: clientSecret }),
  });

  const resp = await fetch(cfg.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });

  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(STATE_KEY);

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error_description || err.error || 'Token exchange failed');
  }
  return resp.json();
}
