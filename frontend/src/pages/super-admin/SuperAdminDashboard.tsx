import { Link } from "react-router-dom";

import { useAuth } from "@/context/use-auth";

export default function SuperAdminDashboard() {
  const { profile, signOut } = useAuth();

  return (
    <div className="dark min-h-screen bg-background px-6 py-12 text-foreground">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Super admin</h1>
            <p className="text-sm text-muted-foreground">
              Signed in as {profile?.email ?? "—"}
            </p>
          </div>
          <div className="flex gap-3 text-sm">
            <Link to="/" className="text-primary hover:underline">
              Home
            </Link>
            <button
              type="button"
              onClick={() => void signOut()}
              className="text-muted-foreground hover:text-foreground hover:underline"
            >
              Sign out
            </button>
          </div>
        </div>
        <p className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
          Business management and platform stats will land in Phase 4.
        </p>
      </div>
    </div>
  );
}
