import { useEffect, useState } from 'react';
import { sessionService, Session } from '@/services/auth';
import Alert from '@/components/Alert';
import { Monitor, Smartphone, Tablet, Trash2 } from 'lucide-react';

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [message, setMessage] = useState('');

  useEffect(() => { sessionService.getSessions().then(setSessions); }, []);

  const revoke = async (id: string) => {
    await sessionService.revokeSession(id);
    setSessions((p) => p.filter((s) => s.id !== id));
    setMessage('Session revoked');
  };

  const revokeAll = async () => {
    await sessionService.revokeAllSessions();
    setSessions([]);
    setMessage('All sessions revoked');
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Active sessions</h1>
        {sessions.length > 1 && (
          <button onClick={revokeAll} className="btn-secondary text-sm text-red-600">
            Revoke all
          </button>
        )}
      </div>

      {message && <Alert type="success" message={message} onClose={() => setMessage('')} />}

      {sessions.length === 0 ? (
        <div className="card text-center py-10 text-gray-400">No active sessions</div>
      ) : (
        <ul className="space-y-3">
          {sessions.map((s) => (
            <li key={s.id} className="card flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  {s.device_info === 'Mobile' ? (
                    <Smartphone className="w-5 h-5 text-gray-400" />
                  ) : s.device_info === 'Tablet' ? (
                    <Tablet className="w-5 h-5 text-gray-400" />
                  ) : (
                    <Monitor className="w-5 h-5 text-gray-400" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-sm">{s.device_info || 'Unknown device'}</p>
                  <p className="text-xs text-gray-400">{s.ip_address || 'Unknown IP'}</p>
                  <p className="text-xs text-gray-400">
                    Last active {new Date(s.last_active_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <button
                onClick={() => revoke(s.id)}
                className="text-red-500 hover:text-red-700 flex-shrink-0"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
