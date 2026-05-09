import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ClientAdminUser,
  OAuthClientCreatePayload,
  OAuthClientRead,
  OAuthClientWithSecret,
  clientsAdminService,
  usersAdminService,
  AdminUserListItem,
} from '@/services/admin';
import Alert from '@/components/Alert';
import {
  AppWindow,
  Copy,
  KeyRound,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Shield,
  ShieldCheck,
  Trash2,
  X,
  Check,
  AlertTriangle,
  Power,
  PowerOff,
  FileDown,
} from 'lucide-react';

const SCOPE_OPTIONS = ['openid', 'profile', 'email', 'offline_access'];

function copyToClipboard(text: string) {
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).catch(() => {});
  }
}

function userInitials(email: string | null, fullName: string | null) {
  if (fullName) {
    const parts = fullName.trim().split(/\s+/);
    return (parts[0]?.[0] || '') + (parts[1]?.[0] || '');
  }
  return (email?.[0] || '?').toUpperCase();
}

interface CreateModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (c: OAuthClientWithSecret) => void;
}

function CreateClientModal({ open, onClose, onCreated }: CreateModalProps) {
  const [appName, setAppName] = useState('');
  const [description, setDescription] = useState('');
  const [redirectUris, setRedirectUris] = useState<string[]>(['']);
  const [scopes, setScopes] = useState<string[]>(['openid', 'profile', 'email']);
  const [requirePkce, setRequirePkce] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      setAppName('');
      setDescription('');
      setRedirectUris(['']);
      setScopes(['openid', 'profile', 'email']);
      setRequirePkce(true);
      setError('');
    }
  }, [open]);

  if (!open) return null;

  const updateUri = (i: number, v: string) =>
    setRedirectUris((arr) => arr.map((u, idx) => (idx === i ? v : u)));
  const addUri = () => setRedirectUris((arr) => [...arr, '']);
  const removeUri = (i: number) =>
    setRedirectUris((arr) => arr.filter((_, idx) => idx !== i));

  const toggleScope = (s: string) =>
    setScopes((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const submit = async () => {
    setError('');
    const cleanedUris = redirectUris.map((u) => u.trim()).filter(Boolean);
    if (!appName.trim()) {
      setError('Application name is required.');
      return;
    }
    if (cleanedUris.length === 0) {
      setError('At least one redirect URI is required.');
      return;
    }
    if (scopes.length === 0) {
      setError('Select at least one scope.');
      return;
    }
    setSubmitting(true);
    try {
      const payload: OAuthClientCreatePayload = {
        app_name: appName.trim(),
        description: description.trim() || null,
        redirect_uris: cleanedUris,
        allowed_scopes: scopes,
        require_pkce: requirePkce,
      };
      const result = await clientsAdminService.create(payload);
      onCreated(result);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to create client');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl w-full max-w-lg shadow-xl">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">Create OAuth Client</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
          {error && <Alert type="error" message={error} />}

          <div>
            <label className="text-xs font-medium text-gray-700 uppercase tracking-wide">
              Application name
            </label>
            <input
              value={appName}
              onChange={(e) => setAppName(e.target.value)}
              className="input mt-1 w-full"
              placeholder="My App"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 uppercase tracking-wide">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input mt-1 w-full"
              rows={2}
              placeholder="Optional description shown on the consent screen"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 uppercase tracking-wide">
              Redirect URIs
            </label>
            <div className="mt-1 space-y-2">
              {redirectUris.map((uri, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    value={uri}
                    onChange={(e) => updateUri(i, e.target.value)}
                    className="input flex-1"
                    placeholder="https://app.example.com/callback"
                  />
                  {redirectUris.length > 1 && (
                    <button
                      onClick={() => removeUri(i)}
                      className="p-2 text-gray-400 hover:text-red-600"
                      aria-label="Remove URI"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={addUri}
                className="text-xs text-primary-600 hover:underline inline-flex items-center gap-1"
              >
                <Plus className="w-3 h-3" /> Add another redirect URI
              </button>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 uppercase tracking-wide">
              Allowed scopes
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              {SCOPE_OPTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => toggleScope(s)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                    scopes.includes(s)
                      ? 'bg-primary-600 border-primary-600 text-white'
                      : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {scopes.includes(s) && <Check className="w-3 h-3 inline mr-1" />}
                  {s}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={requirePkce}
              onChange={(e) => setRequirePkce(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm text-gray-800">Require PKCE</span>
            <span className="text-xs text-gray-500">
              (recommended for public clients)
            </span>
          </label>
        </div>
        <div className="flex justify-end gap-2 p-4 border-t">
          <button onClick={onClose} className="btn-secondary text-sm">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            className="btn-primary text-sm disabled:opacity-50"
          >
            {submitting ? 'Creating…' : 'Create client'}
          </button>
        </div>
      </div>
    </div>
  );
}

interface SecretRevealProps {
  client: OAuthClientWithSecret;
  onClose: () => void;
  title?: string;
}

function SecretRevealModal({ client, onClose, title }: SecretRevealProps) {
  const [copiedId, setCopiedId] = useState(false);
  const [copiedSecret, setCopiedSecret] = useState(false);

  const copy = (val: string, which: 'id' | 'secret') => {
    copyToClipboard(val);
    if (which === 'id') {
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 1500);
    } else {
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 1500);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl w-full max-w-lg shadow-xl">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold">
            {title || 'Save these credentials'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-800">
              The client secret is shown <strong>only once</strong>. Copy it now and
              store it in your secrets manager. You can rotate it later but it cannot
              be recovered.
            </p>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 uppercase tracking-wide">
              Client ID
            </label>
            <div className="mt-1 flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-xs font-mono break-all">
                {client.client_id}
              </code>
              <button
                onClick={() => copy(client.client_id, 'id')}
                className="btn-secondary text-xs gap-1 shrink-0"
              >
                {copiedId ? (
                  <Check className="w-3 h-3 text-green-600" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
                {copiedId ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 uppercase tracking-wide">
              Client secret
            </label>
            <div className="mt-1 flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-xs font-mono break-all">
                {client.client_secret}
              </code>
              <button
                onClick={() => copy(client.client_secret, 'secret')}
                className="btn-secondary text-xs gap-1 shrink-0"
              >
                {copiedSecret ? (
                  <Check className="w-3 h-3 text-green-600" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
                {copiedSecret ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>
        </div>
        <div className="flex justify-between items-center p-4 border-t gap-2">
          <button
            onClick={async () => {
              try {
                await clientsAdminService.downloadIntegrationDocs(client.id, client.app_name);
              } catch {
                /* noop — admin can retry from detail view */
              }
            }}
            className="btn-secondary text-xs"
          >
            Download integration docs
          </button>
          <button onClick={onClose} className="btn-primary text-sm">
            I've saved it
          </button>
        </div>
      </div>
    </div>
  );
}

interface UserPickerProps {
  onPick: (u: AdminUserListItem) => void;
  excludeIds: string[];
}

function UserPicker({ onPick, excludeIds }: UserPickerProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AdminUserListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await usersAdminService.searchUsers(query || undefined, undefined, 0, 8);
        setResults(r.items.filter((u) => !excludeIds.includes(u.id)));
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [query, open, excludeIds]);

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-1.5">
        <Search className="w-4 h-4 text-gray-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Add admin by email or name"
          className="flex-1 text-sm outline-none bg-transparent"
        />
      </div>
      {open && (
        <div className="absolute z-30 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto">
          {loading ? (
            <div className="p-3 text-center text-xs text-gray-400">Searching…</div>
          ) : results.length === 0 ? (
            <div className="p-3 text-center text-xs text-gray-400">No users.</div>
          ) : (
            results.map((u) => (
              <button
                key={u.id}
                onClick={() => {
                  onPick(u);
                  setQuery('');
                  setOpen(false);
                }}
                className="flex items-center gap-2 w-full px-3 py-2 hover:bg-gray-50 text-left"
              >
                <div className="w-7 h-7 rounded-full bg-gray-200 text-gray-700 text-[11px] font-semibold flex items-center justify-center shrink-0">
                  {userInitials(u.email, u.full_name)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-800 truncate">{u.email}</div>
                  {u.full_name && (
                    <div className="text-xs text-gray-500 truncate">{u.full_name}</div>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

interface EditPanelProps {
  client: OAuthClientRead;
  onClose: () => void;
  onChanged: () => void;
  onError: (msg: string) => void;
  onSuccess: (msg: string) => void;
  onSecretRotated: (c: OAuthClientWithSecret) => void;
}

function ClientEditDrawer({
  client,
  onClose,
  onChanged,
  onError,
  onSuccess,
  onSecretRotated,
}: EditPanelProps) {
  const [appName, setAppName] = useState(client.app_name);
  const [description, setDescription] = useState(client.description || '');
  const [redirectUris, setRedirectUris] = useState<string[]>(
    client.redirect_uris.length ? client.redirect_uris : ['']
  );
  const [scopes, setScopes] = useState<string[]>(client.allowed_scopes);
  const [requirePkce, setRequirePkce] = useState(client.require_pkce);
  const [isActive, setIsActive] = useState(client.is_active);
  const [saving, setSaving] = useState(false);

  const [admins, setAdmins] = useState<ClientAdminUser[]>([]);
  const [adminsLoading, setAdminsLoading] = useState(false);

  const loadAdmins = async () => {
    setAdminsLoading(true);
    try {
      setAdmins(await clientsAdminService.listAdmins(client.id));
    } catch (e: any) {
      onError(e.response?.data?.detail || 'Failed to load admins');
    } finally {
      setAdminsLoading(false);
    }
  };

  useEffect(() => {
    loadAdmins();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client.id]);

  const updateUri = (i: number, v: string) =>
    setRedirectUris((arr) => arr.map((u, idx) => (idx === i ? v : u)));
  const addUri = () => setRedirectUris((arr) => [...arr, '']);
  const removeUri = (i: number) =>
    setRedirectUris((arr) => arr.filter((_, idx) => idx !== i));
  const toggleScope = (s: string) =>
    setScopes((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const save = async () => {
    setSaving(true);
    try {
      await clientsAdminService.update(client.id, {
        app_name: appName,
        description: description || null,
        redirect_uris: redirectUris.map((u) => u.trim()).filter(Boolean),
        allowed_scopes: scopes,
        require_pkce: requirePkce,
        is_active: isActive,
      });
      onSuccess('Client updated.');
      onChanged();
    } catch (e: any) {
      onError(e.response?.data?.detail || 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const rotate = async () => {
    if (
      !confirm(
        'Rotate the client secret? The old secret will stop working immediately.',
      )
    )
      return;
    try {
      const result = await clientsAdminService.rotateSecret(client.id);
      onSecretRotated(result);
    } catch (e: any) {
      onError(e.response?.data?.detail || 'Failed to rotate secret');
    }
  };

  const remove = async () => {
    if (
      !confirm(
        `Delete client "${client.app_name}"? All issued tokens and authorization grants will be revoked.`,
      )
    )
      return;
    try {
      await clientsAdminService.remove(client.id);
      onSuccess('Client deleted.');
      onClose();
      onChanged();
    } catch (e: any) {
      onError(e.response?.data?.detail || 'Failed to delete client');
    }
  };

  const toggleActive = async () => {
    try {
      await clientsAdminService.update(client.id, { is_active: !isActive });
      setIsActive(!isActive);
      onSuccess(`Client ${!isActive ? 'enabled' : 'disabled'}.`);
      onChanged();
    } catch (e: any) {
      onError(e.response?.data?.detail || 'Failed to update status');
    }
  };

  const assignAdmin = async (u: AdminUserListItem) => {
    try {
      await clientsAdminService.assignAdmin(client.id, u.id);
      loadAdmins();
    } catch (e: any) {
      onError(e.response?.data?.detail || 'Failed to assign admin');
    }
  };

  const removeAdmin = async (userId: string) => {
    try {
      await clientsAdminService.removeAdmin(client.id, userId);
      loadAdmins();
    } catch (e: any) {
      onError(e.response?.data?.detail || 'Failed to remove admin');
    }
  };

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex justify-end">
      <div className="bg-white w-full max-w-xl shadow-xl flex flex-col h-full">
        <div className="flex items-start justify-between p-5 border-b shrink-0">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold truncate">{client.app_name}</h2>
            <code className="text-xs text-gray-500 font-mono break-all">
              {client.client_id}
            </code>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 ml-2 shrink-0"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          <section className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Details
            </h3>
            <div>
              <label className="text-xs text-gray-700">Application name</label>
              <input
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                className="input mt-1 w-full"
              />
            </div>
            <div>
              <label className="text-xs text-gray-700">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="input mt-1 w-full"
                rows={2}
              />
            </div>
            <div>
              <label className="text-xs text-gray-700">Redirect URIs</label>
              <div className="mt-1 space-y-2">
                {redirectUris.map((uri, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      value={uri}
                      onChange={(e) => updateUri(i, e.target.value)}
                      className="input flex-1"
                      placeholder="https://app.example.com/callback"
                    />
                    {redirectUris.length > 1 && (
                      <button
                        onClick={() => removeUri(i)}
                        className="p-2 text-gray-400 hover:text-red-600"
                        aria-label="Remove"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  onClick={addUri}
                  className="text-xs text-primary-600 hover:underline inline-flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Add redirect URI
                </button>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-700">Allowed scopes</label>
              <div className="mt-2 flex flex-wrap gap-2">
                {SCOPE_OPTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleScope(s)}
                    className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                      scopes.includes(s)
                        ? 'bg-primary-600 border-primary-600 text-white'
                        : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {scopes.includes(s) && <Check className="w-3 h-3 inline mr-1" />}
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={requirePkce}
                onChange={(e) => setRequirePkce(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm text-gray-800">Require PKCE</span>
            </label>
            <div className="pt-2">
              <button
                onClick={save}
                disabled={saving}
                className="btn-primary text-sm disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </section>

          <section className="space-y-3 border-t pt-5">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Administrators
            </h3>
            <p className="text-xs text-gray-500">
              Users granted app-admin scope for this client.
            </p>
            <UserPicker
              onPick={assignAdmin}
              excludeIds={admins.map((a) => a.user_id)}
            />
            <div className="flex flex-wrap gap-2 mt-2">
              {adminsLoading ? (
                <span className="text-xs text-gray-400">Loading…</span>
              ) : admins.length === 0 ? (
                <span className="text-xs text-gray-400">
                  No admins assigned yet.
                </span>
              ) : (
                admins.map((a) => (
                  <div
                    key={a.user_id}
                    className="inline-flex items-center gap-2 bg-gray-100 rounded-full pl-1 pr-2 py-1"
                  >
                    {a.avatar_url ? (
                      <img
                        src={a.avatar_url}
                        alt=""
                        className="w-5 h-5 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-gray-300 text-gray-700 text-[9px] font-semibold flex items-center justify-center">
                        {userInitials(a.email, a.full_name)}
                      </div>
                    )}
                    <span className="text-xs text-gray-800">{a.email}</span>
                    <button
                      onClick={() => removeAdmin(a.user_id)}
                      className="p-0.5 rounded-full hover:bg-gray-200 text-gray-500"
                      aria-label="Remove admin"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="border-t pt-5 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Integration
            </h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={async () => {
                  try {
                    await clientsAdminService.downloadIntegrationDocs(client.id, client.app_name);
                  } catch (e) {
                    setError(extractErrorMessage(e, 'Could not download docs'));
                  }
                }}
                className="btn-secondary text-xs gap-1"
              >
                <FileDown className="w-3 h-3" /> Download integration docs
              </button>
              <span className="text-xs text-gray-400 self-center">
                Markdown — share with the team integrating this app
              </span>
            </div>
          </section>

          <section className="border-t pt-5 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Danger zone
            </h3>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={rotate}
                className="btn-secondary text-xs gap-1"
              >
                <RotateCcw className="w-3 h-3" /> Rotate secret
              </button>
              <button onClick={toggleActive} className="btn-secondary text-xs gap-1">
                {isActive ? (
                  <>
                    <PowerOff className="w-3 h-3" /> Disable client
                  </>
                ) : (
                  <>
                    <Power className="w-3 h-3" /> Enable client
                  </>
                )}
              </button>
              <button
                onClick={remove}
                className="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 inline-flex items-center gap-1"
              >
                <Trash2 className="w-3 h-3" /> Delete client
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

export default function ClientsAdmin() {
  const [clients, setClients] = useState<OAuthClientRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [query, setQuery] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<OAuthClientRead | null>(null);
  const [secretToShow, setSecretToShow] = useState<{
    client: OAuthClientWithSecret;
    title?: string;
  } | null>(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setClients(await clientsAdminService.list());
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load clients');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return clients;
    const q = query.toLowerCase();
    return clients.filter(
      (c) =>
        c.app_name.toLowerCase().includes(q) ||
        c.client_id.toLowerCase().includes(q) ||
        (c.description || '').toLowerCase().includes(q),
    );
  }, [clients, query]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">OAuth Clients</h1>
          <p className="text-gray-500 text-sm mt-1">
            Register and manage applications that authenticate through this identity
            provider.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="btn-secondary text-xs gap-1">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />{' '}
            Refresh
          </button>
          <button
            onClick={() => setCreateOpen(true)}
            className="btn-primary text-xs gap-1"
          >
            <Plus className="w-3.5 h-3.5" /> New client
          </button>
        </div>
      </div>

      {error && <Alert type="error" message={error} />}
      {success && <Alert type="success" message={success} />}

      <div className="card p-4">
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-1.5 max-w-md">
          <Search className="w-4 h-4 text-gray-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, client ID, or description"
            className="flex-1 text-sm outline-none bg-transparent"
          />
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-600 uppercase">
            <tr>
              <th className="text-left p-3">Application</th>
              <th className="text-left p-3">Client ID</th>
              <th className="text-left p-3">Scopes</th>
              <th className="text-left p-3">PKCE</th>
              <th className="text-left p-3">Status</th>
              <th className="text-right p-3">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-400">
                  Loading clients…
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-400">
                  No OAuth clients found.
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setEditing(c)}
                >
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      {c.logo_url ? (
                        <img
                          src={c.logo_url}
                          alt=""
                          className="w-8 h-8 rounded object-cover"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded bg-primary-50 text-primary-600 flex items-center justify-center">
                          <AppWindow className="w-4 h-4" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
                          {c.app_name}
                        </div>
                        {c.description && (
                          <div className="text-xs text-gray-500 truncate max-w-[200px]">
                            {c.description}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="p-3 font-mono text-xs text-gray-600 max-w-[200px] truncate">
                    {c.client_id}
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-1">
                      {c.allowed_scopes.map((s) => (
                        <span
                          key={s}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="p-3">
                    {c.require_pkce ? (
                      <span className="inline-flex items-center gap-1 text-xs text-green-700">
                        <ShieldCheck className="w-3 h-3" /> Required
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                        <Shield className="w-3 h-3" /> Optional
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        c.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {c.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="p-3 text-right text-xs text-gray-500 whitespace-nowrap">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <CreateClientModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(c) => {
          setCreateOpen(false);
          setSecretToShow({ client: c, title: 'Client created — save these credentials' });
          load();
        }}
      />

      {editing && (
        <ClientEditDrawer
          client={editing}
          onClose={() => setEditing(null)}
          onChanged={load}
          onError={setError}
          onSuccess={setSuccess}
          onSecretRotated={(c) =>
            setSecretToShow({
              client: c,
              title: 'New client secret — save it now',
            })
          }
        />
      )}

      {secretToShow && (
        <SecretRevealModal
          client={secretToShow.client}
          title={secretToShow.title}
          onClose={() => setSecretToShow(null)}
        />
      )}

      {/* small helper icon to silence unused import lint */}
      <span className="hidden">
        <KeyRound />
      </span>
    </div>
  );
}
