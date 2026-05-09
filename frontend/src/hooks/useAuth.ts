import { useAuthStore } from '@/store/authStore';

export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const error = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const register = useAuthStore((s) => s.register);
  const logout = useAuthStore((s) => s.logout);
  const globalLogout = useAuthStore((s) => s.globalLogout);
  const fetchUser = useAuthStore((s) => s.fetchUser);
  const clearError = useAuthStore((s) => s.clearError);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    globalLogout,
    fetchUser,
    clearError,
    isSuperuser: user?.is_superuser ?? false,
  };
}
