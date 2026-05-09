import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Users, Briefcase, Activity, AlertTriangle, KeyRound, UserPlus,
  TrendingUp, TrendingDown, Zap, ChevronRight, Shield, Globe,
  ToggleLeft, RefreshCw, Timer, Lock, Ban, CheckCircle2,
  XCircle, Eye, UserX, PlusCircle, RotateCcw, LogOut,
  BarChart2, Clock, Fingerprint, Key,
} from 'lucide-react';
import { clsx } from 'clsx';
import {
  adminService, MetricsOverview, SecurityAlert, AuditEvent, TopApp,
} from '@/services/admin';

/* ─── enriched overview shape ──────────────────────────────────────────────── */
interface RichOverview extends MetricsOverview {
  // Users breakdown
  inactive_users: number;
  blocked_users: number;
  verified_users: number;
  unverified_users: number;
  // Auth
  total_logins_today: number;
  password_logins_24h: number;
  mfa_logins_24h: number;
  password_reset_requests_24h: number;
  // OAuth
  active_clients: number;
  disabled_clients: number;
  tokens_issued_total: number;
  tokens_revoked_total: number;
  refresh_tokens_active: number;
  // Sessions
  expired_sessions: number;
  revoked_sessions: number;
  // Security
  suspicious_logins: number;
  blocked_ips: number;
  rate_limit_hits_24h: number;
  account_lockouts: number;
}

/* ─── Quick actions ─────────────────────────────────────────────────────────── */
const QUICK_ACTIONS = [
  { label: 'Create User',       icon: UserPlus,   to: '/admin/users',    color: 'text-violet-600 bg-violet-50' },
  { label: 'Create Client',     icon: PlusCircle, to: '/admin/clients',  color: 'text-blue-600 bg-blue-50' },
  { label: 'Assign Role',       icon: Lock,       to: '/admin/roles',    color: 'text-amber-600 bg-amber-50' },
  { label: 'Revoke Sessions',   icon: LogOut,     to: '/admin/sessions', color: 'text-red-600 bg-red-50' },
  { label: 'Block User',        icon: UserX,      to: '/admin/users',    color: 'text-orange-600 bg-orange-50' },
  { label: 'Rotate Secret',     icon: RotateCcw,  to: '/admin/clients',  color: 'text-teal-600 bg-teal-50' },
];

/* ─── Event badge map ───────────────────────────────────────────────────────── */
const EVENT_MAP: Record<string, { color: string; label: string }> = {
  'auth.login':            { color: 'bg-green-100 text-green-700',   label: 'Login' },
  'auth.login_failed':     { color: 'bg-red-100 text-red-700',       label: 'Failed login' },
  'auth.logout':           { color: 'bg-gray-100 text-gray-700',     label: 'Logout' },
  'auth.global_logout':    { color: 'bg-amber-100 text-amber-700',   label: 'Global logout' },
  'auth.social_login':     { color: 'bg-blue-100 text-blue-700',     label: 'Social login' },
  'auth.social_register':  { color: 'bg-blue-100 text-blue-700',     label: 'Social register' },
  'auth.social_link':      { color: 'bg-indigo-100 text-indigo-700', label: 'Account linked' },
  'user.register':         { color: 'bg-purple-100 text-purple-700', label: 'New user' },
  'user.deleted':          { color: 'bg-red-100 text-red-800',       label: 'User deleted' },
  'user.force_logout':     { color: 'bg-orange-100 text-orange-700', label: 'Force logout' },
  'role.assigned':         { color: 'bg-teal-100 text-teal-700',     label: 'Role assigned' },
  'client.created':        { color: 'bg-sky-100 text-sky-700',       label: 'Client created' },
  'session.revoked_by_admin': { color: 'bg-rose-100 text-rose-700', label: 'Session revoked' },
  'provider.updated':      { color: 'bg-lime-100 text-lime-700',     label: 'Provider updated' },
};

export default function SuperAdminDashboard() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<RichOverview | null>(null);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [topApps, setTopApps] = useState<TopApp[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([
      adminService.getOverview().catch(() => null),
      adminService.getSecurityAlerts().catch(() => []),
      adminService.getRecentAudit(20).catch(() => []),
      adminService.getTopApps(8).catch(() => []),
    ]).then(([m, a, e, t]) => {
      setMetrics(m as any);
      setAlerts(a);
      setAudit(e);
      setTopApps(t);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, []);

  const criticalAlerts = alerts.filter(a => a.severity === 'high');
  const warningAlerts = alerts.filter(a => a.severity === 'medium');

  return (
    <div className="space-y-8">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Platform Overview</h1>
          <p className="text-gray-500 text-sm mt-1">
            Real-time operational metrics, security signals, and activity across the SSO platform.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {metrics && (
            <p className="text-xs text-gray-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Updated {new Date(metrics.generated_at).toLocaleTimeString()}
            </p>
          )}
          <button
            onClick={load}
            className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Critical alerts banner ──────────────────────────────────── */}
      {criticalAlerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-red-800 text-sm">
              {criticalAlerts.length} Critical Security Alert{criticalAlerts.length > 1 ? 's' : ''}
            </p>
            <ul className="mt-1 space-y-0.5">
              {criticalAlerts.map((a, i) => (
                <li key={i} className="text-sm text-red-700">• {a.title}: {a.detail}</li>
              ))}
            </ul>
          </div>
          <Link to="/admin/security" className="text-xs text-red-700 font-semibold hover:underline shrink-0">
            Investigate →
          </Link>
        </div>
      )}

      {/* ── User KPIs ────────────────────────────────────────────────── */}
      <KPISection title="Users" icon={<Users className="w-4 h-4" />} to="/admin/users">
        <KPI icon={<Users className="w-4 h-4" />}         label="Total Users"      value={metrics?.total_users}         accent="indigo" loading={loading} />
        <KPI icon={<CheckCircle2 className="w-4 h-4" />}  label="Active"           value={metrics?.active_users}        accent="green"  loading={loading} />
        <KPI icon={<XCircle className="w-4 h-4" />}       label="Inactive"         value={metrics?.inactive_users}      accent="gray"   loading={loading} />
        <KPI icon={<Ban className="w-4 h-4" />}           label="Blocked"          value={metrics?.blocked_users}       accent="red"    loading={loading} />
        <KPI icon={<CheckCircle2 className="w-4 h-4" />}  label="Verified"         value={metrics?.verified_users}      accent="green"  loading={loading} />
        <KPI icon={<AlertTriangle className="w-4 h-4" />} label="Unverified"       value={metrics?.unverified_users}    accent="amber"  loading={loading} />
      </KPISection>

      {/* ── Auth KPIs ────────────────────────────────────────────────── */}
      <KPISection title="Authentication (24h)" icon={<Key className="w-4 h-4" />} to="/admin/audit-logs">
        <KPI icon={<TrendingUp className="w-4 h-4" />}    label="Logins Today"     value={(metrics as any)?.total_logins_today ?? metrics?.successful_logins_24h} accent="green"  loading={loading} />
        <KPI icon={<TrendingDown className="w-4 h-4" />}  label="Failed Logins"    value={metrics?.failed_logins_24h}           accent="red"    loading={loading}
          alert={!!metrics && metrics.failed_logins_24h > 50} />
        <KPI icon={<Globe className="w-4 h-4" />}         label="Social Logins"    value={metrics?.social_logins_24h}           accent="blue"   loading={loading} />
        <KPI icon={<KeyRound className="w-4 h-4" />}      label="Password Logins"  value={(metrics as any)?.password_logins_24h ?? 0}         accent="gray"   loading={loading} />
        <KPI icon={<Fingerprint className="w-4 h-4" />}   label="MFA Logins"       value={(metrics as any)?.mfa_logins_24h ?? 0}              accent="violet" loading={loading} />
        <KPI icon={<RotateCcw className="w-4 h-4" />}     label="PW Reset Reqs"    value={(metrics as any)?.password_reset_requests_24h ?? 0} accent="amber"  loading={loading} />
      </KPISection>

      {/* ── OAuth KPIs ──────────────────────────────────────────────── */}
      <KPISection title="OAuth / OIDC" icon={<Briefcase className="w-4 h-4" />} to="/admin/clients">
        <KPI icon={<Briefcase className="w-4 h-4" />}     label="Total Clients"    value={metrics?.total_clients}          accent="indigo" loading={loading} />
        <KPI icon={<CheckCircle2 className="w-4 h-4" />}  label="Active Clients"   value={metrics?.active_clients}         accent="green"  loading={loading} />
        <KPI icon={<ToggleLeft className="w-4 h-4" />}    label="Disabled Clients" value={metrics?.disabled_clients}       accent="gray"   loading={loading} />
        <KPI icon={<KeyRound className="w-4 h-4" />}      label="Tokens Today"     value={metrics?.tokens_today}           accent="blue"   loading={loading} />
        <KPI icon={<XCircle className="w-4 h-4" />}       label="Tokens Revoked"   value={(metrics as any)?.tokens_revoked_24h}   accent="red"    loading={loading} />
        <KPI icon={<RefreshCw className="w-4 h-4" />}     label="Refresh Active"   value={(metrics as any)?.refresh_tokens_active}  accent="teal"   loading={loading} />
      </KPISection>

      {/* ── Session KPIs ─────────────────────────────────────────────── */}
      <KPISection title="Sessions" icon={<Activity className="w-4 h-4" />} to="/admin/sessions">
        <KPI icon={<Activity className="w-4 h-4" />}      label="Active Sessions"  value={metrics?.active_sessions}   accent="green"  loading={loading} />
        <KPI icon={<Timer className="w-4 h-4" />}         label="Expired"          value={(metrics as any)?.expired_sessions}  accent="gray"   loading={loading} />
        <KPI icon={<XCircle className="w-4 h-4" />}       label="Revoked"          value={(metrics as any)?.revoked_sessions}  accent="red"    loading={loading} />
        <KPI icon={<Users className="w-4 h-4" />}         label="New Users (24h)"  value={metrics?.registrations_24h} accent="violet" loading={loading} />
      </KPISection>

      {/* ── Security KPIs ────────────────────────────────────────────── */}
      <KPISection title="Security" icon={<Shield className="w-4 h-4" />} to="/admin/security">
        <KPI icon={<AlertTriangle className="w-4 h-4" />} label="Suspicious Logins" value={(metrics as any)?.suspicious_logins ?? 0}    accent="red"    loading={loading} alert={!!((metrics as any)?.suspicious_logins)} />
        <KPI icon={<Ban className="w-4 h-4" />}           label="Blocked IPs"        value={(metrics as any)?.blocked_ips ?? 0}          accent="red"    loading={loading} />
        <KPI icon={<Zap className="w-4 h-4" />}           label="Rate Limit Hits"    value={(metrics as any)?.rate_limit_hits_24h ?? 0}  accent="amber"  loading={loading} />
        <KPI icon={<Lock className="w-4 h-4" />}          label="Account Lockouts"   value={(metrics as any)?.account_lockouts ?? 0}     accent="amber"  loading={loading} />
      </KPISection>

      {/* ── Bottom row: Alerts + Activity + Quick Actions ────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Alerts */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Security Alerts
              {alerts.length > 0 && (
                <span className="bg-red-100 text-red-700 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {alerts.length}
                </span>
              )}
            </h2>
            <Link to="/admin/security" className="text-xs text-primary-600 hover:underline">View all</Link>
          </div>
          {alerts.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
              <p className="text-sm text-gray-400">No active alerts.<br />System operating normally.</p>
            </div>
          ) : (
            <ul className="space-y-2">
              {alerts.slice(0, 5).map((a, i) => (
                <li key={i} className={clsx(
                  'rounded-lg border p-3 text-sm',
                  a.severity === 'high'   && 'border-red-200 bg-red-50',
                  a.severity === 'medium' && 'border-amber-200 bg-amber-50',
                  a.severity === 'low'    && 'border-blue-200 bg-blue-50',
                )}>
                  <div className="flex items-center gap-2 mb-1">
                    <SeverityDot s={a.severity} />
                    <p className="font-semibold text-gray-900 text-xs">{a.title}</p>
                  </div>
                  <p className="text-xs text-gray-600">{a.detail}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Recent activity */}
        <div className="card lg:col-span-1">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 text-sm">Recent Activity</h2>
            <Link to="/admin/audit-logs" className="text-xs text-primary-600 hover:underline flex items-center gap-1">
              All logs <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
          {audit.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No recent events.</p>
          ) : (
            <ul className="divide-y divide-gray-50 -mx-2">
              {audit.slice(0, 10).map((e) => {
                const info = EVENT_MAP[e.event_type] || { color: 'bg-gray-100 text-gray-600', label: e.event_type };
                return (
                  <li key={e.id} className="flex items-center justify-between py-2 px-2 hover:bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium ${info.color}`}>
                        {info.label}
                      </span>
                      {e.ip_address && (
                        <span className="text-[10px] text-gray-400 font-mono truncate">{e.ip_address}</span>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-400 shrink-0 ml-2">
                      {new Date(e.created_at).toLocaleTimeString()}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 text-sm mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_ACTIONS.map((qa) => {
              const Icon = qa.icon;
              return (
                <button
                  key={qa.label}
                  onClick={() => navigate(qa.to)}
                  className="flex flex-col items-center gap-2 p-3 rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all text-center group"
                >
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${qa.color} group-hover:scale-110 transition-transform`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-xs font-medium text-gray-700 leading-tight">{qa.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Top Apps ──────────────────────────────────────────────────── */}
      {topApps.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 text-sm">Top Applications — Last 7 Days</h2>
            <Link to="/admin/clients" className="text-xs text-primary-600 hover:underline">
              Manage clients
            </Link>
          </div>
          <div className="space-y-3">
            {topApps.map((app, i) => {
              const maxTokens = topApps[0]?.tokens_7d || 1;
              const pct = Math.round((app.tokens_7d / maxTokens) * 100);
              return (
                <div key={app.client_id} className="flex items-center gap-4">
                  <span className="text-sm font-bold text-gray-300 w-5 text-right">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900 truncate">{app.app_name}</span>
                      <span className="text-sm font-semibold text-primary-700 ml-2 shrink-0">
                        {app.tokens_7d.toLocaleString()} tokens
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary-400 to-primary-600 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-gray-400 font-mono mt-0.5">{app.client_id}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── KPI section wrapper ──────────────────────────────────────────────────── */
function KPISection({
  title, icon, to, children,
}: {
  title: string; icon: React.ReactNode; to: string; children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-2">
          <span className="text-gray-400">{icon}</span>
          {title}
        </h2>
        <Link to={to} className="text-xs text-primary-600 hover:underline flex items-center gap-1">
          View all <ChevronRight className="w-3 h-3" />
        </Link>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {children}
      </div>
    </div>
  );
}

/* ─── Single KPI card ──────────────────────────────────────────────────────── */
type Accent = 'gray' | 'red' | 'green' | 'blue' | 'amber' | 'violet' | 'indigo' | 'teal';

const ACCENT_STYLES: Record<Accent, string> = {
  gray:   'bg-gray-100 text-gray-600',
  red:    'bg-red-50 text-red-600',
  green:  'bg-green-50 text-green-600',
  blue:   'bg-blue-50 text-blue-600',
  amber:  'bg-amber-50 text-amber-600',
  violet: 'bg-violet-50 text-violet-600',
  indigo: 'bg-indigo-50 text-indigo-600',
  teal:   'bg-teal-50 text-teal-600',
};

function KPI({
  icon, label, value, accent = 'gray', loading, alert,
}: {
  icon: React.ReactNode; label: string; value?: number;
  accent?: Accent; loading?: boolean; alert?: boolean;
}) {
  return (
    <div className={clsx(
      'bg-white rounded-xl border p-4 flex flex-col gap-2 relative overflow-hidden',
      alert ? 'border-red-200' : 'border-gray-100',
    )}>
      {alert && (
        <div className="absolute top-0 right-0 left-0 h-0.5 bg-gradient-to-r from-red-400 to-red-600" />
      )}
      <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center shrink-0', ACCENT_STYLES[accent])}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 leading-none">
          {loading ? <span className="text-gray-200">—</span> : (value ?? 0).toLocaleString()}
        </p>
        <p className="text-[11px] text-gray-400 mt-1 leading-tight">{label}</p>
      </div>
    </div>
  );
}

/* ─── Alert severity dot ──────────────────────────────────────────────────── */
function SeverityDot({ s }: { s: string }) {
  return (
    <span className={clsx(
      'w-2 h-2 rounded-full shrink-0',
      s === 'high'   && 'bg-red-500',
      s === 'medium' && 'bg-amber-500',
      s === 'low'    && 'bg-blue-400',
    )} />
  );
}
