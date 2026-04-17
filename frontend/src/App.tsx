import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Phase 0 landing page. Proves Tailwind v4 + design tokens + path alias work.
 * Replaced in Phase 3 with React Router + real auth/dashboard pages.
 */
export default function App() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">(
    "checking",
  );

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
            Multi-tenant RAG platform — Phase 0 scaffold ready.
          </p>
        </header>

        <section className="grid gap-4 sm:grid-cols-2">
          <Card title="Backend" value="FastAPI + uv" />
          <Card title="Frontend" value="React + Vite + TS" />
          <Card title="UI" value="Tailwind v4 + shadcn/ui" />
          <Card title="DB" value="Supabase + pgvector" />
        </section>

        <footer className="pt-4 text-sm text-muted-foreground">
          See <code className="rounded bg-card px-1.5 py-0.5">PLAN.md</code> for
          the full roadmap.
        </footer>
      </div>
    </main>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 transition-colors hover:bg-card/70">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <p className="mt-1 text-base font-medium">{value}</p>
    </div>
  );
}
