import { useEffect, useState } from 'react';
import api from '@/services/api';
import Alert from '@/components/Alert';
import { useAuthStore } from '@/store/authStore';
import { Briefcase, RefreshCw, Trash2 } from 'lucide-react';

interface OAuthClient {
  id: string;
  client_id: string;
  app_name: string;
  description: string | null;
  redirect_uris: string[];
  allowed_scopes: string[];
  is_active: boolean;
  created_at: string;
}

export default function Applications() {
  const { user } = useAuthStore();
  const [clients, setClients] = useState<OAuthClient[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (user?.is_superuser) {
      api.get('/v1/clients').then(({ data }) => setClients(data)).catch(() => setError('Failed to load clients'));
    }
  }, [user]);

  if (!user?.is_superuser) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Applications</h1>
        <div className="card text-center py-10 text-gray-400">
          <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p>Application management requires admin privileges.</p>
        </div>
      </div>
    );
  }

  const rotateSecret = async (id: string) => {
    const { data } = await api.post(`/v1/clients/${id}/rotate-secret`);
    setMessage(`New secret for ${data.app_name}: ${data.client_secret}`);
  };

  const deleteClient = async (id: string) => {
    await api.delete(`/v1/clients/${id}`);
    setClients((p) => p.filter((c) => c.id !== id));
    setMessage('Client deleted');
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">OAuth Applications</h1>
      {error && <Alert type="error" message={error} />}
      {message && <Alert type="info" message={message} onClose={() => setMessage('')} />}

      {clients.length === 0 ? (
        <div className="card text-center py-10 text-gray-400">No registered applications</div>
      ) : (
        <div className="space-y-4">
          {clients.map((c) => (
            <div key={c.id} className="card space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold">{c.app_name}</h3>
                  <p className="text-xs text-gray-400 font-mono">{c.client_id}</p>
                  {c.description && <p className="text-sm text-gray-500 mt-1">{c.description}</p>}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${c.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {c.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div>
                <p className="text-xs text-gray-500 mb-1">Redirect URIs</p>
                {c.redirect_uris.map((u) => (
                  <p key={u} className="text-xs font-mono text-gray-700">{u}</p>
                ))}
              </div>

              <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                <button onClick={() => rotateSecret(c.id)} className="btn-secondary text-xs gap-1">
                  <RefreshCw className="w-3 h-3" /> Rotate secret
                </button>
                <button onClick={() => deleteClient(c.id)} className="btn-secondary text-xs text-red-600 gap-1">
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
