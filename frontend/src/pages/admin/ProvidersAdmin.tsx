import { useEffect, useState } from 'react';
import {
  Globe, CheckCircle2, XCircle, Settings2, RefreshCw,
  Eye, EyeOff, AlertTriangle, Zap, ChevronDown, ChevronUp,
  Lock, ToggleLeft, ToggleRight,
} from 'lucide-react';
import { clsx } from 'clsx';
import {
  providersService, ProviderListItem, ProviderUsage, ProviderUpdatePayload,
} from '@/services/admin';

const PROVIDER_META: Record<string, { label: string; color: string; icon: string }> = {
  google:    { label: 'Google',    color: 'text-red-600 bg-red-50 border-red-100',     icon: 'G' },
  github:    { label: 'GitHub',    color: 'text-gray-800 bg-gray-100 border-gray-200', icon: '⌥' },
  microsoft: { label: 'Microsoft', color: 'text-blue-600 bg-blue-50 border-blue-100',  icon: 'M' },
  linkedin:  { label: 'LinkedIn',  color: 'text-sky-700 bg-sky-50 border-sky-100',     icon: 'in' },
};

export default function ProvidersAdmin() {
  const [providers, setProviders] = useState<ProviderListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [usages, setUsages] = useState<Record<string, ProviderUsage>>({});
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState<ProviderUpdatePayload>({});
  const [showSecret, setShowSecret] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await providersService.list();
      setProviders(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const loadUsage = async (provider: string) => {
    if (usages[provider]) return;
    try {
      const u = await providersService.usage(provider);
      setUsages(prev => ({ ...prev, [provider]: u }));
    } catch {}
  };

  const handleExpand = (p: string) => {
    if (expanded === p) {
      setExpanded(null);
      setEditing(null);
    } else {
      setExpanded(p);
      loadUsage(p);
    }
  };

  const handleToggle = async (p: ProviderListItem) => {
    setError(null);
    try {
      if (p.is_enabled) {
        await providersService.disable(p.provider);
        setSuccess(`${p.provider} disabled.`);
      } else {
        await providersService.enable(p.provider);
        setSuccess(`${p.provider} enabled.`);
      }
      setTimeout(() => setSuccess(null), 3000);
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to toggle provider.');
    }
  };

  const handleEdit = (p: ProviderListItem) => {
    setEditing(p.provider);
    setForm({ client_id: p.client_id || '', redirect_uri: p.redirect_uri || '', client_secret: '' });
  };

  const handleSave = async (provider: string) => {
    setSaving(true);
    setError(null);
    try {
      await providersService.update(provider, {
        client_id: form.client_id || undefined,
        client_secret: form.client_secret || undefined,
        redirect_uri: form.redirect_uri || undefined,
      });
      setSuccess('Provider credentials updated.');
      setTimeout(() => setSuccess(null), 3000);
      setEditing(null);
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to update provider.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Social Providers</h1>
          <p className="text-gray-500 text-sm mt-1">
            Manage OAuth2 credentials and availability for each social login provider.
          </p>
        </div>
        <button onClick={load} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Status messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {success}
        </div>
      )}

      {/* Provider cards */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card animate-pulse h-24 bg-gray-50" />
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {providers.map((p) => {
            const meta = PROVIDER_META[p.provider] || { label: p.provider, color: 'text-gray-600 bg-gray-50 border-gray-100', icon: '?' };
            const isOpen = expanded === p.provider;
            const isEditing = editing === p.provider;
            const usage = usages[p.provider];

            return (
              <div key={p.provider} className={clsx(
                'bg-white rounded-2xl border transition-all',
                isOpen ? 'border-primary-200 shadow-sm' : 'border-gray-100',
              )}>
                {/* Row */}
                <div className="flex items-center gap-4 px-6 py-4">
                  {/* Provider icon */}
                  <div className={clsx(
                    'w-12 h-12 rounded-xl border flex items-center justify-center font-bold text-lg shrink-0',
                    meta.color,
                  )}>
                    {meta.icon}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <h3 className="font-semibold text-gray-900">{meta.label}</h3>
                      <StatusBadge enabled={p.is_enabled} configured={p.configured} />
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                      <span className={clsx('font-mono', p.client_id ? 'text-gray-600' : 'italic')}>
                        {p.client_id ? `Client: ${p.client_id.slice(0, 24)}…` : 'No client ID configured'}
                      </span>
                      <span className="capitalize">Source: {p.source}</span>
                      {p.updated_at && <span>Updated {new Date(p.updated_at).toLocaleDateString()}</span>}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    {/* Toggle */}
                    <button
                      onClick={() => handleToggle(p)}
                      title={p.is_enabled ? 'Disable provider' : 'Enable provider'}
                      className={clsx(
                        'p-2 rounded-lg transition-colors',
                        p.is_enabled
                          ? 'text-green-600 hover:bg-green-50'
                          : 'text-gray-400 hover:bg-gray-100',
                      )}
                    >
                      {p.is_enabled ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />}
                    </button>
                    {/* Configure */}
                    <button
                      onClick={() => { handleExpand(p.provider); if (!isOpen) handleEdit(p); }}
                      className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
                    >
                      <Settings2 className="w-3.5 h-3.5" />
                      Configure
                    </button>
                    {/* Expand */}
                    <button
                      onClick={() => handleExpand(p.provider)}
                      className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg"
                    >
                      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Expanded panel */}
                {isOpen && (
                  <div className="border-t border-gray-100 px-6 py-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Edit credentials */}
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                        <Lock className="w-4 h-4 text-gray-400" />
                        OAuth2 Credentials
                      </h4>
                      {isEditing ? (
                        <div className="space-y-3">
                          <FormField
                            label="Client ID"
                            value={form.client_id || ''}
                            onChange={v => setForm(f => ({ ...f, client_id: v }))}
                            placeholder="e.g. 1234567890-abc.apps.googleusercontent.com"
                          />
                          <div>
                            <label className="label">Client Secret</label>
                            <div className="relative">
                              <input
                                type={showSecret ? 'text' : 'password'}
                                className="input pr-10"
                                value={form.client_secret || ''}
                                onChange={e => setForm(f => ({ ...f, client_secret: e.target.value }))}
                                placeholder={p.has_secret ? 'Leave blank to keep current' : 'Enter new secret'}
                              />
                              <button
                                type="button"
                                onClick={() => setShowSecret(v => !v)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                              >
                                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                              </button>
                            </div>
                            {p.has_secret && (
                              <p className="text-xs text-gray-400 mt-1">A secret is already stored. Leave blank to keep it.</p>
                            )}
                          </div>
                          <FormField
                            label="Redirect URI"
                            value={form.redirect_uri || ''}
                            onChange={v => setForm(f => ({ ...f, redirect_uri: v }))}
                            placeholder={p.env_redirect_uri || 'https://your-sso/auth/google/callback'}
                          />
                          <div className="flex gap-2 pt-2">
                            <button
                              className="btn-primary text-sm"
                              disabled={saving}
                              onClick={() => handleSave(p.provider)}
                            >
                              {saving ? 'Saving…' : 'Save credentials'}
                            </button>
                            <button
                              className="btn-secondary text-sm"
                              onClick={() => setEditing(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <InfoRow label="Client ID" value={p.client_id || '—'} mono />
                          <InfoRow label="Redirect URI" value={p.redirect_uri || p.env_redirect_uri || '—'} mono />
                          <InfoRow label="Secret stored" value={p.has_secret ? 'Yes (encrypted)' : 'No'} />
                          <InfoRow label="Config source" value={p.source === 'db' ? 'Database (overrides .env)' : '.env defaults'} />
                          <button
                            className="btn-secondary text-xs mt-2"
                            onClick={() => handleEdit(p)}
                          >
                            Edit credentials
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Usage stats */}
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                        <Zap className="w-4 h-4 text-gray-400" />
                        Usage — Last 30 Days
                      </h4>
                      {!usage ? (
                        <div className="text-sm text-gray-400 animate-pulse">Loading usage…</div>
                      ) : (
                        <div className="grid grid-cols-2 gap-3">
                          {[
                            { label: 'Logins',       value: usage.logins,        color: 'text-green-700 bg-green-50' },
                            { label: 'Registrations',value: usage.registrations,  color: 'text-blue-700 bg-blue-50' },
                            { label: 'Account Links',value: usage.account_links,  color: 'text-violet-700 bg-violet-50' },
                            { label: 'Failures',     value: usage.failures,       color: 'text-red-700 bg-red-50' },
                          ].map(s => (
                            <div key={s.label} className={`rounded-xl px-4 py-3 ${s.color}`}>
                              <p className="text-2xl font-bold">{s.value.toLocaleString()}</p>
                              <p className="text-xs font-medium mt-0.5 opacity-80">{s.label}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ enabled, configured }: { enabled: boolean; configured: boolean }) {
  if (!configured) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
        <XCircle className="w-3 h-3" /> Not configured
      </span>
    );
  }
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full',
      enabled ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600',
    )}>
      {enabled ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
      {enabled ? 'Enabled' : 'Disabled'}
    </span>
  );
}

function FormField({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      <input
        className="input font-mono text-xs"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
      <p className={clsx('text-sm text-gray-900 break-all', mono && 'font-mono text-xs')}>{value}</p>
    </div>
  );
}
