import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { storage } from '@/utils/storage';
import { useAuthStore } from '@/store/authStore';

export default function SocialCallback() {
  const navigate = useNavigate();
  const fetchUser = useAuthStore((s) => s.fetchUser);

  useEffect(() => {
    // Tokens are in the URL fragment (#access_token=...&refresh_token=...)
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (accessToken && refreshToken) {
      storage.setAccessToken(accessToken);
      storage.setRefreshToken(refreshToken);
      // Clean the fragment from the URL
      window.history.replaceState({}, document.title, window.location.pathname);
      fetchUser().then(() => navigate('/dashboard', { replace: true }));
    } else {
      navigate('/login?error=social_login_failed', { replace: true });
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-500">Completing sign in…</p>
    </div>
  );
}
