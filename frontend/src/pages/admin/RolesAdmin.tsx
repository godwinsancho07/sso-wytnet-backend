import { useEffect, useMemo, useState } from 'react';
import {
  rolesAdminService,
  permissionsAdminService,
  usersAdminService,
  AdminRole,
  AdminRoleDetail,
  AdminPermissionsByResource,
  AdminPermission,
  AdminUserListItem,
} from '@/services/admin';
import Alert from '@/components/Alert';
import {
  Plus,
  Shield,
  Users,
  Lock,
  X,
  Save,
  Trash2,
  UserPlus,
  UserMinus,
  Search,
} from 'lucide-react';

const PROTECTED = new Set(['super_admin', 'app_admin', 'user']);

const RESOURCE_ORDER = ['client', 'user', 'role', 'session', 'audit', 'self'];

export default function RolesAdmin() {
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [counts, setCounts] = useState<Record<string, { perms: number; users: number }>>({});
  const [permsByResource, setPermsByResource] = useState<AdminPermissionsByResource>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const [createOpen, setCreateOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const loadRoles = async () => {
    setLoading(true);
    setError('');
    try {
      const [list, perms] = await Promise.all([
        rolesAdminService.list(),
        permissionsAdminService.list(),
      ]);
      setRoles(list);
      setPermsByResource(perms);
      // Fetch counts in parallel
      const detailed = await Promise.all(list.map((r) => rolesAdminService.get(r.id)));
      const c: Record<string, { perms: number; users: number }> = {};
      detailed.forEach((d) => {
        c[d.id] = { perms: d.permissions.length, users: d.user_count };
      });
      setCounts(c);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoles();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Roles</h1>
          <p className="text-gray-500 text-sm mt-1">
            Define roles and the permissions they grant.
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="btn-primary text-sm gap-1 inline-flex items-center"
        >
          <Plus className="w-4 h-4" /> Create role
        </button>
      </div>

      {error && <Alert type="error" message={error} />}

      {loading ? (
        <div className="card p-8 text-center text-gray-400">Loading…</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {roles.map((r) => {
            const isProtected = PROTECTED.has(r.name);
            const c = counts[r.id] || { perms: 0, users: 0 };
            return (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className="card text-left p-5 hover:shadow-md hover:border-primary-300 transition cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-2">
                  {isProtected ? (
                    <Lock className="w-4 h-4 text-amber-500" />
                  ) : (
                    <Shield className="w-4 h-4 text-primary-500" />
                  )}
                  <h3 className="font-semibold text-gray-900">{r.name}</h3>
                  {isProtected && (
                    <span className="ml-auto text-[10px] uppercase tracking-wide bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                      Protected
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 line-clamp-2 min-h-[2rem]">
                  {r.description || 'No description'}
                </p>
                <div className="mt-3 flex items-center gap-3 text-xs text-gray-600">
                  <span className="inline-flex items-center gap-1">
                    <Shield className="w-3 h-3" /> {c.perms} permissions
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Users className="w-3 h-3" /> {c.users} users
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {createOpen && (
        <CreateRoleModal
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            loadRoles();
          }}
        />
      )}

      {selectedId && (
        <RoleDetailDrawer
          roleId={selectedId}
          permsByResource={permsByResource}
          resourceOrder={RESOURCE_ORDER}
          onClose={() => setSelectedId(null)}
          onChanged={() => {
            loadRoles();
          }}
        />
      )}
    </div>
  );
}

// ── Create role modal ────────────────────────────────────────────────────────

function CreateRoleModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      await rolesAdminService.create({ name, description });
      onCreated();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to create role');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h3 className="font-semibold">Create role</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 space-y-3">
          {error && <Alert type="error" message={error} />}
          <div>
            <label className="text-xs font-medium text-gray-700">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. content_editor"
              className="input w-full mt-1"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-700">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="input w-full mt-1"
            />
          </div>
        </div>
        <div className="px-5 py-3 border-t flex justify-end gap-2 bg-gray-50">
          <button onClick={onClose} className="btn-secondary text-sm">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy || !name.trim()}
            className="btn-primary text-sm disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Role detail drawer ───────────────────────────────────────────────────────

function RoleDetailDrawer({
  roleId,
  permsByResource,
  resourceOrder,
  onClose,
  onChanged,
}: {
  roleId: string;
  permsByResource: AdminPermissionsByResource;
  resourceOrder: string[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const [detail, setDetail] = useState<AdminRoleDetail | null>(null);
  const [users, setUsers] = useState<AdminUserListItem[]>([]);
  const [allUsers, setAllUsers] = useState<AdminUserListItem[]>([]);
  const [selectedPerms, setSelectedPerms] = useState<Set<string>>(new Set());
  const [originalPerms, setOriginalPerms] = useState<Set<string>>(new Set());
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [userSearch, setUserSearch] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const isProtected = detail ? detail.is_protected : false;

  const load = async () => {
    setError('');
    setBusy(true);
    try {
      const [d, all] = await Promise.all([
        rolesAdminService.get(roleId),
        usersAdminService.searchUsers(undefined, undefined, 0, 200),
      ]);
      setDetail(d);
      const ids = new Set(d.permissions.map((p) => p.id));
      setSelectedPerms(new Set(ids));
      setOriginalPerms(new Set(ids));
      setAllUsers(all.items);
      setUsers(all.items.filter((u) => u.roles.some((r) => r.id === roleId)));
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load role');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleId]);

  const toggle = (pid: string) => {
    setSelectedPerms((prev) => {
      const next = new Set(prev);
      if (next.has(pid)) next.delete(pid);
      else next.add(pid);
      return next;
    });
  };

  const dirty = useMemo(() => {
    if (selectedPerms.size !== originalPerms.size) return true;
    for (const p of selectedPerms) if (!originalPerms.has(p)) return true;
    return false;
  }, [selectedPerms, originalPerms]);

  const save = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const toGrant = [...selectedPerms].filter((p) => !originalPerms.has(p));
      const toRevoke = [...originalPerms].filter((p) => !selectedPerms.has(p));
      for (const pid of toGrant) await rolesAdminService.grantPermission(roleId, pid);
      for (const pid of toRevoke) await rolesAdminService.revokePermission(roleId, pid);
      setSuccess('Permissions updated.');
      await load();
      onChanged();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const removeUser = async (userId: string) => {
    try {
      await rolesAdminService.removeUser(userId, roleId);
      await load();
      onChanged();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to remove user');
    }
  };

  const addUser = async (userId: string) => {
    try {
      await rolesAdminService.assignUser(userId, roleId);
      await load();
      onChanged();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to add user');
    }
  };

  const deleteRole = async () => {
    try {
      await rolesAdminService.remove(roleId);
      onChanged();
      onClose();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to delete');
    }
  };

  const assignedIds = new Set(users.map((u) => u.id));
  const candidateUsers = allUsers
    .filter((u) => !assignedIds.has(u.id))
    .filter((u) =>
      userSearch
        ? `${u.email} ${u.full_name || ''}`.toLowerCase().includes(userSearch.toLowerCase())
        : false,
    )
    .slice(0, 8);

  const orderedResources = [
    ...resourceOrder.filter((r) => permsByResource[r]),
    ...Object.keys(permsByResource).filter((r) => !resourceOrder.includes(r)),
  ];

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex justify-end">
      <div className="bg-white w-full max-w-5xl h-full overflow-y-auto shadow-2xl">
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
          <div>
            <div className="flex items-center gap-2">
              {isProtected ? (
                <Lock className="w-4 h-4 text-amber-500" />
              ) : (
                <Shield className="w-4 h-4 text-primary-500" />
              )}
              <h2 className="text-lg font-bold">{detail?.name || '…'}</h2>
              {isProtected && (
                <span className="text-[10px] uppercase tracking-wide bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                  Protected
                </span>
              )}
            </div>
            {detail?.description && (
              <p className="text-xs text-gray-500 mt-0.5">{detail.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isProtected ? (
              <button
                disabled
                title="Protected roles cannot be deleted (super_admin, app_admin, user)"
                className="btn-secondary text-xs gap-1 inline-flex items-center opacity-50 cursor-not-allowed"
              >
                <Trash2 className="w-3 h-3" /> Delete
              </button>
            ) : (
              <button
                onClick={() => setConfirmDelete(true)}
                className="btn-secondary text-xs gap-1 inline-flex items-center text-red-600 hover:bg-red-50"
              >
                <Trash2 className="w-3 h-3" /> Delete
              </button>
            )}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4">
          {error && <Alert type="error" message={error} />}
          {success && <Alert type="success" message={success} />}

          {busy && !detail ? (
            <div className="text-gray-400 text-sm">Loading…</div>
          ) : (
            <div className="grid lg:grid-cols-3 gap-6">
              {/* Left 2/3: permissions grid */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-sm text-gray-700">Permissions</h3>
                  <button
                    onClick={save}
                    disabled={!dirty || saving}
                    className="btn-primary text-xs gap-1 inline-flex items-center disabled:opacity-50"
                  >
                    <Save className="w-3 h-3" />
                    {saving ? 'Saving…' : dirty ? 'Save changes' : 'Saved'}
                  </button>
                </div>

                {orderedResources.map((resource) => (
                  <div key={resource} className="card p-4">
                    <h4 className="font-semibold text-xs uppercase tracking-wide text-gray-500 mb-3">
                      {resource}
                    </h4>
                    <div className="grid sm:grid-cols-2 gap-2">
                      {(permsByResource[resource] || []).map((p: AdminPermission) => {
                        const checked = selectedPerms.has(p.id);
                        return (
                          <label
                            key={p.id}
                            className={`flex items-start gap-2 p-2 rounded-md border text-sm cursor-pointer ${
                              checked
                                ? 'border-primary-300 bg-primary-50'
                                : 'border-gray-200 hover:bg-gray-50'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggle(p.id)}
                              className="mt-0.5"
                            />
                            <div className="flex-1 min-w-0">
                              <div className="font-mono text-xs text-gray-900 truncate">
                                {p.name}
                              </div>
                              {p.description && (
                                <div className="text-[11px] text-gray-500 line-clamp-2">
                                  {p.description}
                                </div>
                              )}
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {/* Right 1/3: users */}
              <div className="space-y-3">
                <h3 className="font-semibold text-sm text-gray-700">
                  Users ({users.length})
                </h3>
                <div className="card p-3 space-y-1 max-h-72 overflow-y-auto">
                  {users.length === 0 ? (
                    <div className="text-xs text-gray-400 text-center py-3">
                      No users assigned.
                    </div>
                  ) : (
                    users.map((u) => (
                      <div
                        key={u.id}
                        className="flex items-center justify-between gap-2 p-1.5 rounded hover:bg-gray-50"
                      >
                        <div className="min-w-0">
                          <div className="text-xs font-medium truncate">
                            {u.full_name || u.email}
                          </div>
                          <div className="text-[10px] text-gray-400 truncate font-mono">
                            {u.email}
                          </div>
                        </div>
                        <button
                          onClick={() => removeUser(u.id)}
                          className="text-red-500 hover:bg-red-50 rounded p-1 shrink-0"
                          title="Remove from role"
                        >
                          <UserMinus className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>

                <div className="card p-3 space-y-2">
                  <h4 className="text-xs font-semibold text-gray-700">Add user</h4>
                  <div className="relative">
                    <Search className="w-3 h-3 absolute left-2 top-2.5 text-gray-400" />
                    <input
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      placeholder="Search by email or name…"
                      className="input w-full text-xs pl-7"
                    />
                  </div>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {userSearch && candidateUsers.length === 0 && (
                      <div className="text-[11px] text-gray-400 text-center py-2">
                        No matches.
                      </div>
                    )}
                    {candidateUsers.map((u) => (
                      <button
                        key={u.id}
                        onClick={() => addUser(u.id)}
                        className="flex items-center justify-between w-full gap-2 p-1.5 rounded hover:bg-primary-50 text-left"
                      >
                        <div className="min-w-0">
                          <div className="text-xs font-medium truncate">
                            {u.full_name || u.email}
                          </div>
                          <div className="text-[10px] text-gray-400 truncate font-mono">
                            {u.email}
                          </div>
                        </div>
                        <UserPlus className="w-3.5 h-3.5 text-primary-500 shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {confirmDelete && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-5 space-y-3">
            <h3 className="font-semibold">Delete role?</h3>
            <p className="text-sm text-gray-600">
              This will remove the role from all users and revoke its permissions. The
              users themselves will not be deleted.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setConfirmDelete(false)} className="btn-secondary text-sm">
                Cancel
              </button>
              <button
                onClick={() => {
                  setConfirmDelete(false);
                  deleteRole();
                }}
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
