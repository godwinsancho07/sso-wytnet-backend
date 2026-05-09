import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Shield, Zap } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import Alert from '@/components/Alert';
import SocialLoginButtons from '@/components/SocialLoginButtons';

const schema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

type FormData = z.infer<typeof schema>;

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, clearError, primaryDashboard } = useAuthStore();
  const searchParams = new URLSearchParams(location.search);
  const nextUrl = searchParams.get('next');
  const from = (location.state as any)?.from?.pathname;

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const redirectAfterLogin = () => {
    if (nextUrl) {
      // Full redirect so session cookie is sent to /oauth/authorize
      window.location.href = nextUrl;
      return;
    }
    navigate(from || primaryDashboard(), { replace: true });
  };

  const onSubmit = async (data: FormData) => {
    try {
      await login(data.email, data.password);
      redirectAfterLogin();
    } catch {}
  };

  const quickLogin = async (email: string, password: string) => {
    try {
      await login(email, password);
      redirectAfterLogin();
    } catch {}
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600 mb-4">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Sign in</h1>
          <p className="text-gray-500 mt-1 text-sm">Access your SSO account</p>
        </div>

        <div className="card space-y-5">
          {error && (
            <Alert type="error" message={error} onClose={clearError} />
          )}

          <SocialLoginButtons />

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs text-gray-400">
              <span className="bg-white px-3">or continue with email</span>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                {...register('email')}
                type="email"
                className="input"
                placeholder="you@example.com"
                autoComplete="email"
              />
              {errors.email && (
                <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="label mb-0">Password</label>
                <Link to="/forgot-password" className="text-xs text-primary-600 hover:underline">
                  Forgot password?
                </Link>
              </div>
              <input
                {...register('password')}
                type="password"
                className="input"
                placeholder="••••••••"
                autoComplete="current-password"
              />
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            <button type="submit" disabled={isLoading} className="btn-primary w-full">
              {isLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="text-center text-sm text-gray-500">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary-600 font-medium hover:underline">
              Create one
            </Link>
          </p>

          {import.meta.env.DEV && (
            <div className="border-t border-dashed border-amber-200 pt-4 space-y-2">
              <p className="text-[10px] uppercase text-amber-700 text-center font-semibold tracking-wide">
                Dev quick login
              </p>
              <button
                type="button"
                onClick={() => quickLogin('admin@example.com', 'Admin123!@#')}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 w-full rounded-lg bg-amber-50 border border-amber-200 px-4 py-2 text-xs font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-50 transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                Super Admin <span className="font-mono opacity-60">admin@example.com</span>
              </button>
              <button
                type="button"
                onClick={() => quickLogin('appadmin@example.com', 'AppAdmin123!@#')}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 w-full rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-xs font-medium text-blue-900 hover:bg-blue-100 disabled:opacity-50 transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                App Admin <span className="font-mono opacity-60">appadmin@example.com</span>
              </button>
              <button
                type="button"
                onClick={() => quickLogin('user@example.com', 'User123!@#')}
                disabled={isLoading}
                className="flex items-center justify-center gap-2 w-full rounded-lg bg-gray-50 border border-gray-200 px-4 py-2 text-xs font-medium text-gray-900 hover:bg-gray-100 disabled:opacity-50 transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                End User <span className="font-mono opacity-60">user@example.com</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
