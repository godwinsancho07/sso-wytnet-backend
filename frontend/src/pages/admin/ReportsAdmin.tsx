import { useEffect, useState } from 'react';
import {
  BarChart2, TrendingUp, Users, RefreshCw, Download,
  Calendar, ChevronDown, Globe, Briefcase, Activity,
} from 'lucide-react';
import { clsx } from 'clsx';
import {
  reportsService,
  LoginSummaryDay, UsersGrowthDay, OAuthUsageReport, ProviderBreakdownEntry,
} from '@/services/admin';

type Tab = 'logins' | 'growth' | 'oauth' | 'providers';

const TABS: { key: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'logins',    label: 'Login Report',      icon: TrendingUp },
  { key: 'growth',    label: 'User Growth',        icon: Users },
  { key: 'oauth',     label: 'OAuth Usage',        icon: Briefcase },
  { key: 'providers', label: 'Provider Breakdown', icon: Globe },
];

const DAY_OPTIONS = [7, 14, 30, 60, 90];

export default function ReportsAdmin() {
  const [tab, setTab] = useState<Tab>('logins');
  const [days, setDays] = useState(30);

  const [logins, setLogins] = useState<LoginSummaryDay[]>([]);
  const [growth, setGrowth] = useState<UsersGrowthDay[]>([]);
  const [oauth, setOauth] = useState<OAuthUsageReport | null>(null);
  const [providers, setProviders] = useState<ProviderBreakdownEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      if (tab === 'logins')    setLogins(await reportsService.loginSummary(days));
      if (tab === 'growth')    setGrowth(await reportsService.usersGrowth(days));
      if (tab === 'oauth')     setOauth(await reportsService.oauthUsage(days));
      if (tab === 'providers') setProviders(await reportsService.providerBreakdown(days));
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, [tab, days]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const from = new Date(Date.now() - days * 86400000).toISOString().split('T')[0];
      const to = new Date().toISOString().split('T')[0];
      await reportsService.exportAuditCsv({ from, to });
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports &amp; Analytics</h1>
          <p className="text-gray-500 text-sm mt-1">
            Aggregated platform analytics across authentication, users, and OAuth usage.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Days picker */}
          <div className="relative">
            <select
              value={days}
              onChange={e => setDays(+e.target.value)}
              className="input pr-8 text-sm appearance-none"
            >
              {DAY_OPTIONS.map(d => (
                <option key={d} value={d}>Last {d} days</option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 text-gray-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
          <button
            onClick={load}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="btn-primary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
        {TABS.map(t => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                tab === t.key
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700',
              )}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {loading ? (
        <div className="card animate-pulse h-64 flex items-center justify-center text-gray-300">
          <BarChart2 className="w-12 h-12" />
        </div>
      ) : (
        <>
          {tab === 'logins' && <LoginReport data={logins} days={days} />}
          {tab === 'growth' && <GrowthReport data={growth} days={days} />}
          {tab === 'oauth' && oauth && <OAuthReport data={oauth} />}
          {tab === 'providers' && <ProvidersReport data={providers} />}
        </>
      )}
    </div>
  );
}

/* ─── Login report ─────────────────────────────────────────────────────────── */
function LoginReport({ data, days }: { data: LoginSummaryDay[]; days: number }) {
  const totalSuccess = data.reduce((s, d) => s + d.success, 0);
  const totalFailed  = data.reduce((s, d) => s + d.failed, 0);
  const totalSocial  = data.reduce((s, d) => s + d.social, 0);
  const totalReg     = data.reduce((s, d) => s + d.registrations, 0);
  const maxVal = Math.max(...data.map(d => d.success + d.failed), 1);

  return (
    <div className="space-y-6">
      {/* KPI summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Successful Logins',  value: totalSuccess,  color: 'text-green-700 bg-green-50' },
          { label: 'Failed Logins',      value: totalFailed,   color: 'text-red-700 bg-red-50' },
          { label: 'Social Logins',      value: totalSocial,   color: 'text-blue-700 bg-blue-50' },
          { label: 'New Registrations',  value: totalReg,      color: 'text-violet-700 bg-violet-50' },
        ].map(k => (
          <div key={k.label} className={`rounded-xl px-5 py-4 ${k.color}`}>
            <p className="text-3xl font-bold">{k.value.toLocaleString()}</p>
            <p className="text-xs font-medium mt-1 opacity-80">{k.label}</p>
            <p className="text-[10px] opacity-60 mt-0.5">Last {days} days</p>
          </div>
        ))}
      </div>

      {/* Bar chart (CSS) */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4 text-sm">Daily Login Activity</h2>
        <div className="flex items-end gap-1 h-40 overflow-x-auto pb-2">
          {data.map((d) => {
            const successPct = Math.round((d.success / maxVal) * 100);
            const failedPct  = Math.round((d.failed  / maxVal) * 100);
            return (
              <div key={d.date} className="flex flex-col items-center gap-0.5 shrink-0 group" style={{ minWidth: 20 }}>
                <div className="flex flex-col justify-end h-32 gap-0.5 relative">
                  {/* Tooltip */}
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                    ✓ {d.success} / ✗ {d.failed}
                  </div>
                  <div className="w-4 bg-red-400 rounded-t" style={{ height: `${failedPct}%` }} />
                  <div className="w-4 bg-green-400 rounded-t" style={{ height: `${successPct}%` }} />
                </div>
                <span className="text-[8px] text-gray-400 rotate-45 origin-left mt-1">
                  {d.date.slice(5)}
                </span>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-green-400" /> Success</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-red-400" /> Failed</span>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900 text-sm">Daily Breakdown</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-6 py-3">Date</th>
                <th className="text-right px-6 py-3">Success</th>
                <th className="text-right px-6 py-3">Failed</th>
                <th className="text-right px-6 py-3">Social</th>
                <th className="text-right px-6 py-3">Registrations</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {[...data].reverse().slice(0, 20).map(d => (
                <tr key={d.date} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-mono text-gray-700">{d.date}</td>
                  <td className="px-6 py-3 text-right text-green-700 font-medium">{d.success.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right text-red-600 font-medium">{d.failed.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right text-blue-600">{d.social.toLocaleString()}</td>
                  <td className="px-6 py-3 text-right text-violet-600">{d.registrations.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─── User growth report ───────────────────────────────────────────────────── */
function GrowthReport({ data, days }: { data: UsersGrowthDay[]; days: number }) {
  const latest = data[data.length - 1];
  const first = data[0];
  const growth = latest && first ? latest.total_users - first.total_users : 0;
  const totalNew = data.reduce((s, d) => s + d.new_users, 0);
  const maxVal = Math.max(...data.map(d => d.total_users), 1);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Users Now', value: latest?.total_users ?? 0, color: 'text-indigo-700 bg-indigo-50' },
          { label: 'New Users',       value: totalNew,                  color: 'text-green-700 bg-green-50' },
          { label: 'Net Growth',      value: growth,                    color: 'text-amber-700 bg-amber-50' },
        ].map(k => (
          <div key={k.label} className={`rounded-xl px-5 py-4 ${k.color}`}>
            <p className="text-3xl font-bold">{k.value.toLocaleString()}</p>
            <p className="text-xs font-medium mt-1 opacity-80">{k.label}</p>
            <p className="text-[10px] opacity-60 mt-0.5">Last {days} days</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4 text-sm">User Growth Trend</h2>
        <div className="flex items-end gap-1 h-40 overflow-x-auto pb-2">
          {data.map((d) => {
            const pct = Math.round((d.total_users / maxVal) * 100);
            return (
              <div key={d.date} className="flex flex-col items-center shrink-0 group" style={{ minWidth: 20 }}>
                <div className="flex flex-col justify-end h-32">
                  <div className="absolute invisible group-hover:visible bg-gray-900 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap z-10">
                    {d.date}: {d.total_users.toLocaleString()} users
                  </div>
                  <div className="w-4 bg-indigo-400 rounded-t" style={{ height: `${pct}%` }} />
                </div>
                <span className="text-[8px] text-gray-400 rotate-45 origin-left mt-1">
                  {d.date.slice(5)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900 text-sm">Daily Growth</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-6 py-3">Date</th>
              <th className="text-right px-6 py-3">New Users</th>
              <th className="text-right px-6 py-3">Total Users</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {[...data].reverse().slice(0, 20).map(d => (
              <tr key={d.date} className="hover:bg-gray-50">
                <td className="px-6 py-3 font-mono text-gray-700">{d.date}</td>
                <td className="px-6 py-3 text-right text-green-700 font-medium">+{d.new_users}</td>
                <td className="px-6 py-3 text-right font-semibold">{d.total_users.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── OAuth usage report ───────────────────────────────────────────────────── */
function OAuthReport({ data }: { data: OAuthUsageReport }) {
  const maxTokens = Math.max(...data.top_clients.map(c => c.tokens), 1);

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4 text-sm">Top 10 OAuth Clients by Token Issuance</h2>
        <div className="space-y-3">
          {data.top_clients.map((c, i) => {
            const pct = Math.round((c.tokens / maxTokens) * 100);
            return (
              <div key={c.client_db_id} className="flex items-center gap-4">
                <span className="text-sm font-bold text-gray-300 w-5 shrink-0 text-right">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900 truncate">{c.app_name}</span>
                    <span className="text-sm font-semibold text-primary-700 shrink-0 ml-2">
                      {c.tokens.toLocaleString()} tokens
                    </span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-gray-400 font-mono mt-0.5">{c.client_id}</p>
                </div>
              </div>
            );
          })}
          {data.top_clients.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-6">No OAuth data for the selected period.</p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Provider breakdown report ────────────────────────────────────────────── */
function ProvidersReport({ data }: { data: ProviderBreakdownEntry[] }) {
  // Aggregate by provider
  const byProvider: Record<string, number> = {};
  data.forEach(d => {
    byProvider[d.provider] = (byProvider[d.provider] || 0) + d.count;
  });
  const total = Object.values(byProvider).reduce((s, v) => s + v, 0);

  const COLORS: Record<string, string> = {
    google: 'bg-red-400', github: 'bg-gray-700',
    microsoft: 'bg-blue-500', linkedin: 'bg-sky-600',
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4 text-sm">Social Login Distribution</h2>
        {total === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No social login data for this period.</p>
        ) : (
          <div className="space-y-4">
            {Object.entries(byProvider)
              .sort(([, a], [, b]) => b - a)
              .map(([provider, count]) => {
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={provider}>
                    <div className="flex items-center justify-between mb-1.5 text-sm">
                      <span className="font-medium text-gray-900 capitalize">{provider}</span>
                      <span className="text-gray-500">{count.toLocaleString()} ({pct}%)</span>
                    </div>
                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${COLORS[provider] || 'bg-gray-400'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {data.length > 0 && (
        <div className="card overflow-hidden p-0">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900 text-sm">Provider Events Timeline</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-6 py-3">Date</th>
                <th className="text-left px-6 py-3">Provider</th>
                <th className="text-right px-6 py-3">Count</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {[...data].reverse().slice(0, 20).map((d, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-mono text-gray-600">{d.date}</td>
                  <td className="px-6 py-3">
                    <span className="capitalize font-medium text-gray-900">{d.provider}</span>
                  </td>
                  <td className="px-6 py-3 text-right font-semibold">{d.count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
