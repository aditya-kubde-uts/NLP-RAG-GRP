import type { ReactNode } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "@/context/use-auth";
import { ApiError, apiJson } from "@/lib/api";
import type { BusinessRow } from "@/types/super-admin";

const INDUSTRIES = [
  "Education",
  "Restaurant",
  "Healthcare",
  "Retail",
  "Legal",
  "Technology",
  "Other",
] as const;

function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function authHeaders(token: string | undefined): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export default function CreateBusinessPage() {
  const { session } = useAuth();
  const token = session?.access_token;
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugDirty, setSlugDirty] = useState(false);
  const [description, setDescription] = useState("");
  const [industry, setIndustry] = useState<(typeof INDUSTRIES)[number]>("Education");
  const [userLoginRequired, setUserLoginRequired] = useState(false);
  const [welcomeMessage, setWelcomeMessage] = useState("Hello! How can I help you today?");
  const [primaryColor, setPrimaryColor] = useState("#6366f1");
  const [maxChunks, setMaxChunks] = useState(8);
  const [confidence, setConfidence] = useState(0.15);
  const [pending, setPending] = useState(false);

  const autoSlug = slugify(name);
  const effectiveSlug = slugDirty ? slug : autoSlug;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      toast.error("Not signed in.");
      return;
    }
    setPending(true);
    try {
      await apiJson<BusinessRow>("/api/super-admin/businesses", {
        method: "POST",
        headers: authHeaders(token),
        json: {
          name: name.trim(),
          slug: effectiveSlug.trim().toLowerCase(),
          description: description.trim() || null,
          industry,
          settings: {
            user_login_required: userLoginRequired,
            welcome_message: welcomeMessage,
            primary_color: primaryColor,
            max_chunks_per_query: maxChunks,
            confidence_threshold: confidence,
          },
        },
      });
      toast.success("Business created.");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Create failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8">
        <Link to="/dashboard" className="text-sm text-indigo-300 hover:underline">
          ← Back to dashboard
        </Link>
        <h1 className="mt-4 text-2xl font-semibold text-white">Create business</h1>
        <p className="mt-1 text-sm text-white/50">
          A business is an isolated tenant: knowledge base, chat, and admins.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="space-y-6 rounded-xl border border-white/10 bg-[#1a1a3e] p-6 shadow-xl"
      >
        <Field label="Business name" required>
          <input
            value={name}
            onChange={(ev) => setName(ev.target.value)}
            required
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
          />
        </Field>

        <Field label="Slug (URL-safe)" required>
          <input
            value={effectiveSlug}
            onChange={(ev) => {
              setSlugDirty(true);
              setSlug(ev.target.value.toLowerCase());
            }}
            required
            pattern="[a-z0-9-]+"
            title="Lowercase letters, digits, and hyphens only"
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm text-white outline-none focus:border-indigo-500"
          />
        </Field>

        <Field label="Description">
          <textarea
            value={description}
            onChange={(ev) => setDescription(ev.target.value)}
            rows={4}
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
          />
        </Field>

        <Field label="Industry" required>
          <select
            value={industry}
            onChange={(ev) => setIndustry(ev.target.value as (typeof INDUSTRIES)[number])}
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
          >
            {INDUSTRIES.map((i) => (
              <option key={i} value={i}>
                {i}
              </option>
            ))}
          </select>
        </Field>

        <div className="border-t border-white/10 pt-6">
          <h2 className="text-sm font-semibold text-white">Chat settings</h2>
          <p className="mt-1 text-xs text-white/45">Defaults can be changed later.</p>

          <label className="mt-4 flex items-center gap-2 text-sm text-white/85">
            <input
              type="checkbox"
              checked={userLoginRequired}
              onChange={(ev) => setUserLoginRequired(ev.target.checked)}
            />
            Require user login for chat
          </label>

          <Field label="Welcome message" className="mt-4">
            <textarea
              value={welcomeMessage}
              onChange={(ev) => setWelcomeMessage(ev.target.value)}
              rows={2}
              className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
            />
          </Field>

          <Field label="Primary brand color" className="mt-4">
            <div className="mt-1 flex items-center gap-3">
              <input
                type="color"
                value={primaryColor}
                onChange={(ev) => setPrimaryColor(ev.target.value)}
                className="h-10 w-14 cursor-pointer rounded border border-white/10 bg-transparent"
              />
              <input
                value={primaryColor}
                onChange={(ev) => setPrimaryColor(ev.target.value)}
                className="flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm text-white outline-none focus:border-indigo-500"
              />
            </div>
          </Field>

          <Field label="Max chunks per query" className="mt-4">
            <input
              type="number"
              min={1}
              max={32}
              value={maxChunks}
              onChange={(ev) => setMaxChunks(Number(ev.target.value))}
              className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
            />
          </Field>

          <Field label={`Confidence threshold (${confidence.toFixed(2)})`} className="mt-4">
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={confidence}
              onChange={(ev) => setConfidence(Number(ev.target.value))}
              className="mt-2 w-full accent-indigo-500"
            />
          </Field>
        </div>

        <div className="flex justify-end gap-3 border-t border-white/10 pt-6">
          <Link
            to="/dashboard"
            className="rounded-lg px-4 py-2 text-sm text-white/70 hover:bg-white/5"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={pending}
            className="rounded-lg bg-indigo-500 px-5 py-2 text-sm font-medium text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-400 disabled:opacity-50"
          >
            {pending ? "Creating…" : "Create business"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  children,
  required,
  className,
}: {
  label: string;
  children: ReactNode;
  required?: boolean;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="text-xs font-medium text-white/55">
        {label}
        {required ? <span className="text-red-400"> *</span> : null}
      </label>
      {children}
    </div>
  );
}
