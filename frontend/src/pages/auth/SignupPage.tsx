import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/context/use-auth";

export default function SignupPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setPending(true);
    try {
      const { message, user } = await signUp(email, password, fullName);
      if (message) {
        setInfo(message);
        return;
      }
      if (user?.is_super_admin) {
        navigate("/dashboard", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Sign up failed.";
      setError(msg);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="dark flex min-h-screen items-center justify-center bg-[#0f0f23] px-4 py-12 text-foreground">
      <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#1a1a2e]/90 p-8 shadow-xl backdrop-blur-md">
        <h1 className="text-2xl font-semibold tracking-tight text-white">Create account</h1>
        <p className="mt-1 text-sm text-white/60">Start with email and a secure password.</p>

        <form className="mt-8 space-y-5" onSubmit={onSubmit}>
          <div className="space-y-2">
            <label htmlFor="fullName" className="text-xs font-medium uppercase tracking-wide text-white/50">
              Full name
            </label>
            <input
              id="fullName"
              name="fullName"
              type="text"
              autoComplete="name"
              required
              value={fullName}
              onChange={(ev) => setFullName(ev.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition-[border-color,box-shadow] focus:border-[#6366f1] focus:ring-2 focus:ring-[#6366f1]/30"
            />
          </div>
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
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(ev) => setPassword(ev.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2.5 text-sm text-white outline-none transition-[border-color,box-shadow] focus:border-[#6366f1] focus:ring-2 focus:ring-[#6366f1]/30"
            />
            <p className="text-xs text-white/40">At least 8 characters.</p>
          </div>

          {error ? <p className="text-sm text-red-400">{error}</p> : null}
          {info ? <p className="text-sm text-[#a5b4fc]">{info}</p> : null}

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
                Creating…
              </span>
            ) : (
              "Create account"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-white/55">
          Already registered?{" "}
          <Link to="/login" className="font-medium text-[#6366f1] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
