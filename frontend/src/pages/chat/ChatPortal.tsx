import { Link, useParams } from "react-router-dom";

export default function ChatPortal() {
  const { slug } = useParams<{ slug: string }>();

  return (
    <div className="dark min-h-screen bg-background px-6 py-12 text-foreground">
      <div className="mx-auto max-w-3xl space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-muted-foreground">Business slug: {slug}</p>
        <p className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
          RAG chat UI will be wired in a later phase. For now this route is public.
        </p>
        <Link to="/" className="text-sm text-primary hover:underline">
          ← Home
        </Link>
      </div>
    </div>
  );
}
