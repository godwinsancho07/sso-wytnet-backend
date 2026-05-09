import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AdminSession,
  adminSessionsService,
  usersAdminService,
  AdminUserListItem,
} from '@/services/admin';
import Alert from '@/components/Alert';
import {
  RefreshCw,
  Search,
  Trash2,
  ShieldOff,
  X,
  Filter,
  Monitor,
  Globe,
  Clock,
} from 'lucide-react';

type StatusFilter = 'all' | 'active' | 'expired' | 'revoked';

const STATUS_OPTIONS: { label: string; value: StatusFilter }[] = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Expired', value: 'expired' },
  { label: 'Revoked', value: 'revoked' },
];

const PAGE_SIZE = 50;

function statusBadge(status: AdminSession['status']) {
  const styles: Record<AdminSession['status'], string> = {
    active: 'bg-green-100 text-green-700',
    expired: 'bg-amber-100 text-amber-700',
    revoked: 'bg-red-100 text-red-700',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status]}`}>
      {status}
    </span>
  );
}

function relativeTime(iso: string | null) {
  if (!iso) return '—';
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  if (days < 30) return `${days}d ago`;
  return d.toLocaleDateString();
}

function userInitials(email: string | null, fullName: string | null) {
  if (fullName) {
    const parts = fullName.trim().split(/\s+/);
    return (parts[0]?.[0] || '') + (parts[1]?.[0] || '');
  }
  return (email?.[0] || '?').toUpperCase();
}

interface UserPickerProps {
  selected: AdminUserListItem | null;
  onSelect: (u: AdminUserListItem | null) => void;
}

function UserAutocomplete({ selected, onSelect }: UserPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<AdminUserListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await usersAdminService.searchUsers(query || undefined, undefined, 0, 10);
        setResults(r.items);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [query, open]);

  return (
    <div ref={containerRef} className="relative">
      {selected ? (
        <div className="flex items-center gap-2 bg-primary-50 border border-primary-200 rounded-lg pl-2 pr-1 py-1">
          <div className="w-6 h-6 rounded-full bg-primary-600 text-white text-[10px] font-semibold flex items-center justify-center">
            {userInitials(selected.email, selected.full_name)}
          </div>
          <span className="text-sm text-gray-800 truncate max-w-[180px]">
            {selected.email}
          </span>
          <button
            onClick={() => onSelect(null)}
            className="p-1 rounded hover:bg-primary-100 text-primary-700"
            aria-label="Clear filter"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-1.5 w-72">
          <Search className="w-4 h-4 text-gray-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setOpen(true)}
            placeholder="Filter by user (email or name)"
            className="flex-1 text-sm outline-none bg-transparent"
          />
        </div>
      )}

      {open && !selected && (
        <div className="absolute z-30 mt-1 w-72 bg-white border border-gray-200 rounded-lg shadow-lg max-h-72 overflow-auto">
          {loading ? (
            <div className="p-4 text-center text-xs text-gray-400">Searching…</div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-400">No users.</div>
          ) : (
            results.map((u) => (
              <button
                key={u.id}
                onClick={() => {
                  onSelect(u);
                  setOpen(false);
                  setQuery('');
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

export default function SessionsAdmin() {
  const [items, setItems] = useState<AdminSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [user, setUser] = useState<AdminUserListItem | null>(null);
  const [offset, setOffset] = useState(0);
  const [count, setCount] = useState(0);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await adminSessionsService.list({
        user_id: user?.id,
        status: statusFilter === 'all' ? undefined : statusFilter,
        offset,
        limit: PAGE_SIZE,
      });
      setItems(r.items);
      setCount(r.count);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, user?.id, offset]);

  useEffect(() => {
    setOffset(0);
  }, [statusFilter, user?.id]);

  const handleRevoke = async (s: AdminSession) => {
    if (!confirm(`Revoke this session for ${s.user_email}?`)) return;
    try {
      await adminSessionsService.revoke(s.id);
      setSuccess('Session revoked.');
      load();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to revoke session');
    }
  };

  const handleRevokeAllForUser = async () => {
    if (!user) return;
    if (
      !confirm(
        `Revoke ALL sessions and refresh tokens for ${user.email}? They will be signed out everywhere.`,
      )
    )
      return;
    try {
      const r = await adminSessionsService.revokeAllForUser(user.id);
      setSuccess(
        `Revoked ${r.revoked_sessions} session(s) and ${r.revoked_refresh_tokens} refresh token(s).`,
      );
      load();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to revoke user sessions');
    }
  };

  const counters = useMemo(() => {
    return {
      total: items.length,
      active: items.filter((i) => i.status === 'active').length,
      revoked: items.filter((i) => i.status === 'revoked').length,
    };
  }, [items]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sessions</h1>
          <p className="text-gray-500 text-sm mt-1">
            All active and historical sessions across every user.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="btn-secondary text-xs gap-1">
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          {user && (
            <button
              onClick={handleRevokeAllForUser}
              className="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 inline-flex items-center gap-1"
            >
              <ShieldOff className="w-3.5 h-3.5" /> Revoke all for this user
            </button>
          )}
        </div>
      </div>

      {error && <Alert type="error" message={error} />}
      {success && <Alert type="success" message={success} />}

      <div className="card flex flex-col lg:flex-row lg:items-center gap-4 p-4">
        <UserAutocomplete selected={user} onSelect={setUser} />

        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-gray-400" />
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
                statusFilter === opt.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex gap-4 text-xs text-gray-500">
          <span>
            Showing <strong className="text-gray-800">{counters.total}</strong>
          </span>
          <span>
            Active <strong className="text-green-700">{counters.active}</strong>
          </span>
          <span>
            Revoked <strong className="text-red-700">{counters.revoked}</strong>
          </span>
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-600 uppercase">
            <tr>
              <th className="text-left p-3">User</th>
              <th className="text-left p-3">Device</th>
              <th className="text-left p-3">IP</th>
              <th className="text-left p-3">Created</th>
              <th className="text-left p-3">Last active</th>
              <th className="text-left p-3">Expires</th>
              <th className="text-left p-3">Status</th>
              <th className="text-right p-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-gray-400">
                  Loading sessions…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-gray-400">
                  No sessions match your filters.
                </td>
              </tr>
            ) : (
              items.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50 align-top">
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      {s.user_avatar_url ? (
                        <img
                          src={s.user_avatar_url}
                          alt=""
                          className="w-8 h-8 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-700 text-xs font-semibold flex items-center justify-center">
                          {userInitials(s.user_email, s.user_full_name)}
                        </div>
                      )}
                      <div className="min-w-0">
                        <div className="text-sm text-gray-800 truncate max-w-[180px]">
                          {s.user_email || '—'}
                        </div>
                        {s.user_full_name && (
                          <div className="text-xs text-gray-500 truncate max-w-[180px]">
                            {s.user_full_name}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="p-3 text-xs text-gray-700 max-w-[180px]">
                    <div className="flex items-start gap-1.5">
                      <Monitor className="w-3.5 h-3.5 text-gray-400 mt-0.5 shrink-0" />
                      <span className="truncate" title={s.user_agent || ''}>
                        {s.device_info || s.user_agent || '—'}
                      </span>
                    </div>
                  </td>
                  <td className="p-3 font-mono text-xs text-gray-700">
                    <div className="flex items-center gap-1">
                      <Globe className="w-3 h-3 text-gray-400" />
                      {s.ip_address || '—'}
                    </div>
                  </td>
                  <td className="p-3 text-xs text-gray-500 whitespace-nowrap">
                    {relativeTime(s.created_at)}
                  </td>
                  <td className="p-3 text-xs text-gray-500 whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-gray-400" />
                      {relativeTime(s.last_active_at)}
                    </div>
                  </td>
                  <td className="p-3 text-xs text-gray-500 whitespace-nowrap">
                    {s.expires_at ? new Date(s.expires_at).toLocaleString() : '—'}
                  </td>
                  <td className="p-3">{statusBadge(s.status)}</td>
                  <td className="p-3 text-right">
                    {s.status === 'active' ? (
                      <button
                        onClick={() => handleRevoke(s)}
                        className="text-xs inline-flex items-center gap-1 text-red-600 hover:text-red-700 hover:underline"
                      >
                        <Trash2 className="w-3.5 h-3.5" /> Revoke
                      </button>
                    ) : (
                      <span className="text-xs text-gray-300">—</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>
          Page {Math.floor(offset / PAGE_SIZE) + 1} · {count} on this page
        </span>
        <div className="flex gap-2">
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            className="btn-secondary text-xs disabled:opacity-40"
          >
            Previous
          </button>
          <button
            disabled={count < PAGE_SIZE}
            onClick={() => setOffset(offset + PAGE_SIZE)}
            className="btn-secondary text-xs disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
