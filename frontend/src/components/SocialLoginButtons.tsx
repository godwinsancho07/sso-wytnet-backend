import { authService } from '@/services/auth';

const PROVIDERS = [
  { name: 'google', label: 'Google', color: 'hover:bg-red-50 border-gray-300' },
  { name: 'github', label: 'GitHub', color: 'hover:bg-gray-100 border-gray-300' },
  { name: 'microsoft', label: 'Microsoft', color: 'hover:bg-blue-50 border-gray-300' },
  { name: 'linkedin', label: 'LinkedIn', color: 'hover:bg-sky-50 border-gray-300' },
] as const;

export default function SocialLoginButtons() {
  const handleSocialLogin = (provider: string) => {
    window.location.href = authService.getSocialLoginUrl(provider);
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      {PROVIDERS.map(({ name, label, color }) => (
        <button
          key={name}
          type="button"
          onClick={() => handleSocialLogin(name)}
          className={`flex items-center justify-center gap-2 rounded-lg border bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition-colors ${color}`}
        >
          <ProviderIcon name={name} />
          {label}
        </button>
      ))}
    </div>
  );
}

function ProviderIcon({ name }: { name: string }) {
  const icons: Record<string, string> = {
    google: 'G',
    github: '⌥',
    microsoft: '⊞',
    linkedin: 'in',
  };
  return (
    <span className="w-5 h-5 flex items-center justify-center text-xs font-bold rounded">
      {icons[name] || name[0].toUpperCase()}
    </span>
  );
}
