import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useAuthStore } from '@/store/authStore';
import { userService, SocialAccount } from '@/services/auth';
import Alert from '@/components/Alert';
import { Trash2 } from 'lucide-react';

export default function Profile() {
  const { user, fetchUser } = useAuthStore();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const { register, handleSubmit, reset } = useForm({
    defaultValues: { full_name: user?.full_name || '', avatar_url: user?.avatar_url || '' },
  });

  useEffect(() => {
    if (user) reset({ full_name: user.full_name || '', avatar_url: user.avatar_url || '' });
    userService.getSocialAccounts().then(setAccounts);
  }, [user]);

  const onSubmit = async (data: any) => {
    setError(''); setSuccess('');
    try {
      await userService.updateProfile(data);
      await fetchUser();
      setSuccess('Profile updated');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Update failed');
    }
  };

  const unlink = async (provider: string) => {
    await userService.unlinkSocialAccount(provider);
    setAccounts((prev) => prev.filter((a) => a.provider !== provider));
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Profile</h1>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-800">Personal information</h2>
        {success && <Alert type="success" message={success} />}
        {error && <Alert type="error" message={error} />}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input className="input bg-gray-50" value={user?.email || ''} disabled />
            <p className="text-xs text-gray-400 mt-1">
              {user?.email_verified ? '✓ Verified' : '⚠ Not verified'}
            </p>
          </div>
          <div>
            <label className="label">Full name</label>
            <input {...register('full_name')} className="input" placeholder="Your full name" />
          </div>
          <div>
            <label className="label">Avatar URL</label>
            <input {...register('avatar_url')} className="input" placeholder="https://..." />
          </div>
          <button type="submit" className="btn-primary">Save changes</button>
        </form>
      </div>

      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-800">Linked social accounts</h2>
        {accounts.length === 0 ? (
          <p className="text-sm text-gray-500">No social accounts linked.</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {accounts.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium capitalize text-sm">{a.provider}</p>
                  <p className="text-xs text-gray-400">{a.provider_email || 'No email'}</p>
                </div>
                <button
                  onClick={() => unlink(a.provider)}
                  className="text-red-500 hover:text-red-700 text-sm flex items-center gap-1"
                >
                  <Trash2 className="w-4 h-4" /> Unlink
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
