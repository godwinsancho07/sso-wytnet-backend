import { useEffect, useState } from 'react';
import { ShieldCheck, Copy, AlertCircle, KeyRound, Power } from 'lucide-react';

import Alert from '@/components/Alert';
import { extractErrorMessage } from '@/utils/errors';
import { mfaService, MFASetupData, MFAStatus } from '@/services/admin';

const QR_CDN = 'https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=';

export default function MFASetup() {
  const [status, setStatus] = useState<MFAStatus | null>(null);
  const [setup, setSetup] = useState<MFASetupData | null>(null);
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);

  const loadStatus = async () => {
    try {
      setStatus(await mfaService.getStatus());
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to load MFA status'));
    }
  };

  useEffect(() => { loadStatus(); }, []);

  const startSetup = async () => {
    setError(''); setInfo(''); setBusy(true);
    try {
      setSetup(await mfaService.setup());
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to start MFA setup'));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setInfo(''); setBusy(true);
    try {
      await mfaService.confirm(code.trim());
      setInfo('MFA enabled. Save your backup codes — they will not be shown again.');
      setCode('');
      await loadStatus();
    } catch (e) {
      setError(extractErrorMessage(e, 'Invalid code. Try again.'));
    } finally {
      setBusy(false);
    }
  };

  const disable = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setInfo(''); setBusy(true);
    try {
      await mfaService.disable(password);
      setPassword('');
      setSetup(null);
      setInfo('MFA disabled.');
      await loadStatus();
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to disable MFA'));
    } finally {
      setBusy(false);
    }
  };

  const copy = (txt: string) => {
    navigator.clipboard.writeText(txt).then(
      () => setInfo('Copied to clipboard.'),
      () => setError('Could not copy to clipboard.'),
    );
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="w-7 h-7 text-primary-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Two-Factor Authentication</h1>
          <p className="text-gray-500 text-sm">
            Add an authenticator-app code on top of your password.
          </p>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}
      {info && <Alert type="success" message={info} onClose={() => setInfo('')} />}

      {status?.is_required && !status.is_enabled && !setup && (
        <div className="card p-4 border-l-4 border-amber-400 bg-amber-50 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
          <div className="text-sm text-amber-900">
            An administrator has required you to enable MFA. Please complete setup below.
          </div>
        </div>
      )}

      {status?.is_enabled ? (
        <div className="card p-6 space-y-4">
          <div className="flex items-center gap-2 text-green-700">
            <ShieldCheck className="w-5 h-5" />
            <span className="font-medium">MFA is enabled on this account.</span>
          </div>
          {status.last_used_at && (
            <p className="text-xs text-gray-500">
              Last used: {new Date(status.last_used_at).toLocaleString()}
            </p>
          )}
          <form onSubmit={disable} className="space-y-3 pt-2 border-t border-gray-100">
            <p className="text-sm text-gray-700">
              To disable MFA, confirm your password.
            </p>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Current password"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
              required
            />
            <button
              type="submit"
              disabled={busy}
              className="btn-secondary text-sm gap-1 text-red-700"
            >
              <Power className="w-4 h-4" /> Disable MFA
            </button>
          </form>
        </div>
      ) : !setup ? (
        <div className="card p-6 space-y-4">
          <p className="text-sm text-gray-700">
            Click the button below to generate a new TOTP secret. Scan it with
            an authenticator app like Google Authenticator, Authy, or 1Password.
          </p>
          <button onClick={startSetup} disabled={busy} className="btn-primary text-sm gap-1">
            <KeyRound className="w-4 h-4" /> Begin Setup
          </button>
        </div>
      ) : (
        <div className="card p-6 space-y-6">
          <div>
            <h2 className="font-semibold text-gray-900 mb-2">1. Scan the QR code</h2>
            <div className="flex flex-col sm:flex-row gap-4 items-start">
              <img
                src={QR_CDN + encodeURIComponent(setup.otpauth_uri)}
                alt="MFA QR code"
                className="w-[220px] h-[220px] border border-gray-200 rounded"
              />
              <div className="space-y-2 flex-1 text-xs">
                <p className="text-gray-600">
                  Or enter the secret manually:
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 break-all bg-gray-50 border border-gray-200 px-2 py-1 rounded font-mono">
                    {setup.secret}
                  </code>
                  <button
                    onClick={() => copy(setup.secret)}
                    className="p-1.5 border border-gray-200 rounded hover:bg-gray-50"
                    title="Copy secret"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-gray-500 text-[11px] break-all">
                  {setup.otpauth_uri}
                </p>
              </div>
            </div>
          </div>

          <div>
            <h2 className="font-semibold text-gray-900 mb-2">2. Save your backup codes</h2>
            <p className="text-xs text-gray-600 mb-3">
              Each code can be used once if you lose your authenticator. They will not be shown again.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {setup.backup_codes.map((c) => (
                <code
                  key={c}
                  className="bg-gray-50 border border-gray-200 px-2 py-1.5 rounded font-mono text-xs text-center"
                >
                  {c}
                </code>
              ))}
            </div>
            <button
              onClick={() => copy(setup.backup_codes.join('\n'))}
              className="btn-secondary text-xs gap-1 mt-2"
            >
              <Copy className="w-3 h-3" /> Copy all
            </button>
          </div>

          <form onSubmit={confirm} className="space-y-3">
            <h2 className="font-semibold text-gray-900">3. Confirm with a code</h2>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="6-digit code"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={8}
              className="w-40 px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono tracking-widest text-center"
              required
            />
            <div>
              <button type="submit" disabled={busy} className="btn-primary text-sm">
                Confirm & Enable
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
