import { useEffect, useState } from 'react';
import api from '@/services/api';
import {
  Briefcase, KeyRound, Users, Activity, RefreshCw, ChevronDown, Copy, CheckCircle,
} from 'lucide-react';
import { clsx } from 'clsx';
import { appAdminService, AppOverview, AppUser } from '@/services/admin';

interface OwnedClient {
  id: string;
  client_id: string;
  app_name: string;
  description: string | null;
  redirect_uris: string[];
  allowed_scopes: string[];
  is_active: boolean;
}

export default function AppAdminDashboard() {
  const [clients, setClients] = useState<OwnedClient[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<AppOverview | null>(null);
  const [users, setUsers] = useState<AppUser[]>([]);
  const [secret, setSecret] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get<OwnedClient[]>('/v1/clients').then((r) => {
      setClients(r.data);
      if (r.data.length) setSelectedId(r.data[0].id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setMetrics(null);
    setUsers([]);
    appAdminService.getMetrics(selectedId).then(setMetrics).catch(() => {});
    appAdminService.getRecentUsers(selectedId).then(setUsers).catch(() => {});
  }, [selectedId]);

  const rotate = async () => {
    if (!selectedId) return;
    const { data } = await api.post(`/v1/clients/${selectedId}/rotate-secret`);
    setSecret(data.client_secret);
    setCopied(false);
  };

  const copy = () => {
    if (!secret) return;
    navigator.clipboard.writeText(secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const selected = clients.find((c) => c.id === selectedId);

  if (clients.length === 0) {
    return (
      <div className="card text-center py-12 text-gray-400 max-w-2xl mx-auto">
        <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p>You don't own any OAuth applications yet.</p>
        <p className="text-xs mt-1">A platform admin must assign you to a client.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">App Administration</h1>
        <p className="text-gray-500 text-sm mt-1">
          Token usage and user activity for the apps you own.
        </p>
      </div>

      <div className="card">
        <label className="text-xs text-gray-500 uppercase tracking-wide block mb-2">Application</label>
        <div className="relative">
          <select
            value={selectedId || ''}
            onChange={(e) => setSelectedId(e.target.value)}
            className="input appearance-none pr-10"
          >
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.app_name} ({c.client_id})</option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {selected && (
        <>
          {secret && (
            <div className="card bg-amber-50 border-amber-200 space-y-2">
              <p className="text-sm font-semibold text-amber-900">New client secret</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 break-all text-xs bg-white p-2 rounded border border-amber-200">{secret}</code>
                <button onClick={copy} className="btn-secondary text-xs gap-1 shrink-0">
                  {copied ? <CheckCircle className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <p className="text-xs text-amber-700">Save this now — it will not be shown again.</p>
              <button onClick={() => setSecret(null)} className="text-xs text-amber-700 hover:underline">
                Dismiss
              </button>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPI icon={<Users className="w-5 h-5" />} label="Authorized users" value={metrics?.authorized_users} />
            <KPI icon={<KeyRound className="w-5 h-5" />} label="Active tokens" value={metrics?.active_tokens} />
            <KPI icon={<Activity className="w-5 h-5" />} label="Tokens (24h)" value={metrics?.tokens_24h} />
            <KPI icon={<Activity className="w-5 h-5" />} label="Tokens (7d)" value={metrics?.tokens_7d} />
          </div>

          <div className="card space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{selected.app_name}</h3>
                <p className="text-xs text-gray-400 font-mono">{selected.client_id}</p>
                {selected.description && (
                  <p className="text-sm text-gray-500 mt-1">{selected.description}</p>
                )}
              </div>
              <span className={clsx(
                'text-xs px-2 py-0.5 rounded-full',
                selected.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500',
              )}>
                {selected.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>

            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Redirect URIs</p>
              <div className="space-y-1">
                {selected.redirect_uris.map((u) => (
                  <p key={u} className="text-xs font-mono text-gray-700 bg-gray-50 px-2 py-1 rounded">{u}</p>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Allowed scopes</p>
              <div className="flex gap-1.5 flex-wrap">
                {selected.allowed_scopes.map((s) => (
                  <span key={s} className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded">{s}</span>
                ))}
              </div>
            </div>

            <div className="pt-2 border-t border-gray-100">
              <button onClick={rotate} className="btn-secondary text-xs gap-1">
                <RefreshCw className="w-3 h-3" /> Rotate client secret
              </button>
            </div>
          </div>

          <div className="card">
            <h2 className="font-semibold mb-3">Recent users</h2>
            {users.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-6">
                No users have used this app yet.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="text-left pb-2">User</th>
                    <th className="text-right pb-2">Last seen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map((u) => (
                    <tr key={u.user_id}>
                      <td className="py-2">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-semibold">
                            {(u.full_name || u.email)[0].toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm">{u.full_name || u.email}</p>
                            <p className="text-xs text-gray-400">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-2 text-right text-xs text-gray-500">
                        {u.last_seen ? new Date(u.last_seen).toLocaleString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function KPI({
  icon, label, value,
}: { icon: React.ReactNode; label: string; value?: number }) {
  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-2">
        <div className="rounded-lg bg-primary-50 p-2 text-primary-600">{icon}</div>
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      </div>
      <p className="text-2xl font-bold text-gray-900">
        {value === undefined ? <span className="text-gray-300">—</span> : value.toLocaleString()}
      </p>
    </div>
  );
}
