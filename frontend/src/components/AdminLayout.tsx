import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Shield, LogOut } from 'lucide-react';
import { clsx } from 'clsx';
import { getSidebarByRole, getRoleLabel, SidebarItem } from '@/config/sidebar';

export default function AdminLayout() {
  const { user, permissions, logout } = useAuthStore();
  const navigate = useNavigate();

  const roles = permissions?.roles || [];
  const items = getSidebarByRole(roles);
  const brandLabel = getRoleLabel(roles);
  const homeRoute = items.find((i) => i.section === 'main')?.to || '/dashboard';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const main = items.filter((i) => i.section === 'main');
  const self = items.filter((i) => i.section === 'self');

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-gray-900 text-gray-300 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <Link to={homeRoute} className="flex items-center gap-2 text-white font-bold">
            <Shield className="w-5 h-5" />
            {brandLabel}
          </Link>
          <p className="text-xs text-gray-500 mt-2 truncate">{user?.email}</p>
        </div>

        <nav className="flex-1 p-3 space-y-1 text-sm">
          {main.map((item) => (
            <SidebarLink key={item.to} item={item} />
          ))}

          {self.length > 0 && (
            <div className="border-t border-gray-800 mt-4 pt-4">
              {self.map((item) => (
                <SidebarLink key={item.to} item={item} />
              ))}
            </div>
          )}
        </nav>

        <button
          onClick={handleLogout}
          className="m-3 flex items-center gap-2 text-sm text-gray-400 hover:text-white px-3 py-2 rounded"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </aside>

      <main className="flex-1 bg-gray-50 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}

function SidebarLink({ item }: { item: SidebarItem }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end
      className={({ isActive }) =>
        clsx(
          'flex items-center gap-2 px-3 py-2 rounded transition-colors',
          isActive ? 'bg-gray-800 text-white' : 'hover:bg-gray-800 hover:text-white',
        )
      }
    >
      <Icon className="w-4 h-4" />
      {item.label}
    </NavLink>
  );
}
