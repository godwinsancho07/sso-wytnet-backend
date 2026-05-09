import { useEffect, useState } from 'react';
import {
  ShieldAlert, Ban, Unlock, RefreshCw, Plus, AlertTriangle, KeyRound,
} from 'lucide-react';
import { clsx } from 'clsx';

import Alert from '@/components/Alert';
import { extractErrorMessage } from '@/utils/errors';
import {
  adminService,
  securityService,
  BlockedIP,
  LockedAccount,
  SecurityAlert,
} from '@/services/admin';

type Tab = 'blocked' | 'locked' | 'alerts';

const TABS: { id: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'blocked', label: 'Blocked IPs', icon: Ban },
  { id: 'locked', label: 'Locked Accounts', icon: ShieldAlert },
  { id: 'alerts', label: 'Threat Alerts', icon: AlertTriangle },
];

export default function SecurityCenter() {
  const [tab, setTab] = useState<Tab>('blocked');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Security Center</h1>
        <p className="text-gray-500 text-sm mt-1">
          Manage IP blocks, locked accounts, and active threat signals.
        </p>
      </div>

      <div className="border-b border-gray-200 flex gap-1">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition',
                active
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-gray-500 hover:text-gray-800',
              )}
            >
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'blocked' && <BlockedIPsTab />}
      {tab === 'locked' && <LockedAccountsTab />}
      {tab === 'alerts' && <ThreatAlertsTab />}
    </div>
  );
}

// ── Blocked IPs ──────────────────────────────────────────────────────────────

function BlockedIPsTab() {
  const [items, setItems] = useState<BlockedIP[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [ip, setIP] = useState('');
  const [reason, setReason] = useState('');
  const [expiresAt, setExpiresAt] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await securityService.listBlockedIPs());
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to load blocked IPs'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const onAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ip.trim()) return;
    setError('');
    try {
      await securityService.blockIP(
        ip.trim(),
        reason.trim() || undefined,
        expiresAt || null,
      );
      setIP(''); setReason(''); setExpiresAt('');
      await load();
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to block IP'));
    }
  };

  const onUnblock = async (ipAddr: string) => {
    if (!confirm(`Unblock ${ipAddr}?`)) return;
    try {
      await securityService.unblockIP(ipAddr);
      await load();
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to unblock IP'));
    }
  };

  return (
    <div className="space-y-4">
      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <form onSubmit={onAdd} className="card p-4 grid md:grid-cols-4 gap-3">
        <input
          value={ip}
          onChange={(e) => setIP(e.target.value)}
          placeholder="IP address (e.g. 1.2.3.4)"
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm md:col-span-1"
          required
        />
        <input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Reason (optional)"
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm md:col-span-2"
        />
        <input
          type="datetime-local"
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
          title="Optional expiry — leave blank for permanent"
        />
        <button type="submit" className="btn-primary text-sm gap-1 md:col-span-4 md:w-auto md:justify-self-start">
          <Plus className="w-4 h-4" /> Block IP
        </button>
      </form>

      <div className="flex justify-end">
        <button onClick={load} className="btn-secondary text-xs gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-600 uppercase">
            <tr>
              <th className="text-left p-3">IP</th>
              <th className="text-left p-3">Reason</th>
              <th className="text-left p-3">Created</th>
              <th className="text-left p-3">Expires</th>
              <th className="text-right p-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={5} className="p-6 text-center text-gray-400">Loading…</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={5} className="p-6 text-center text-gray-400">No IPs are blocked.</td></tr>
            ) : (
              items.map((b) => (
                <tr key={b.id} className="hover:bg-gray-50">
                  <td className="p-3 font-mono text-xs">{b.ip_address}</td>
                  <td className="p-3 text-gray-700">{b.reason || '—'}</td>
                  <td className="p-3 text-xs text-gray-500">
                    {new Date(b.created_at).toLocaleString()}
                  </td>
                  <td className="p-3 text-xs text-gray-500">
                    {b.expires_at ? new Date(b.expires_at).toLocaleString() : 'Permanent'}
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => onUnblock(b.ip_address)}
                      className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-50 inline-flex items-center gap-1"
                    >
                      <Unlock className="w-3 h-3" /> Unblock
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Locked accounts ──────────────────────────────────────────────────────────

function LockedAccountsTab() {
  const [items, setItems] = useState<LockedAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await securityService.listLockedAccounts());
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to load locked accounts'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const onUnlock = async (id: string, email: string) => {
    if (!confirm(`Unlock account for ${email}?`)) return;
    try {
      await securityService.unlockUser(id);
      await load();
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to unlock'));
    }
  };

  const onForceMFA = async (id: string, email: string) => {
    if (!confirm(`Require ${email} to set up MFA at next login?`)) return;
    try {
      await securityService.forceMFA(id);
      alert('MFA will be required on next login.');
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to force MFA'));
    }
  };

  return (
    <div className="space-y-4">
      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <div className="flex justify-end">
        <button onClick={load} className="btn-secondary text-xs gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-600 uppercase">
            <tr>
              <th className="text-left p-3">User</th>
              <th className="text-left p-3">Email</th>
              <th className="text-right p-3">Failed attempts</th>
              <th className="text-left p-3">Locked until</th>
              <th className="text-left p-3">Status</th>
              <th className="text-right p-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={6} className="p-6 text-center text-gray-400">Loading…</td></tr>
            ) : items.length === 0 ? (
              <tr><td colSpan={6} className="p-6 text-center text-gray-400">No accounts are locked or failing.</td></tr>
            ) : (
              items.map((u) => (
                <tr key={u.user_id} className="hover:bg-gray-50">
                  <td className="p-3">{u.full_name || '—'}</td>
                  <td className="p-3 text-gray-700">{u.email}</td>
                  <td className="p-3 text-right tabular-nums">{u.failed_login_count}</td>
                  <td className="p-3 text-xs text-gray-500">
                    {u.locked_until ? new Date(u.locked_until).toLocaleString() : '—'}
                  </td>
                  <td className="p-3">
                    {u.is_locked ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-100">
                        Locked
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-100">
                        Failing
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-right space-x-1">
                    <button
                      onClick={() => onUnlock(u.user_id, u.email)}
                      className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-50 inline-flex items-center gap-1"
                    >
                      <Unlock className="w-3 h-3" /> Unlock
                    </button>
                    <button
                      onClick={() => onForceMFA(u.user_id, u.email)}
                      className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-50 inline-flex items-center gap-1"
                    >
                      <KeyRound className="w-3 h-3" /> Force MFA
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Threat alerts (re-uses /v1/security/alerts) ──────────────────────────────

function ThreatAlertsTab() {
  const [items, setItems] = useState<SecurityAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await adminService.getSecurityAlerts());
    } catch (e) {
      setError(extractErrorMessage(e, 'Failed to load alerts'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const sevColor = (s: SecurityAlert['severity']) =>
    s === 'high'
      ? 'bg-red-50 text-red-700 border-red-100'
      : s === 'medium'
      ? 'bg-amber-50 text-amber-700 border-amber-100'
      : 'bg-gray-50 text-gray-700 border-gray-200';

  return (
    <div className="space-y-4">
      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <div className="flex justify-end">
        <button onClick={load} className="btn-secondary text-xs gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="card p-6 text-center text-gray-400">Loading…</div>
      ) : items.length === 0 ? (
        <div className="card p-6 text-center text-gray-400">
          No active threats detected.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((a, i) => (
            <div
              key={`${a.type}-${i}`}
              className={clsx('card p-4 border-l-4', sevColor(a.severity))}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium">{a.title}</div>
                  <div className="text-xs text-gray-600 mt-1">{a.detail}</div>
                  {a.ip && (
                    <div className="text-xs font-mono text-gray-500 mt-1">
                      IP: {a.ip}
                    </div>
                  )}
                </div>
                <span
                  className={clsx(
                    'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border',
                    sevColor(a.severity),
                  )}
                >
                  {a.severity}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
