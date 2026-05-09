import api from './api';

export interface MetricsOverview {
  // Users
  total_users: number;
  active_users: number;
  inactive_users: number;
  blocked_users: number;
  verified_users: number;
  unverified_users: number;
  // Auth
  total_logins_today: number;
  successful_logins_24h: number;
  failed_logins_24h: number;
  social_logins_24h: number;
  password_logins_24h: number;
  mfa_logins_24h: number;
  password_reset_requests_24h: number;
  registrations_24h: number;
  // OAuth
  total_clients: number;
  active_clients: number;
  disabled_clients: number;
  tokens_today: number;
  tokens_revoked_24h: number;
  refresh_tokens_active: number;
  // Sessions
  active_sessions: number;
  expired_sessions: number;
  revoked_sessions: number;
  // Security
  suspicious_logins: number;
  blocked_ips: number;
  rate_limit_hits_24h: number;
  account_lockouts: number;
  generated_at: string;
}

export interface SecurityAlert {
  severity: 'low' | 'medium' | 'high';
  type: string;
  title: string;
  detail: string;
  ip?: string;
  count?: number;
}

export interface AuditEvent {
  id: string;
  user_id: string | null;
  event_type: string;
  ip_address: string | null;
  user_agent: string | null;
  metadata: any;
  created_at: string;
}

export interface TopApp {
  app_name: string;
  client_id: string;
  tokens_7d: number;
}

export interface AppOverview {
  client_id: string;
  active_tokens: number;
  tokens_24h: number;
  tokens_7d: number;
  authorized_users: number;
  active_refresh_tokens: number;
  generated_at: string;
}

export interface AppUser {
  user_id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  last_seen: string | null;
}

export interface AuthorizedApp {
  id: string;
  client_id: string;
  app_name: string;
  logo_url: string | null;
  authorized_at: string | null;
  token_count: number;
}

export const appAdminService = {
  async getMetrics(clientDbId: string): Promise<AppOverview> {
    const { data } = await api.get<AppOverview>(`/v1/clients/${clientDbId}/metrics`);
    return data;
  },
  async getRecentUsers(clientDbId: string, limit = 20): Promise<AppUser[]> {
    const { data } = await api.get<AppUser[]>(
      `/v1/clients/${clientDbId}/recent-users`,
      { params: { limit } },
    );
    return data;
  },
};

export const userActivityService = {
  async getActivity(limit = 20): Promise<AuditEvent[]> {
    const { data } = await api.get<AuditEvent[]>('/v1/me/activity', { params: { limit } });
    return data;
  },
  async getAuthorizedApps(): Promise<AuthorizedApp[]> {
    const { data } = await api.get<AuthorizedApp[]>('/v1/me/authorized-apps');
    return data;
  },
  async revokeApp(clientDbId: string): Promise<void> {
    await api.delete(`/v1/me/authorized-apps/${clientDbId}`);
  },
};

export interface AdminUserRoleRef {
  id: string;
  name: string;
}

export interface AdminUserListItem {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  email_verified: boolean;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
  roles: AdminUserRoleRef[];
  providers: string[];
  active_sessions: number;
  connected_apps: number;
}

export interface AdminUserListResponse {
  items: AdminUserListItem[];
  offset: number;
  limit: number;
  count: number;
}

export interface AdminUserDetailUser {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  email_verified: boolean;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminUserDetailRole {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface AdminUserDetailSession {
  id: string;
  device_info: string | null;
  ip_address: string | null;
  user_agent: string | null;
  is_revoked: boolean;
  expires_at: string;
  last_active_at: string;
  created_at: string;
}

export interface AdminUserDetailSocial {
  id: string;
  provider: string;
  provider_email: string | null;
  created_at: string;
}

export interface AdminUserDetail {
  user: AdminUserDetailUser;
  roles: AdminUserDetailRole[];
  sessions: AdminUserDetailSession[];
  social_accounts: AdminUserDetailSocial[];
  recent_audit: AuditEvent[];
}

export type UserStatusFilter = 'active' | 'suspended' | 'unverified' | undefined;

export const usersAdminService = {
  async searchUsers(
    q?: string,
    status?: UserStatusFilter,
    offset = 0,
    limit = 50,
  ): Promise<AdminUserListResponse> {
    const params: Record<string, string | number> = { offset, limit };
    if (q) params.q = q;
    if (status) params.status = status;
    const { data } = await api.get<AdminUserListResponse>('/v1/users', { params });
    return data;
  },

  async getUserDetail(userId: string): Promise<AdminUserDetail> {
    const { data } = await api.get<AdminUserDetail>(`/v1/users/${userId}/detail`);
    return data;
  },

  async suspend(userId: string): Promise<void> {
    await api.patch(`/v1/users/${userId}/deactivate`);
  },

  async activate(userId: string): Promise<void> {
    await api.patch(`/v1/users/${userId}/activate`);
  },

  async forceLogout(userId: string): Promise<void> {
    await api.post(`/v1/users/${userId}/force-logout`);
  },

  async adminResetPassword(userId: string): Promise<{ message: string }> {
    const { data } = await api.post(`/v1/users/${userId}/admin-reset-password`);
    return data;
  },

  async deleteUser(userId: string): Promise<void> {
    await api.delete(`/v1/users/${userId}`);
  },

  async assignRole(userId: string, roleId: string): Promise<void> {
    await api.post('/v1/roles/assign', { user_id: userId, role_id: roleId });
  },

  async removeRole(userId: string, roleId: string): Promise<void> {
    await api.post('/v1/roles/remove', { user_id: userId, role_id: roleId });
  },

  async listRoles(): Promise<AdminUserDetailRole[]> {
    const { data } = await api.get<AdminUserDetailRole[]>('/v1/roles');
    return data;
  },
};

export const adminService = {
  async getOverview(): Promise<MetricsOverview> {
    // Try the rich full-overview first; fall back to basic overview
    try {
      const { data } = await api.get<MetricsOverview>('/v1/metrics/full-overview');
      return data;
    } catch {
      const { data } = await api.get<MetricsOverview>('/v1/metrics/overview');
      return data;
    }
  },
  async getSecurityAlerts(): Promise<SecurityAlert[]> {
    const { data } = await api.get<SecurityAlert[]>('/v1/security/alerts');
    return data;
  },
  async getRecentAudit(limit = 25): Promise<AuditEvent[]> {
    const { data } = await api.get<AuditEvent[]>('/v1/audit/recent', {
      params: { limit },
    });
    return data;
  },
  async getTopApps(limit = 5): Promise<TopApp[]> {
    const { data } = await api.get<TopApp[]>('/v1/metrics/top-apps', {
      params: { limit },
    });
    return data;
  },
};

// ── Roles & Permissions admin ────────────────────────────────────────────────

export interface AdminPermission {
  id: string;
  name: string;
  description: string | null;
  resource: string;
  action: string;
}

export interface AdminPermissionWithUsage extends AdminPermission {
  role_count: number;
}

export interface AdminRole {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface AdminRoleDetail extends AdminRole {
  permissions: AdminPermission[];
  user_count: number;
  is_protected: boolean;
}

export type AdminPermissionsByResource = Record<string, AdminPermissionWithUsage[]>;

export const rolesAdminService = {
  async list(): Promise<AdminRole[]> {
    const { data } = await api.get<AdminRole[]>('/v1/roles');
    return data;
  },
  async get(roleId: string): Promise<AdminRoleDetail> {
    const { data } = await api.get<AdminRoleDetail>(`/v1/roles/${roleId}`);
    return data;
  },
  async create(body: { name: string; description?: string }): Promise<AdminRole> {
    const { data } = await api.post<AdminRole>('/v1/roles', body);
    return data;
  },
  async update(
    roleId: string,
    body: { name?: string; description?: string },
  ): Promise<AdminRole> {
    const { data } = await api.patch<AdminRole>(`/v1/roles/${roleId}`, body);
    return data;
  },
  async remove(roleId: string): Promise<void> {
    await api.delete(`/v1/roles/${roleId}`);
  },
  async grantPermission(roleId: string, permissionId: string): Promise<void> {
    await api.post(`/v1/roles/${roleId}/permissions`, {
      permission_id: permissionId,
    });
  },
  async revokePermission(roleId: string, permissionId: string): Promise<void> {
    await api.delete(`/v1/roles/${roleId}/permissions/${permissionId}`);
  },
  async assignUser(userId: string, roleId: string): Promise<void> {
    await api.post('/v1/roles/assign', { user_id: userId, role_id: roleId });
  },
  async removeUser(userId: string, roleId: string): Promise<void> {
    await api.post('/v1/roles/remove', { user_id: userId, role_id: roleId });
  },
};

export const permissionsAdminService = {
  async list(): Promise<AdminPermissionsByResource> {
    const { data } = await api.get<AdminPermissionsByResource>('/v1/permissions');
    return data;
  },
  async create(body: {
    name: string;
    resource: string;
    action: string;
    description?: string;
  }): Promise<AdminPermission> {
    const { data } = await api.post<AdminPermission>('/v1/permissions', body);
    return data;
  },
  async remove(permissionId: string): Promise<void> {
    await api.delete(`/v1/permissions/${permissionId}`);
  },
};

// ── Admin: Sessions across all users ────────────────────────────────────────

export interface AdminSession {
  id: string;
  user_id: string;
  user_email: string | null;
  user_full_name: string | null;
  user_avatar_url: string | null;
  device_info: string | null;
  ip_address: string | null;
  user_agent: string | null;
  is_revoked: boolean;
  is_expired: boolean;
  status: 'active' | 'expired' | 'revoked';
  expires_at: string | null;
  last_active_at: string | null;
  created_at: string | null;
}

export interface AdminSessionsResponse {
  items: AdminSession[];
  offset: number;
  limit: number;
  count: number;
}

export const adminSessionsService = {
  async list(
    params: {
      user_id?: string;
      status?: 'active' | 'expired' | 'revoked';
      offset?: number;
      limit?: number;
    } = {},
  ): Promise<AdminSessionsResponse> {
    const { data } = await api.get<AdminSessionsResponse>('/v1/admin/sessions', {
      params,
    });
    return data;
  },
  async revoke(sessionId: string): Promise<void> {
    await api.delete(`/v1/admin/sessions/${sessionId}`);
  },
  async revokeAllForUser(
    userId: string,
  ): Promise<{ revoked_sessions: number; revoked_refresh_tokens: number }> {
    const { data } = await api.post(`/v1/admin/sessions/revoke-user/${userId}`);
    return data;
  },
};

// ── Admin: OAuth Client CRUD + admin assignment ─────────────────────────────

export interface OAuthClientRead {
  id: string;
  client_id: string;
  app_name: string;
  description: string | null;
  logo_url: string | null;
  redirect_uris: string[];
  allowed_scopes: string[];
  is_active: boolean;
  is_confidential: boolean;
  require_pkce: boolean;
  created_at: string;
}

export interface OAuthClientWithSecret extends OAuthClientRead {
  client_secret: string;
}

export interface OAuthClientCreatePayload {
  app_name: string;
  description?: string | null;
  logo_url?: string | null;
  redirect_uris: string[];
  allowed_scopes: string[];
  is_confidential?: boolean;
  require_pkce?: boolean;
}

export interface OAuthClientUpdatePayload {
  app_name?: string;
  description?: string | null;
  logo_url?: string | null;
  redirect_uris?: string[];
  allowed_scopes?: string[];
  is_active?: boolean;
  require_pkce?: boolean;
}

export interface ClientAdminUser {
  user_id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  assigned_at: string;
}

export const clientsAdminService = {
  async list(): Promise<OAuthClientRead[]> {
    const { data } = await api.get<OAuthClientRead[]>('/v1/clients');
    return data;
  },
  async get(clientDbId: string): Promise<OAuthClientRead> {
    const { data } = await api.get<OAuthClientRead>(`/v1/clients/${clientDbId}`);
    return data;
  },
  async create(payload: OAuthClientCreatePayload): Promise<OAuthClientWithSecret> {
    const { data } = await api.post<OAuthClientWithSecret>('/v1/clients', payload);
    return data;
  },
  async update(
    clientDbId: string,
    payload: OAuthClientUpdatePayload,
  ): Promise<OAuthClientRead> {
    const { data } = await api.patch<OAuthClientRead>(
      `/v1/clients/${clientDbId}`,
      payload,
    );
    return data;
  },
  async remove(clientDbId: string): Promise<void> {
    await api.delete(`/v1/clients/${clientDbId}`);
  },
  async rotateSecret(clientDbId: string): Promise<OAuthClientWithSecret> {
    const { data } = await api.post<OAuthClientWithSecret>(
      `/v1/clients/${clientDbId}/rotate-secret`,
    );
    return data;
  },

  /** Fetch personalized integration markdown for this client. */
  async getIntegrationDocs(clientDbId: string): Promise<string> {
    const { data } = await api.get<string>(
      `/v1/clients/${clientDbId}/integration-docs`,
      { responseType: 'text', transformResponse: (v) => v },
    );
    return data;
  },

  /** Trigger a browser download of the integration markdown. */
  async downloadIntegrationDocs(
    clientDbId: string,
    appName: string,
  ): Promise<void> {
    const md = await this.getIntegrationDocs(clientDbId);
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const safeName =
      appName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'client';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeName}-sso-integration.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  async listAdmins(clientDbId: string): Promise<ClientAdminUser[]> {
    const { data } = await api.get<ClientAdminUser[]>(
      `/v1/clients/${clientDbId}/admins`,
    );
    return data;
  },
  async assignAdmin(clientDbId: string, userId: string): Promise<ClientAdminUser> {
    const { data } = await api.post<ClientAdminUser>(
      `/v1/clients/${clientDbId}/admins`,
      { user_id: userId },
    );
    return data;
  },
  async removeAdmin(clientDbId: string, userId: string): Promise<void> {
    await api.delete(`/v1/clients/${clientDbId}/admins/${userId}`);
  },
};

// ── Security Center (admin) ──────────────────────────────────────────────────

export interface BlockedIP {
  id: string;
  ip_address: string;
  reason: string | null;
  blocked_by_user_id: string | null;
  created_at: string;
  expires_at: string | null;
  is_expired: boolean;
}

export interface LockedAccount {
  user_id: string;
  email: string;
  full_name: string | null;
  failed_login_count: number;
  locked_until: string | null;
  is_locked: boolean;
}

export const securityService = {
  async listBlockedIPs(): Promise<BlockedIP[]> {
    const { data } = await api.get<BlockedIP[]>('/v1/security/blocked-ips');
    return data;
  },
  async blockIP(
    ip: string,
    reason?: string,
    expires_at?: string | null,
  ): Promise<BlockedIP> {
    const { data } = await api.post<BlockedIP>('/v1/security/blocked-ips', {
      ip,
      reason: reason || null,
      expires_at: expires_at || null,
    });
    return data;
  },
  async unblockIP(ip: string): Promise<void> {
    await api.delete(`/v1/security/blocked-ips/${encodeURIComponent(ip)}`);
  },
  async listLockedAccounts(): Promise<LockedAccount[]> {
    const { data } = await api.get<LockedAccount[]>('/v1/security/locked-accounts');
    return data;
  },
  async unlockUser(userId: string): Promise<void> {
    await api.post(`/v1/security/users/${userId}/unlock`);
  },
  async forceMFA(userId: string): Promise<void> {
    await api.post(`/v1/security/users/${userId}/force-mfa`);
  },
};

// ── MFA self-service ─────────────────────────────────────────────────────────

export interface MFAStatus {
  is_enabled: boolean;
  is_required: boolean;
  last_used_at: string | null;
}

export interface MFASetupData {
  secret: string;
  otpauth_uri: string;
  backup_codes: string[];
}

export const mfaService = {
  async getStatus(): Promise<MFAStatus> {
    const { data } = await api.get<MFAStatus>('/v1/me/mfa/status');
    return data;
  },
  async setup(): Promise<MFASetupData> {
    const { data } = await api.get<MFASetupData>('/v1/me/mfa/setup');
    return data;
  },
  async confirm(code: string): Promise<{ is_enabled: boolean }> {
    const { data } = await api.post<{ is_enabled: boolean }>('/v1/me/mfa/confirm', {
      code,
    });
    return data;
  },
  async disable(password: string): Promise<{ is_enabled: boolean }> {
    const { data } = await api.post<{ is_enabled: boolean }>('/v1/me/mfa/disable', {
      password,
    });
    return data;
  },
};

// ── Provider settings admin ──────────────────────────────────────────────────

export interface ProviderListItem {
  provider: string;
  is_enabled: boolean;
  configured: boolean;
  client_id: string | null;
  redirect_uri: string | null;
  env_redirect_uri: string | null;
  has_secret: boolean;
  source: 'env' | 'db';
  updated_at: string | null;
  updated_by_user_id: string | null;
}

export interface ProviderUsage {
  provider: string;
  window_days: number;
  logins: number;
  registrations: number;
  account_links: number;
  failures: number;
}

export interface ProviderUpdatePayload {
  client_id?: string | null;
  client_secret?: string | null;
  redirect_uri?: string | null;
  is_enabled?: boolean;
}

export const providersService = {
  async list(): Promise<ProviderListItem[]> {
    const { data } = await api.get<ProviderListItem[]>('/v1/admin/providers');
    return data;
  },
  async update(provider: string, payload: ProviderUpdatePayload): Promise<ProviderListItem> {
    const { data } = await api.patch<ProviderListItem>(
      `/v1/admin/providers/${provider}`,
      payload,
    );
    return data;
  },
  async enable(provider: string): Promise<ProviderListItem> {
    const { data } = await api.post<ProviderListItem>(`/v1/admin/providers/${provider}/enable`);
    return data;
  },
  async disable(provider: string): Promise<ProviderListItem> {
    const { data } = await api.post<ProviderListItem>(`/v1/admin/providers/${provider}/disable`);
    return data;
  },
  async usage(provider: string): Promise<ProviderUsage> {
    const { data } = await api.get<ProviderUsage>(`/v1/admin/providers/${provider}/usage`);
    return data;
  },
};

// ── Reports ──────────────────────────────────────────────────────────────────

export interface LoginSummaryDay {
  date: string;
  success: number;
  failed: number;
  social: number;
  registrations: number;
}

export interface UsersGrowthDay {
  date: string;
  new_users: number;
  total_users: number;
}

export interface OAuthUsageTopClient {
  client_db_id: string;
  app_name: string;
  client_id: string;
  tokens: number;
}

export interface OAuthUsageDaily {
  date: string;
  client_id: string;
  count: number;
}

export interface OAuthUsageReport {
  top_clients: OAuthUsageTopClient[];
  daily: OAuthUsageDaily[];
}

export interface ProviderBreakdownEntry {
  date: string;
  provider: string;
  count: number;
}

export const reportsService = {
  async loginSummary(days = 30): Promise<LoginSummaryDay[]> {
    const { data } = await api.get<LoginSummaryDay[]>('/v1/reports/login-summary', {
      params: { days },
    });
    return data;
  },
  async usersGrowth(days = 30): Promise<UsersGrowthDay[]> {
    const { data } = await api.get<UsersGrowthDay[]>('/v1/reports/users-growth', {
      params: { days },
    });
    return data;
  },
  async oauthUsage(days = 30): Promise<OAuthUsageReport> {
    const { data } = await api.get<OAuthUsageReport>('/v1/reports/oauth-usage', {
      params: { days },
    });
    return data;
  },
  async providerBreakdown(days = 30): Promise<ProviderBreakdownEntry[]> {
    const { data } = await api.get<ProviderBreakdownEntry[]>('/v1/reports/provider-breakdown', {
      params: { days },
    });
    return data;
  },
  async exportAuditCsv(opts: { from?: string; to?: string; event_type?: string }): Promise<void> {
    const params = new URLSearchParams();
    if (opts.from) params.set('from', opts.from);
    if (opts.to) params.set('to', opts.to);
    if (opts.event_type) params.set('event_type', opts.event_type);

    const response = await api.get('/v1/reports/audit.csv', {
      params: Object.fromEntries(params),
      responseType: 'blob',
    });
    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_${opts.from ?? 'start'}_${opts.to ?? 'now'}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};
