import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { authService } from '@/services/auth';
import Alert from '@/components/Alert';

const schema = z.object({
  new_password: z.string().min(8),
  confirm: z.string(),
}).refine((d) => d.new_password === d.confirm, { message: "Passwords don't match", path: ['confirm'] });

type FormData = z.infer<typeof schema>;

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    setError('');
    try {
      await authService.resetPassword(token, data.new_password);
      navigate('/login', { state: { message: 'Password reset successfully. Please sign in.' } });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Reset failed. The link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-8">Set new password</h1>
        <div className="card space-y-4">
          {error && <Alert type="error" message={error} />}
          {!token && <Alert type="error" message="Invalid or missing reset token." />}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="label">New password</label>
              <input {...register('new_password')} type="password" className="input" placeholder="Min 8 characters" />
              {errors.new_password && <p className="text-red-500 text-xs mt-1">{errors.new_password.message}</p>}
            </div>
            <div>
              <label className="label">Confirm new password</label>
              <input {...register('confirm')} type="password" className="input" placeholder="Repeat password" />
              {errors.confirm && <p className="text-red-500 text-xs mt-1">{errors.confirm.message}</p>}
            </div>
            <button type="submit" disabled={loading || !token} className="btn-primary w-full">
              {loading ? 'Saving…' : 'Set new password'}
            </button>
          </form>
          <p className="text-center text-sm">
            <Link to="/login" className="text-primary-600 hover:underline">Back to sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
