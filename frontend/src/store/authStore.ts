import { create } from 'zustand';
import { User, UserPermissions, authService, permissionService } from '@/services/auth';
import { storage } from '@/utils/storage';
import { extractErrorMessage } from '@/utils/errors';

interface AuthState {
  user: User | null;
  permissions: UserPermissions | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<UserPermissions | null>;
  register: (email: string, password: string, full_name?: string) => Promise<void>;
  logout: () => Promise<void>;
  globalLogout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  fetchPermissions: () => Promise<UserPermissions | null>;

  hasPermission: (p: string) => boolean;
  hasAnyPermission: (ps: string[]) => boolean;
  hasRole: (role: string) => boolean;
  ownsClient: (clientDbId: string) => boolean;
  primaryDashboard: () => string;

  setUser: (user: User | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  permissions: null,
  isAuthenticated: !!storage.getAccessToken(),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      await authService.login({ email, password });
      const user = await authService.getMe();
      const permissions = await permissionService.getMyPermissions().catch(() => null);
      set({ user, permissions, isAuthenticated: true, isLoading: false });
      return permissions;
    } catch (err: any) {
      set({ error: extractErrorMessage(err, 'Login failed'), isLoading: false });
      throw err;
    }
  },

  register: async (email, password, full_name) => {
    set({ isLoading: true, error: null });
    try {
      await authService.register({ email, password, full_name });
      set({ isLoading: false });
    } catch (err: any) {
      set({ error: extractErrorMessage(err, 'Registration failed'), isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    await authService.logout();
    set({ user: null, permissions: null, isAuthenticated: false });
  },

  globalLogout: async () => {
    await authService.globalLogout();
    set({ user: null, permissions: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    if (!storage.getAccessToken()) return;
    set({ isLoading: true });
    try {
      const user = await authService.getMe();
      const permissions = await permissionService.getMyPermissions().catch(() => null);
      set({ user, permissions, isAuthenticated: true, isLoading: false });
    } catch {
      storage.clearTokens();
      set({ user: null, permissions: null, isAuthenticated: false, isLoading: false });
    }
  },

  fetchPermissions: async () => {
    try {
      const permissions = await permissionService.getMyPermissions();
      set({ permissions });
      return permissions;
    } catch {
      return null;
    }
  },

  hasPermission: (permission) => {
    const p = get().permissions;
    return !!p && p.permissions.includes(permission);
  },
  hasAnyPermission: (permissions) => {
    const p = get().permissions;
    return !!p && permissions.some((perm) => p.permissions.includes(perm));
  },
  hasRole: (role) => {
    const p = get().permissions;
    return !!p && p.roles.includes(role);
  },
  ownsClient: (clientDbId) => {
    const p = get().permissions;
    return !!p && p.owned_client_ids.includes(clientDbId);
  },
  primaryDashboard: () => {
    const p = get().permissions;
    if (!p) return '/dashboard';
    if (p.is_super_admin || p.roles.includes('super_admin')) return '/admin/dashboard';
    if (p.roles.includes('app_admin')) return '/app-admin/dashboard';
    return '/dashboard';
  },

  setUser: (user) => set({ user, isAuthenticated: !!user }),
  clearError: () => set({ error: null }),
}));
