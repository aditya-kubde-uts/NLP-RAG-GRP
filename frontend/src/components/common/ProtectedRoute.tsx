import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/context/AuthContext";

type Props = {
  children: React.ReactNode;
  /** When true, only users with ``is_super_admin`` may access the route. */
  requireSuperAdmin?: boolean;
};

export function ProtectedRoute({ children, requireSuperAdmin = false }: Props) {
  const { session, profile, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="dark flex min-h-screen items-center justify-center bg-[#0f0f23] text-muted-foreground">
        <p className="text-sm">Loading…</p>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (requireSuperAdmin) {
    if (!profile) {
      return (
        <div className="dark flex min-h-screen flex-col items-center justify-center gap-2 bg-[#0f0f23] px-6 text-center text-foreground">
          <h1 className="text-xl font-semibold">Access denied</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            We could not verify your profile. Try signing in again, or contact a platform
            administrator.
          </p>
        </div>
      );
    }
    if (!profile.is_super_admin) {
      return (
        <div className="dark flex min-h-screen flex-col items-center justify-center gap-2 bg-[#0f0f23] px-6 text-center text-foreground">
          <h1 className="text-xl font-semibold">Access denied</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            This area is restricted to platform super administrators.
          </p>
        </div>
      );
    }
  }

  return <>{children}</>;
}
