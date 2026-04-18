import { Navigate, useLocation, useParams } from "react-router-dom";

import { useAuth } from "@/context/use-auth";

type Props = {
  children: React.ReactNode;
  /** When true, only users with ``is_super_admin`` may access the route. */
  requireSuperAdmin?: boolean;
  /**
   * When true, the route's ``:slug`` URL parameter must match one of the
   * businesses the current user administers. Super admins bypass this check.
   */
  requireBusinessAdminSlug?: boolean;
};

export function ProtectedRoute({
  children,
  requireSuperAdmin = false,
  requireBusinessAdminSlug = false,
}: Props) {
  const { session, profile, loading } = useAuth();
  const location = useLocation();
  const params = useParams<{ slug?: string }>();

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
      return <AccessDenied reason="profile-missing" />;
    }
    if (!profile.is_super_admin) {
      return <AccessDenied reason="super-admin-only" />;
    }
  }

  if (requireBusinessAdminSlug) {
    if (!profile) {
      return <AccessDenied reason="profile-missing" />;
    }
    const slug = params.slug;
    const isMember = slug
      ? profile.businesses.some((b) => b.slug === slug)
      : false;
    if (!profile.is_super_admin && !isMember) {
      return <AccessDenied reason="not-business-admin" />;
    }
  }

  return <>{children}</>;
}

function AccessDenied({
  reason,
}: {
  reason: "profile-missing" | "super-admin-only" | "not-business-admin";
}) {
  const message =
    reason === "profile-missing"
      ? "We could not verify your profile. Try signing in again, or contact a platform administrator."
      : reason === "super-admin-only"
        ? "This area is restricted to platform super administrators."
        : "You are not an administrator for this business.";
  return (
    <div className="dark flex min-h-screen flex-col items-center justify-center gap-2 bg-[#0f0f23] px-6 text-center text-foreground">
      <h1 className="text-xl font-semibold">Access denied</h1>
      <p className="max-w-md text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
