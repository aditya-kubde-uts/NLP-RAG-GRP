import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/context/use-auth";

export default function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const userProfile = await signIn(email, password);
      if (userProfile?.is_super_admin) {
        navigate("/dashboard", { replace: true });
      } else if (userProfile && userProfile.businesses.length > 0) {
        // Non-super-admins land directly in the workspace they manage.
        const target = `/b/${userProfile.businesses[0].slug}/admin`;
        navigate(target, { replace: true });
      } else {
        navigate(from === "/login" ? "/" : from, { replace: true });
      }
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Sign in failed.";
      setError(msg);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="dark flex min-h-screen items-center justify-center bg-[#0f0f23] px-4 py-12 text-foreground">
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#1a1a2e]/90 p-8 shadow-xl backdrop-blur-md transition-shadow">
        <h1 className="text-2xl font-semibold tracking-tight text-white">Sign in</h1>
        <p className="mt-1 text-sm text-white/60">RAG Factory — use your workspace email.</p>

        <form className="mt-8 space-y-5" onSubmit={onSubmit}>
          <div className="space-y-2">
            <label htmlFor="email" className="text-xs font-medium uppercase tracking-wide text-white/50">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition-[border-color,box-shadow] focus:border-[#6366f1] focus:ring-2 focus:ring-[#6366f1]/30"
            />
          </div>
          <div className="space-y-2">
            <label
              htmlFor="password"
              className="text-xs font-medium uppercase tracking-wide text-white/50"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition-[border-color,box-shadow] focus:border-[#6366f1] focus:ring-2 focus:ring-[#6366f1]/30"
            />
          </div>

          {error ? <p className="text-sm text-red-400">{error}</p> : null}

          <button
            type="submit"
            disabled={pending}
            className="flex w-full items-center justify-center rounded-lg bg-[#6366f1] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#5558e3] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {pending ? (
              <span className="inline-flex items-center gap-2">
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                  aria-hidden
                />
                Signing in…
              </span>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-white/55">
          No account?{" "}
          <Link to="/signup" className="font-medium text-[#6366f1] hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
