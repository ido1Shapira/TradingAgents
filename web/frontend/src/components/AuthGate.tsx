import { useEffect, type ReactNode } from 'react';
import { useAuthStore } from '../stores/authStore';
import { Spinner } from '../ui';
import { LoginPage } from './LoginPage';

interface AuthGateProps {
  children: ReactNode;
}

export function AuthGate({ children }: AuthGateProps) {
  const { user, loading, check } = useAuthStore();

  useEffect(() => {
    check();
  }, [check]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-market">
        <Spinner size="lg" />
        <p className="text-xs text-slate-500 font-medium">Connecting…</p>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return <>{children}</>;
}
