import { Link, useParams } from "react-router-dom";

import { useAuth } from "@/context/use-auth";

export default function BusinessAdminDashboard() {
  const { slug } = useParams<{ slug: string }>();
  const { signOut } = useAuth();

  return (
    <div className="dark min-h-screen bg-background px-6 py-12 text-foreground">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Business admin</h1>
            <p className="text-sm text-muted-foreground">Workspace: {slug}</p>
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
          Knowledge base and analytics will be added in later phases.
        </p>
      </div>
    </div>
  );
}
