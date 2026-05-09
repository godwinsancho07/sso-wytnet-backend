import { useSearchParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import api from '@/services/api';
import Alert from '@/components/Alert';
import { Shield, CheckCircle } from 'lucide-react';

const SCOPE_DESCRIPTIONS: Record<string, string> = {
  openid: 'Verify your identity',
  profile: 'Access your name and avatar',
  email: 'Access your email address',
  offline_access: 'Stay signed in',
};

export default function OAuthConsent() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [clientName, setClientName] = useState('');
  const [error, setError] = useState('');

  const clientId = params.get('client_id') || '';
  const scopes = (params.get('scope') || 'openid').split(' ');
  const redirectUri = params.get('redirect_uri') || '';
  const state = params.get('state') || '';
  const nonce = params.get('nonce') || '';
  const codeChallenge = params.get('code_challenge') || '';
  const codeChallengeMethod = params.get('code_challenge_method') || '';

  useEffect(() => {
    api.get(`/v1/clients`)
      .then(({ data }) => {
        const client = data.find((c: any) => c.client_id === clientId);
        if (client) setClientName(client.app_name);
      })
      .catch(() => {});
  }, [clientId]);

  const approve = async () => {
    const url = new URLSearchParams({
      response_type: 'code',
      client_id: clientId,
      redirect_uri: redirectUri,
      scope: scopes.join(' '),
      ...(state && { state }),
      ...(nonce && { nonce }),
      ...(codeChallenge && { code_challenge: codeChallenge }),
      ...(codeChallengeMethod && { code_challenge_method: codeChallengeMethod }),
    });
    try {
      const resp = await api.get(`/oauth/authorize?${url.toString()}`, {
        maxRedirects: 0,
        validateStatus: (s) => s < 400,
      });
      window.location.href = resp.headers?.location || redirectUri;
    } catch (err: any) {
      if (err.response?.status === 302 || err.response?.headers?.location) {
        window.location.href = err.response.headers.location;
      } else {
        setError('Authorization failed');
      }
    }
  };

  const deny = () => {
    window.location.href = `${redirectUri}?error=access_denied${state ? `&state=${state}` : ''}`;
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600 mb-4">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-xl font-bold">Authorization Request</h1>
          <p className="text-gray-500 text-sm mt-1">
            <strong>{clientName || clientId}</strong> is requesting access
          </p>
        </div>

        <div className="card space-y-5">
          {error && <Alert type="error" message={error} />}

          <div>
            <p className="text-sm font-medium text-gray-700 mb-3">This application will be able to:</p>
            <ul className="space-y-2">
              {scopes.map((scope) => (
                <li key={scope} className="flex items-center gap-2 text-sm text-gray-700">
                  <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                  {SCOPE_DESCRIPTIONS[scope] || scope}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex gap-3">
            <button onClick={deny} className="btn-secondary flex-1">Deny</button>
            <button onClick={approve} className="btn-primary flex-1">Approve</button>
          </div>

          <p className="text-xs text-gray-400 text-center">
            You can revoke access at any time from your Applications page.
          </p>
        </div>
      </div>
    </div>
  );
}
