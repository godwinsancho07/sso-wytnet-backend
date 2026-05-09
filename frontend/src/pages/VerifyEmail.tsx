import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { authService } from '@/services/auth';
import Alert from '@/components/Alert';

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link.');
      return;
    }
    authService.verifyEmail(token)
      .then(() => { setStatus('success'); setMessage('Email verified! You can now sign in.'); })
      .catch((err) => { setStatus('error'); setMessage(err.response?.data?.detail || 'Verification failed.'); });
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center card space-y-4">
        <h1 className="text-2xl font-bold">Email Verification</h1>
        {status === 'loading' && <p className="text-gray-500">Verifying…</p>}
        {status === 'success' && <Alert type="success" message={message} />}
        {status === 'error' && <Alert type="error" message={message} />}
        {status !== 'loading' && (
          <Link to="/login" className="btn-primary inline-block">Go to sign in</Link>
        )}
      </div>
    </div>
  );
}
