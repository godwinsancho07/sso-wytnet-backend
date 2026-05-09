import api from './api';
import { storage } from '@/utils/storage';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
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

export interface SocialAccount {
  id: string;
  provider: string;
  provider_email: string | null;
  created_at: string;
}

export interface Session {
  id: string;
  device_info: string | null;
  ip_address: string | null;
  user_agent: string | null;
  is_revoked: boolean;
  expires_at: string;
  last_active_at: string;
  created_at: string;
}

export const authService = {
  async register(payload: RegisterPayload) {
    const { data } = await api.post('/auth/register', payload);
    return data;
  },

  async login(payload: LoginPayload): Promise<AuthTokens> {
    const { data } = await api.post<AuthTokens>('/auth/login', payload);
    storage.setAccessToken(data.access_token);
    storage.setRefreshToken(data.refresh_token);
    return data;
  },

  async logout(): Promise<void> {
    await api.post('/auth/logout').catch(() => {});
    storage.clearTokens();
  },

  async globalLogout(): Promise<void> {
    await api.post('/auth/logout/all').catch(() => {});
    storage.clearTokens();
  },

  async getMe(): Promise<User> {
    const { data } = await api.get<User>('/auth/me');
    return data;
  },

  async forgotPassword(email: string): Promise<void> {
    await api.post('/auth/forgot-password', { email });
  },

  async resetPassword(token: string, new_password: string): Promise<void> {
    await api.post('/auth/reset-password', { token, new_password });
  },

  async verifyEmail(token: string): Promise<void> {
    await api.post('/auth/verify-email', { token });
  },

  async changePassword(current_password: string, new_password: string): Promise<void> {
    await api.post('/auth/change-password', { current_password, new_password });
  },

  getSocialLoginUrl(provider: string): string {
    return `${import.meta.env.VITE_API_URL || ''}/auth/${provider}`;
  },
};

export const userService = {
  async updateProfile(data: { full_name?: string; avatar_url?: string }): Promise<User> {
    const { data: user } = await api.patch<User>('/v1/users/me', data);
    return user;
  },

  async getSocialAccounts(): Promise<SocialAccount[]> {
    const { data } = await api.get<SocialAccount[]>('/v1/users/me/social-accounts');
    return data;
  },

  async unlinkSocialAccount(provider: string): Promise<void> {
    await api.delete(`/v1/users/me/social-accounts/${provider}`);
  },
};

export interface UserPermissions {
  user_id: string;
  email: string;
  is_super_admin: boolean;
  roles: string[];
  permissions: string[];
  owned_client_ids: string[];
}

export const permissionService = {
  async getMyPermissions(): Promise<UserPermissions> {
    const { data } = await api.get<UserPermissions>('/auth/me/permissions');
    return data;
  },
};

export const sessionService = {
  async getSessions(): Promise<Session[]> {
    const { data } = await api.get<Session[]>('/v1/sessions');
    return data;
  },

  async revokeSession(sessionId: string): Promise<void> {
    await api.delete(`/v1/sessions/${sessionId}`);
  },

  async revokeAllSessions(): Promise<void> {
    await api.delete('/v1/sessions');
  },
};
