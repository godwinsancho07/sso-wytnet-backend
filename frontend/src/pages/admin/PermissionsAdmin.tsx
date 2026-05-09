import { useEffect, useState } from 'react';
import {
  permissionsAdminService,
  AdminPermissionsByResource,
  AdminPermissionWithUsage,
} from '@/services/admin';
import { permissionService, UserPermissions } from '@/services/auth';
import Alert from '@/components/Alert';
import { Plus, Trash2, X, Shield } from 'lucide-react';

const RESOURCE_ORDER = ['client', 'user', 'role', 'session', 'audit', 'self'];

export default function PermissionsAdmin() {
  const [data, setData] = useState<AdminPermissionsByResource>({});
  const [me, setMe] = useState<UserPermissions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<AdminPermissionWithUsage | null>(null);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [perms, my] = await Promise.all([
        permissionsAdminService.list(),
        permissionService.getMyPermissions().catch(() => null),
      ]);
      setData(perms);
      setMe(my);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load permissions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const isSuper = me?.is_super_admin || me?.roles?.includes('super_admin') || false;

  const orderedResources = [
    ...RESOURCE_ORDER.filter((r) => data[r]),
    ...Object.keys(data).filter((r) => !RESOURCE_ORDER.includes(r)),
  ];

  const remove = async (p: AdminPermissionWithUsage) => {
    setError('');
    try {
      await permissionsAdminService.remove(p.id);
      setSuccess(`Deleted permission '${p.name}'.`);
      await load();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to delete permission');
    } finally {
      setConfirmDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Permissions</h1>
          <p className="text-gray-500 text-sm mt-1">
            Capability primitives that get assigned to roles.
          </p>
        </div>
        {isSuper && (
          <button
            onClick={() => setCreateOpen(true)}
            className="btn-primary text-sm gap-1 inline-flex items-center"
          >
            <Plus className="w-4 h-4" /> Create permission
          </button>
        )}
      </div>

      {error && <Alert type="error" message={error} />}
      {success && <Alert type="success" message={success} />}

      {loading ? (
        <div className="card p-8 text-center text-gray-400">Loading…</div>
      ) : orderedResources.length === 0 ? (
        <div className="card p-8 text-center text-gray-400">No permissions defined.</div>
      ) : (
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-600">
              <tr>
                <th className="text-left p-3 w-32">Resource</th>
                <th className="text-left p-3">Permissions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orderedResources.map((resource) => (
                <tr key={resource} className="align-top">
                  <td className="p-3 font-semibold text-gray-700 uppercase tracking-wide text-xs">
                    {resource}
                  </td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      {(data[resource] || []).map((p) => (
                        <div
                          key={p.id}
                          className="group inline-flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-full pl-2.5 pr-1 py-1 text-xs"
                          title={p.description || ''}
                        >
                          <Shield className="w-3 h-3 text-primary-500" />
                          <span className="font-mono">{p.name}</span>
                          <span className="text-gray-400">
                            • used by {p.role_count} {p.role_count === 1 ? 'role' : 'roles'}
                          </span>
                          {isSuper && (
                            <button
                              onClick={() => setConfirmDelete(p)}
                              className="text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full p-1"
                              title="Delete permission"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {createOpen && (
        <CreatePermissionModal
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            load();
          }}
        />
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-5 space-y-3">
            <h3 className="font-semibold">Delete permission?</h3>
            <p className="text-sm text-gray-600">
              <span className="font-mono bg-gray-100 px-1 py-0.5 rounded">
                {confirmDelete.name}
              </span>{' '}
              is currently assigned to{' '}
              <strong>
                {confirmDelete.role_count}{' '}
                {confirmDelete.role_count === 1 ? 'role' : 'roles'}
              </strong>
              . Deleting it removes it from those roles immediately.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setConfirmDelete(null)}
                className="btn-secondary text-sm"
              >
                Cancel
              </button>
              <button
                onClick={() => remove(confirmDelete)}
                className="btn-primary text-sm bg-red-600 hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CreatePermissionModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [resource, setResource] = useState('');
  const [action, setAction] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const valid = /^[a-z_]+$/.test(resource) && /^[a-z_]+$/.test(action);
  const name = valid ? `${resource}:${action}` : '';

  const submit = async () => {
    if (!valid) return;
    setBusy(true);
    setError('');
    try {
      await permissionsAdminService.create({
        name,
        resource,
        action,
        description: description || undefined,
      });
      onCreated();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to create permission');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h3 className="font-semibold">Create permission</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 space-y-3">
          {error && <Alert type="error" message={error} />}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-medium text-gray-700">Resource</label>
              <input
                value={resource}
                onChange={(e) => setResource(e.target.value.toLowerCase())}
                placeholder="e.g. report"
                className="input w-full mt-1 font-mono text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-700">Action</label>
              <input
                value={action}
                onChange={(e) => setAction(e.target.value.toLowerCase())}
                placeholder="e.g. export"
                className="input w-full mt-1 font-mono text-sm"
              />
            </div>
          </div>
          <p className="text-[11px] text-gray-500">
            Final name:{' '}
            <span className="font-mono bg-gray-100 px-1 py-0.5 rounded">
              {name || 'resource:action'}
            </span>
            . Lowercase letters and underscores only.
          </p>
          <div>
            <label className="text-xs font-medium text-gray-700">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="input w-full mt-1"
              placeholder="What does this permission allow?"
            />
          </div>
        </div>
        <div className="px-5 py-3 border-t flex justify-end gap-2 bg-gray-50">
          <button onClick={onClose} className="btn-secondary text-sm">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy || !valid}
            className="btn-primary text-sm disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}
