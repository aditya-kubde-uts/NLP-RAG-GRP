import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const { session, profile, signOut } = useAuth();
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  const statusColor =
    apiStatus === "online"
      ? "bg-[color:hsl(var(--success))]"
      : apiStatus === "offline"
        ? "bg-destructive"
        : "bg-muted-foreground";

  return (
    <main className="dark min-h-screen bg-background text-foreground">
      <div className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-20">
        <header className="space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-card/50 px-3 py-1 text-xs text-muted-foreground backdrop-blur-sm">
            <span className={cn("h-1.5 w-1.5 rounded-full", statusColor)} />
            <span>
              Backend API: <span className="font-medium">{apiStatus}</span>
            </span>
          </div>
          <h1 className="text-4xl font-semibold tracking-tight">RAG Factory</h1>
          <p className="text-muted-foreground">
            Multi-tenant RAG platform — Phase 3 auth routes are live.
          </p>
          <nav className="flex flex-wrap gap-3 pt-2 text-sm">
            {session ? (
              <>
                {profile?.is_super_admin ? (
                  <Link to="/dashboard" className="text-primary hover:underline">
                    Super admin dashboard
                  </Link>
                ) : null}
                <button
                  type="button"
                  onClick={() => void signOut()}
                  className="text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-primary hover:underline">
                  Sign in
                </Link>
                <Link to="/signup" className="text-muted-foreground hover:text-foreground hover:underline">
                  Sign up
                </Link>
              </>
            )}
          </nav>
        </header>

        <section className="grid gap-4 sm:grid-cols-2">
          <Card title="Backend" value="FastAPI + Supabase Auth" />
          <Card title="Frontend" value="React + Vite + TS" />
          <Card title="Auth" value="/api/auth/* + AuthContext" />
          <Card title="DB" value="Supabase + pgvector" />
        </section>

        {session && profile ? (
          <p className="text-sm text-muted-foreground">
            Signed in as <span className="font-medium text-foreground">{profile.email}</span>
          </p>
        ) : null}
      </div>
    </main>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 transition-colors hover:bg-card/70">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="mt-1 text-base font-medium">{value}</p>
    </div>
  );
}
