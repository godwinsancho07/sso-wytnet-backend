import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, CheckCircle2, XCircle, ShieldAlert, MailWarning,
  ChevronLeft, ChevronRight, Loader2,
} from 'lucide-react';
import { clsx } from 'clsx';

import Alert from '@/components/Alert';
import { extractErrorMessage } from '@/utils/errors';
import {
  usersAdminService,
  AdminUserListItem,
  UserStatusFilter,
} from '@/services/admin';

const PAGE_SIZE = 25;

const FILTERS: { id: 'all' | 'active' | 'suspended' | 'unverified'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'active', label: 'Active' },
  { id: 'suspended', label: 'Suspended' },
  { id: 'unverified', label: 'Unverified' },
];

export default function UsersAdmin() {
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'suspended' | 'unverified'>('all');
  const [offset, setOffset] = useState(0);

  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Debounce search input (300ms)
  const debounceRef = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
      setOffset(0);
    }, 300);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [query]);

  const statusParam: UserStatusFilter = filter === 'all' ? undefined : filter;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    usersAdminService
      .searchUsers(debouncedQuery || undefined, statusParam, offset, PAGE_SIZE)
      .then((res) => {
        if (cancelled) return;
        setUsers(res.items);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(extractErrorMessage(e, 'Failed to load users'));
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, statusParam, offset]);

  const showingFrom = users.length === 0 ? 0 : offset + 1;
  const showingTo = offset + users.length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Users</h1>
        <p className="text-gray-500 text-sm mt-1">
          Search, audit, and manage all user accounts on the platform.
        </p>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <div className="card p-4 space-y-4">
        <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by email or name…"
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => {
                  setFilter(f.id);
                  setOffset(0);
                }}
                className={clsx(
                  'text-xs font-medium px-3 py-1.5 rounded-full border transition',
                  filter === f.id
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">User</th>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Roles</th>
              <th className="text-left px-4 py-3">Providers</th>
              <th className="text-right px-4 py-3">Sessions</th>
              <th className="text-right px-4 py-3">Apps</th>
              <th className="text-right px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-gray-400">
                  <Loader2 className="w-5 h-5 mx-auto animate-spin" />
                </td>
              </tr>
            )}
            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-gray-400">
                  No users match these filters.
                </td>
              </tr>
            )}
            {!loading &&
              users.map((u) => (
                <tr
                  key={u.id}
                  onClick={() => navigate(`/admin/users/${u.id}`)}
                  className="hover:bg-gray-50 cursor-pointer transition"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Avatar user={u} />
                      <div>
                        <div className="font-medium text-gray-900">
                          {u.full_name || '—'}
                        </div>
                        <div className="text-xs text-gray-400 font-mono">
                          {u.id.slice(0, 8)}…
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-700">{u.email}</span>
                      {!u.email_verified && (
                        <MailWarning
                          className="w-3.5 h-3.5 text-amber-500"
                          aria-label="Email not verified"
                        />
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge user={u} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {u.roles.length === 0 && (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                      {u.roles.map((r) => (
                        <span
                          key={r.id}
                          className="text-[11px] px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100"
                        >
                          {r.name}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {u.providers.length === 0 && (
                        <span className="text-xs text-gray-400">password</span>
                      )}
                      {u.providers.map((p) => (
                        <span
                          key={p}
                          className="text-[11px] px-2 py-0.5 rounded bg-gray-100 text-gray-700"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                    {u.active_sessions}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    <span className="font-semibold text-primary-600">{u.connected_apps}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-gray-500">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>

        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50">
          <p className="text-xs text-gray-500">
            Showing {showingFrom}–{showingTo}
          </p>
          <div className="flex gap-2">
            <button
              disabled={offset === 0 || loading}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-200 rounded-md disabled:opacity-50 hover:bg-white"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Prev
            </button>
            <button
              disabled={users.length < PAGE_SIZE || loading}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-200 rounded-md disabled:opacity-50 hover:bg-white"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Avatar({ user }: { user: AdminUserListItem }) {
  if (user.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt={user.email}
        className="w-9 h-9 rounded-full object-cover border border-gray-100"
      />
    );
  }
  const initial =
    (user.full_name?.[0] || user.email[0] || '?').toUpperCase();
  return (
    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center font-semibold text-sm">
      {initial}
    </div>
  );
}

function StatusBadge({ user }: { user: AdminUserListItem }) {
  if (!user.is_active) {
    return (
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-100">
        <ShieldAlert className="w-3 h-3" /> Suspended
      </span>
    );
  }
  if (!user.email_verified) {
    return (
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-100">
        <XCircle className="w-3 h-3" /> Unverified
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-100">
      <CheckCircle2 className="w-3 h-3" /> Active
    </span>
  );
}
