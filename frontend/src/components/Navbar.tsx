import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { LogOut, Shield, User, Monitor, Briefcase, Lock } from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white border-b border-gray-200 px-4">
      <div className="mx-auto max-w-5xl flex items-center justify-between h-16">
        <Link to="/dashboard" className="flex items-center gap-2 font-bold text-primary-700 text-lg">
          <Shield className="w-6 h-6" />
          SSO
        </Link>

        <div className="hidden md:flex items-center gap-1">
          <NavLink to="/dashboard" icon={<Shield className="w-4 h-4" />}>Dashboard</NavLink>
          <NavLink to="/profile" icon={<User className="w-4 h-4" />}>Profile</NavLink>
          <NavLink to="/sessions" icon={<Monitor className="w-4 h-4" />}>Sessions</NavLink>
          <NavLink to="/applications" icon={<Briefcase className="w-4 h-4" />}>Apps</NavLink>
          <NavLink to="/security" icon={<Lock className="w-4 h-4" />}>Security</NavLink>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600 hidden md:block">
            {user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-red-600 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}

function NavLink({ to, icon, children }: { to: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:text-primary-700 hover:bg-primary-50 transition-colors"
    >
      {icon}
      {children}
    </Link>
  );
}
