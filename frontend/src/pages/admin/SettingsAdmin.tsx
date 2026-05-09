import { useState } from 'react';
import {
  Settings, Clock, RefreshCw, Lock, Mail, Globe, Zap,
  Shield, Database, CheckCircle2, AlertTriangle, ChevronRight, Info,
} from 'lucide-react';
import { clsx } from 'clsx';

/* ─── Types ─────────────────────────────────────────────────────────────────── */
interface SettingGroup {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  fields: SettingField[];
}

interface SettingField {
  key: string;
  label: string;
  type: 'number' | 'text' | 'boolean' | 'textarea' | 'select';
  description?: string;
  placeholder?: string;
  options?: string[];
  unit?: string;
  danger?: boolean;
}

/* ─── Settings schema (drives UI — values are read-only from .env for now) ── */
const SETTINGS: SettingGroup[] = [
  {
    id: 'jwt',
    label: 'JWT & Token Configuration',
    icon: Clock,
    description: 'Configure token lifetimes and signing algorithm.',
    fields: [
      { key: 'ACCESS_TOKEN_EXPIRE_MINUTES', label: 'Access Token Expiry', type: 'number', unit: 'minutes', placeholder: '15', description: 'Short-lived access token lifetime. Recommended: 15 minutes.' },
      { key: 'REFRESH_TOKEN_EXPIRE_DAYS',   label: 'Refresh Token Expiry', type: 'number', unit: 'days',   placeholder: '30', description: 'Refresh token lifetime. Rotation is enabled.' },
      { key: 'ID_TOKEN_EXPIRE_MINUTES',     label: 'ID Token Expiry',      type: 'number', unit: 'minutes', placeholder: '60' },
      { key: 'AUTH_CODE_EXPIRE_MINUTES',    label: 'Authorization Code Expiry', type: 'number', unit: 'minutes', placeholder: '10', description: 'PKCE authorization codes expire after this window.' },
      { key: 'JWT_ALGORITHM',               label: 'Signing Algorithm', type: 'select', options: ['RS256', 'RS384', 'RS512'], description: 'RS256 is the OIDC standard.' },
    ],
  },
  {
    id: 'session',
    label: 'Session Management',
    icon: Database,
    description: 'Session lifetime and cookie security settings.',
    fields: [
      { key: 'SESSION_EXPIRE_DAYS', label: 'Session Expiry',   type: 'number', unit: 'days', placeholder: '7' },
      { key: 'SECURE_COOKIES',      label: 'Secure Cookies',   type: 'boolean', description: 'Requires HTTPS. Disable only in local development.' },
    ],
  },
  {
    id: 'security',
    label: 'Security & Rate Limiting',
    icon: Shield,
    description: 'Brute-force protection and rate limit thresholds.',
    fields: [
      { key: 'RATE_LIMIT_LOGIN',          label: 'Login Rate Limit',          type: 'text', placeholder: '10/minute', description: 'Format: N/period (e.g. 10/minute)' },
      { key: 'RATE_LIMIT_REGISTER',       label: 'Register Rate Limit',       type: 'text', placeholder: '5/minute' },
      { key: 'RATE_LIMIT_PASSWORD_RESET', label: 'Password Reset Rate Limit', type: 'text', placeholder: '3/minute' },
    ],
  },
  {
    id: 'email',
    label: 'Email / SMTP',
    icon: Mail,
    description: 'Outbound email server for verification and password-reset emails.',
    fields: [
      { key: 'SMTP_HOST',     label: 'SMTP Host',     type: 'text',    placeholder: 'smtp.example.com' },
      { key: 'SMTP_PORT',     label: 'SMTP Port',     type: 'number',  placeholder: '587' },
      { key: 'SMTP_USER',     label: 'SMTP User',     type: 'text',    placeholder: 'noreply@example.com' },
      { key: 'SMTP_FROM',     label: 'From Address',  type: 'text',    placeholder: 'noreply@sso.local' },
      { key: 'SMTP_TLS',      label: 'Enable TLS',    type: 'boolean' },
    ],
  },
  {
    id: 'cors',
    label: 'CORS & Allowed Origins',
    icon: Globe,
    description: 'Domains allowed to make cross-origin requests to the SSO API.',
    fields: [
      { key: 'ALLOWED_ORIGINS', label: 'Allowed Origins', type: 'textarea', placeholder: 'https://app1.example.com\nhttps://app2.example.com', description: 'One origin per line or comma-separated.' },
      { key: 'FRONTEND_URL',    label: 'Frontend URL',    type: 'text',     placeholder: 'https://sso.example.com' },
    ],
  },
  {
    id: 'oidc',
    label: 'OIDC Issuer',
    icon: Lock,
    description: 'OpenID Connect discovery settings.',
    fields: [
      { key: 'OIDC_ISSUER', label: 'OIDC Issuer', type: 'text', placeholder: 'https://sso.example.com', description: 'Must match the public base URL. Changing this invalidates existing tokens.' },
    ],
  },
];

export default function SettingsAdmin() {
  const [active, setActive] = useState(SETTINGS[0].id);

  const currentGroup = SETTINGS.find(g => g.id === active)!;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
        <p className="text-gray-500 text-sm mt-1">
          Platform-wide configuration. Settings are managed via environment variables and the database.
        </p>
      </div>

      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-blue-800">Environment-driven configuration</p>
          <p className="text-sm text-blue-700 mt-0.5">
            Most settings are sourced from the <code className="bg-blue-100 px-1 rounded text-xs">.env</code> file or environment variables.
            Restart the backend service after changing environment variables. Social provider credentials
            can be updated live from the <a href="/admin/providers" className="underline">Social Providers</a> page.
          </p>
        </div>
      </div>

      {/* Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <nav className="lg:col-span-1">
          <div className="space-y-1">
            {SETTINGS.map(g => {
              const Icon = g.icon;
              return (
                <button
                  key={g.id}
                  onClick={() => setActive(g.id)}
                  className={clsx(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-left transition-colors',
                    active === g.id
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-50',
                  )}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="flex-1">{g.label}</span>
                  <ChevronRight className={clsx('w-3.5 h-3.5 shrink-0', active === g.id ? 'text-primary-500' : 'text-gray-300')} />
                </button>
              );
            })}
          </div>
        </nav>

        {/* Content */}
        <div className="lg:col-span-3">
          <SettingsGroup group={currentGroup} />
        </div>
      </div>
    </div>
  );
}

function SettingsGroup({ group }: { group: SettingGroup }) {
  const Icon = group.icon;

  return (
    <div className="card space-y-6">
      {/* Section header */}
      <div className="flex items-start gap-3 pb-4 border-b border-gray-100">
        <div className="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h2 className="font-semibold text-gray-900">{group.label}</h2>
          <p className="text-sm text-gray-500 mt-0.5">{group.description}</p>
        </div>
      </div>

      {/* Fields */}
      <div className="space-y-6">
        {group.fields.map(f => (
          <SettingRow key={f.key} field={f} />
        ))}
      </div>

      {/* Read-only notice */}
      <div className="rounded-xl bg-gray-50 border border-gray-100 px-4 py-3 flex items-center gap-2.5">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
        <p className="text-xs text-gray-600">
          These values are displayed from your environment configuration. To change them, update your
          <code className="bg-gray-200 px-1 rounded mx-0.5">.env</code> file and restart the backend.
        </p>
      </div>
    </div>
  );
}

function SettingRow({ field }: { field: SettingField }) {
  const placeholder = field.placeholder || '';

  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-start">
      <div className="md:col-span-2">
        <p className="text-sm font-medium text-gray-900">{field.label}</p>
        <p className="text-xs font-mono text-gray-400 mt-0.5">{field.key}</p>
        {field.description && (
          <p className="text-xs text-gray-500 mt-1">{field.description}</p>
        )}
      </div>
      <div className="md:col-span-3">
        {field.type === 'boolean' ? (
          <div className="flex items-center gap-2">
            <div className="w-10 h-5 bg-gray-200 rounded-full relative">
              <div className="w-4 h-4 bg-white rounded-full absolute left-0.5 top-0.5 shadow" />
            </div>
            <span className="text-sm text-gray-500">Set via environment variable</span>
          </div>
        ) : field.type === 'textarea' ? (
          <textarea
            className="input resize-none h-24 text-sm text-gray-400 font-mono"
            disabled
            placeholder={placeholder}
          />
        ) : field.type === 'select' ? (
          <div className="relative">
            <select disabled className="input text-sm text-gray-400 opacity-70">
              <option>{placeholder}</option>
              {field.options?.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <input
              type={field.type === 'number' ? 'number' : 'text'}
              className="input text-sm text-gray-400"
              disabled
              placeholder={placeholder}
            />
            {field.unit && (
              <span className="text-xs text-gray-400 shrink-0">{field.unit}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
