/**
 * Central sidebar registry.
 *
 * Adding a new role = adding a new entry to `SIDEBAR_BY_ROLE`.
 * No layout code changes.
 *
 * Core principle: Role determines dashboard. Permission determines actions.
 */
import {
  Home, Users, Briefcase, Lock, FileText, Activity, Shield,
  AlertTriangle, BarChart3, Link2, Settings, KeySquare, Globe,
  BarChart2, Layers,
} from 'lucide-react';

export interface SidebarItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Optional permission required to render this item. Frontend hint only — backend still enforces. */
  permission?: string;
  /** Section label (groups sidebar items) */
  section?: 'main' | 'self' | 'system';
}

export const SIDEBAR_BY_ROLE: Record<string, SidebarItem[]> = {
  super_admin: [
    // Platform
    { to: '/admin/dashboard',   label: 'Overview',          icon: Home,          section: 'main' },
    { to: '/admin/users',       label: 'Users',             icon: Users,         section: 'main' },
    { to: '/admin/clients',     label: 'OAuth Clients',     icon: Briefcase,     section: 'main' },
    { to: '/admin/roles',       label: 'Roles',             icon: Lock,          section: 'main' },
    { to: '/admin/permissions', label: 'Permissions',       icon: Layers,        section: 'main' },
    { to: '/admin/sessions',    label: 'Sessions',          icon: Activity,      section: 'main' },
    { to: '/admin/audit-logs',  label: 'Audit Logs',        icon: FileText,      section: 'main' },
    { to: '/admin/security',    label: 'Security Center',   icon: Shield,        section: 'main' },
    { to: '/admin/providers',   label: 'Social Providers',  icon: Globe,         section: 'main' },
    { to: '/admin/reports',     label: 'Reports',           icon: BarChart2,     section: 'main' },
    { to: '/admin/settings',    label: 'Settings',          icon: Settings,      section: 'system' },
    // Self
    { to: '/profile',           label: 'My Profile',        icon: Users,         section: 'self' },
    { to: '/sessions',          label: 'My Sessions',       icon: Activity,      section: 'self' },
    { to: '/security',          label: 'My Security',       icon: KeySquare,     section: 'self' },
  ],

  app_admin: [
    { to: '/app-admin/dashboard', label: 'Overview',     icon: Home,         section: 'main' },
    { to: '/app-admin/clients',   label: 'My Apps',      icon: Briefcase,    section: 'main' },
    // Self
    { to: '/profile',             label: 'Profile',      icon: Users,        section: 'self' },
    { to: '/sessions',            label: 'Sessions',     icon: Activity,     section: 'self' },
    { to: '/security',            label: 'Security',     icon: KeySquare,    section: 'self' },
  ],

  user: [
    { to: '/dashboard',     label: 'Dashboard',       icon: Home,    section: 'main' },
    { to: '/profile',       label: 'Profile',         icon: Users,   section: 'main' },
    { to: '/applications',  label: 'Connected Apps',  icon: Link2,   section: 'main' },
    { to: '/sessions',      label: 'Sessions',        icon: Activity,section: 'main' },
    { to: '/security',      label: 'Security',        icon: Lock,    section: 'main' },
  ],
};

/**
 * Pick the sidebar matching the highest-privileged role the user has.
 * Order: super_admin > app_admin > user.
 */
export function getSidebarByRole(roles: string[]): SidebarItem[] {
  if (roles.includes('super_admin')) return SIDEBAR_BY_ROLE.super_admin;
  if (roles.includes('app_admin'))   return SIDEBAR_BY_ROLE.app_admin;
  return SIDEBAR_BY_ROLE.user;
}

/** Brand label for the sidebar header */
export function getRoleLabel(roles: string[]): string {
  if (roles.includes('super_admin')) return 'Platform Admin';
  if (roles.includes('app_admin'))   return 'App Admin';
  return 'My Account';
}
