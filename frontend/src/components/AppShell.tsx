import { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Shield, LogOut, Menu, X, ChevronDown, Search,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useAuthStore } from '@/store/authStore';
import { getSidebarByRole, getRoleLabel, SidebarItem } from '@/config/sidebar';

export default function AppShell() {
  const { user, permissions, logout } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const roles = permissions?.roles || [];
  const items = getSidebarByRole(roles);
  const brandLabel = getRoleLabel(roles);
  const main = items.filter((i) => i.section === 'main');
  const self = items.filter((i) => i.section === 'self');
  const homeRoute = main[0]?.to || '/dashboard';

  const handleLogout = async () => {
    await logout();
    // Force redirect to the production landing page
    window.location.href = 'https://wytnet.com';
  };

  const isSuperAdmin = roles.includes('super_admin');
  const isAppAdmin = roles.includes('app_admin');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 flex flex-col transition-transform lg:translate-x-0',
        mobileOpen ? 'translate-x-0' : '-translate-x-full',
      )}>
        {/* Brand */}
        <Link
          to={homeRoute}
          onClick={() => setMobileOpen(false)}
          className="flex items-center gap-2.5 px-5 h-16 border-b border-gray-100"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-sm leading-tight">SSO</p>
            <p className="text-[10px] uppercase tracking-wider text-gray-400 font-medium">
              {brandLabel}
            </p>
          </div>
        </Link>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          {main.length > 0 && (
            <SidebarSection title={isSuperAdmin ? 'Platform' : isAppAdmin ? 'Application' : 'Account'}>
              {main.map((item) => (
                <SidebarLink
                  key={item.to}
                  item={item}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </SidebarSection>
          )}

          {self.length > 0 && (
            <SidebarSection title="Personal">
              {self.map((item) => (
                <SidebarLink
                  key={item.to}
                  item={item}
                  onClick={() => setMobileOpen(false)}
                />
              ))}
            </SidebarSection>
          )}
        </nav>

        {/* User card */}
        <div className="border-t border-gray-100 p-3 relative">
          <button
            onClick={() => setUserMenuOpen((v) => !v)}
            className="w-full flex items-center gap-2.5 p-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <Avatar user={user} />
            <div className="flex-1 text-left min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user?.full_name || 'Account'}
              </p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
            <ChevronDown className={clsx(
              'w-4 h-4 text-gray-400 transition-transform',
              userMenuOpen && 'rotate-180'
            )} />
          </button>

          {userMenuOpen && (
            <div className="absolute bottom-full left-3 right-3 mb-2 bg-white rounded-lg shadow-lg border border-gray-200 py-1 text-sm">
              <Link
                to="/profile"
                onClick={() => { setUserMenuOpen(false); setMobileOpen(false); }}
                className="block px-3 py-2 hover:bg-gray-50 text-gray-700"
              >
                View profile
              </Link>
              <Link
                to="/security"
                onClick={() => { setUserMenuOpen(false); setMobileOpen(false); }}
                className="block px-3 py-2 hover:bg-gray-50 text-gray-700"
              >
                Security
              </Link>
              <hr className="my-1 border-gray-100" />
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-red-50 text-red-600 text-left"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main column */}
      <div className="lg:pl-64">
        {/* Topbar — mobile + breadcrumb */}
        <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-gray-100 h-14 px-4 lg:px-8 flex items-center gap-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="hidden md:flex items-center gap-2 flex-1 max-w-md">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search…"
              className="bg-transparent text-sm outline-none flex-1 placeholder-gray-400"
            />
          </div>

          <div className="flex-1 lg:flex-none" />

          <RoleBadge roles={roles} />
        </header>

        {/* Page content */}
        <main className="px-4 lg:px-8 py-6 lg:py-8 max-w-7xl mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <p className="px-3 text-[10px] uppercase tracking-wider text-gray-400 font-semibold mb-2">
        {title}
      </p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function SidebarLink({ item, onClick }: { item: SidebarItem; onClick?: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end
      onClick={onClick}
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary-50 text-primary-700'
            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
        )
      }
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span className="flex-1">{item.label}</span>
    </NavLink>
  );
}

function Avatar({ user }: { user: any }) {
  if (user?.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt=""
        className="w-9 h-9 rounded-full object-cover shrink-0"
      />
    );
  }
  const initial = (user?.full_name || user?.email || '?')[0].toUpperCase();
  return (
    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center font-semibold text-sm shrink-0">
      {initial}
    </div>
  );
}

function RoleBadge({ roles }: { roles: string[] }) {
  const isSuper = roles.includes('super_admin');
  const isApp = roles.includes('app_admin');
  if (!isSuper && !isApp) return null;

  return (
    <span className={clsx(
      'text-[10px] uppercase tracking-wider font-semibold px-2 py-1 rounded-full',
      isSuper ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800',
    )}>
      {isSuper ? 'Super Admin' : 'App Admin'}
    </span>
  );
}
