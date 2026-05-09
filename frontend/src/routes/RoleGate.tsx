import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { storage } from '@/utils/storage';

interface Props {
  children: React.ReactNode;
  /** Require ALL of these permissions (any one missing → redirect) */
  requirePermissions?: string[];
  /** Require ANY of these roles */
  requireRoles?: string[];
  /** Where to redirect if denied */
  fallback?: string;
}

export default function RoleGate({
  children,
  requirePermissions = [],
  requireRoles = [],
  fallback,
}: Props) {
  const { isAuthenticated, permissions, hasPermission, hasRole } = useAuthStore();

  if (!isAuthenticated && !storage.getAccessToken()) {
    return <Navigate to="/login" replace />;
  }

  // Permissions still loading — let page render; API will 403 if needed
  if (!permissions) return <>{children}</>;

  if (requirePermissions.length && !requirePermissions.every(hasPermission)) {
    return <Navigate to={fallback || '/dashboard'} replace />;
  }
  if (requireRoles.length && !requireRoles.some(hasRole)) {
    return <Navigate to={fallback || '/dashboard'} replace />;
  }

  return <>{children}</>;
}
