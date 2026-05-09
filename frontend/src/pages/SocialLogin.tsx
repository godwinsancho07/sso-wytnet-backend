import { useLocation, Link } from 'react-router-dom';
import { Shield } from 'lucide-react';
import SocialLoginButtons from '@/components/SocialLoginButtons';
import Alert from '@/components/Alert';

export default function SocialLogin() {
  const location = useLocation();
  const error = new URLSearchParams(location.search).get('error');

  const errorMessages: Record<string, string> = {
    cancelled: 'Social login was cancelled.',
    social_login_failed: 'Social login failed. Please try again.',
    access_denied: 'Access was denied by the provider.',
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600 mb-4">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Sign in with a provider</h1>
          <p className="text-gray-500 mt-1 text-sm">Choose a social account to continue</p>
        </div>

        <div className="card space-y-5">
          {error && (
            <Alert type="error" message={errorMessages[error] || 'An error occurred during social login.'} />
          )}

          <SocialLoginButtons />

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs text-gray-400">
              <span className="bg-white px-3">or</span>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <Link to="/login" className="btn-secondary w-full text-center">
              Sign in with email
            </Link>
            <Link to="/register" className="btn-secondary w-full text-center">
              Create a new account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
