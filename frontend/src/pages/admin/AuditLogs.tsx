import { useEffect, useState } from 'react';
import { adminService, AuditEvent } from '@/services/admin';
import { Filter, RefreshCw } from 'lucide-react';

const EVENT_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Logins', value: 'auth.login' },
  { label: 'Failed logins', value: 'auth.login_failed' },
  { label: 'Registrations', value: 'user.register' },
  { label: 'Social logins', value: 'auth.social_login' },
  { label: 'Logouts', value: 'auth.logout' },
];

export default function AuditLogs() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await import('@/services/api').then((m) =>
        m.default.get<AuditEvent[]>('/v1/audit/recent', {
          params: filter ? { limit: 100, event_type: filter } : { limit: 100 },
        })
      );
      setEvents(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Logs</h1>
          <p className="text-gray-500 text-sm mt-1">
            All authentication and authorization events.
          </p>
        </div>
        <button onClick={load} className="btn-secondary text-xs gap-1">
          <RefreshCw className="w-3 h-3" /> Refresh
        </button>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="w-4 h-4 text-gray-400" />
        {EVENT_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
              filter === f.value
                ? 'bg-primary-600 text-white'
                : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-600 uppercase">
            <tr>
              <th className="text-left p-3">Event</th>
              <th className="text-left p-3">User</th>
              <th className="text-left p-3">IP</th>
              <th className="text-left p-3">Metadata</th>
              <th className="text-right p-3">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={5} className="p-6 text-center text-gray-400">Loading…</td></tr>
            ) : events.length === 0 ? (
              <tr><td colSpan={5} className="p-6 text-center text-gray-400">No events found.</td></tr>
            ) : (
              events.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50">
                  <td className="p-3 font-mono text-xs">{e.event_type}</td>
                  <td className="p-3 text-xs text-gray-500 font-mono">
                    {e.user_id ? e.user_id.slice(0, 8) : '—'}
                  </td>
                  <td className="p-3 font-mono text-xs">{e.ip_address || '—'}</td>
                  <td className="p-3 text-xs text-gray-500 max-w-xs truncate font-mono">
                    {e.metadata ? JSON.stringify(e.metadata) : '—'}
                  </td>
                  <td className="p-3 text-right text-xs text-gray-400 whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString()}
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
