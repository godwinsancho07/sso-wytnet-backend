import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { authService } from '@/services/auth';
import { useAuthStore } from '@/store/authStore';
import Alert from '@/components/Alert';

const schema = z.object({
  current_password: z.string().min(1, 'Current password is required'),
  new_password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm: z.string(),
}).refine((d) => d.new_password === d.confirm, {
  message: "Passwords don't match",
  path: ['confirm'],
});

type FormData = z.infer<typeof schema>;

export default function Security() {
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { globalLogout } = useAuthStore();
  const navigate = useNavigate();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setLoading(true); setError(''); setSuccess('');
    try {
      await authService.changePassword(data.current_password, data.new_password);
      setSuccess('Password changed. Please sign in again.');
      reset();
      setTimeout(() => navigate('/login'), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Password change failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGlobalLogout = async () => {
    await globalLogout();
    navigate('/login');
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Security</h1>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-800">Change password</h2>
        {success && <Alert type="success" message={success} />}
        {error && <Alert type="error" message={error} />}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Current password</label>
            <input {...register('current_password')} type="password" className="input" />
            {errors.current_password && <p className="text-red-500 text-xs mt-1">{errors.current_password.message}</p>}
          </div>
          <div>
            <label className="label">New password</label>
            <input {...register('new_password')} type="password" className="input" />
            {errors.new_password && <p className="text-red-500 text-xs mt-1">{errors.new_password.message}</p>}
          </div>
          <div>
            <label className="label">Confirm new password</label>
            <input {...register('confirm')} type="password" className="input" />
            {errors.confirm && <p className="text-red-500 text-xs mt-1">{errors.confirm.message}</p>}
          </div>
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Changing…' : 'Change password'}
          </button>
        </form>
      </div>

      <div className="card space-y-3 border-red-100">
        <h2 className="font-semibold text-gray-800">Danger zone</h2>
        <p className="text-sm text-gray-500">
          Sign out from all devices and revoke all active sessions.
        </p>
        <button onClick={handleGlobalLogout} className="btn-secondary text-red-600 border-red-200">
          Sign out everywhere
        </button>
      </div>
    </div>
  );
}
