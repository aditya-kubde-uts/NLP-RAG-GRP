import type { ReactNode } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "@/context/use-auth";
import { ApiError, apiJson } from "@/lib/api";
import type {
  AdminCredentials,
  BusinessCreateResponse,
} from "@/types/super-admin";

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

  // Business admin provisioning
  const [assignAdmin, setAssignAdmin] = useState(true);
  const [adminEmail, setAdminEmail] = useState("");
  const [adminFullName, setAdminFullName] = useState("");
  const [adminPassword, setAdminPassword] = useState("");

  const [pending, setPending] = useState(false);
  const [createdSlug, setCreatedSlug] = useState<string | null>(null);
  const [createdCreds, setCreatedCreds] = useState<AdminCredentials | null>(null);

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
      const body: Record<string, unknown> = {
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
      };
      if (assignAdmin && adminEmail.trim()) {
        body.admin_email = adminEmail.trim().toLowerCase();
        if (adminFullName.trim()) body.admin_full_name = adminFullName.trim();
        if (adminPassword) body.admin_password = adminPassword;
      }
      const res = await apiJson<BusinessCreateResponse>("/api/super-admin/businesses", {
        method: "POST",
        headers: authHeaders(token),
        json: body,
      });
      toast.success("Business created.");
      setCreatedSlug(res.slug);
      if (res.admin) {
        setCreatedCreds(res.admin);
      } else {
        navigate("/dashboard", { replace: true });
      }
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Create failed.");
    } finally {
      setPending(false);
    }
  }

  if (createdCreds && createdSlug) {
    return (
      <CredentialsReveal
        slug={createdSlug}
        creds={createdCreds}
        onDone={() => navigate("/dashboard", { replace: true })}
      />
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8">
        <Link to="/dashboard" className="text-sm text-indigo-300 hover:underline">
          ← Back to dashboard
        </Link>
        <h1 className="mt-4 text-2xl font-semibold text-white">Create business</h1>
        <p className="mt-1 text-sm text-white/50">
          A business is an isolated tenant: knowledge base, chat, admins, and settings.
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

        <div className="rounded-lg border border-indigo-400/30 bg-indigo-500/5 p-4">
          <label className="flex items-center gap-2 text-sm font-medium text-white">
            <input
              type="checkbox"
              checked={assignAdmin}
              onChange={(ev) => setAssignAdmin(ev.target.checked)}
            />
            Assign a dedicated Business Admin
          </label>
          <p className="mt-1 text-xs text-white/55">
            The assigned user will be the <em>only</em> admin for this business and receive
            their own login. Leave blank to keep yourself (super admin) as the sole admin.
          </p>

          {assignAdmin ? (
            <div className="mt-4 space-y-4">
              <Field label="Admin email" required>
                <input
                  type="email"
                  value={adminEmail}
                  onChange={(ev) => setAdminEmail(ev.target.value)}
                  required={assignAdmin}
                  placeholder="owner@company.com"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
                />
              </Field>
              <Field label="Admin full name">
                <input
                  value={adminFullName}
                  onChange={(ev) => setAdminFullName(ev.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
                />
              </Field>
              <Field label="Initial password (optional — generated if blank)">
                <input
                  type="text"
                  autoComplete="off"
                  value={adminPassword}
                  onChange={(ev) => setAdminPassword(ev.target.value)}
                  minLength={adminPassword ? 8 : undefined}
                  placeholder="min. 8 chars"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm text-white outline-none focus:border-indigo-500"
                />
              </Field>
              <p className="text-xs text-white/45">
                Email is auto-confirmed — the admin can sign in immediately with the shown
                password. If the email already has an account, it will just be linked to this
                business.
              </p>
            </div>
          ) : null}
        </div>

        <div className="border-t border-white/10 pt-6">
          <h2 className="text-sm font-semibold text-white">Chat settings</h2>
          <p className="mt-1 text-xs text-white/45">Defaults — can be changed by the business admin later.</p>

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

function CredentialsReveal({
  slug,
  creds,
  onDone,
}: {
  slug: string;
  creds: AdminCredentials;
  onDone: () => void;
}) {
  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Copy failed — please copy manually.");
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-6 shadow-xl">
        <h1 className="text-xl font-semibold text-white">Business created</h1>
        <p className="mt-1 text-sm text-white/60">
          Workspace: <span className="font-mono text-indigo-300">/b/{slug}/admin</span>
        </p>

        {creds.was_created ? (
          <div className="mt-6 rounded-lg border border-white/10 bg-black/30 p-4">
            <p className="text-sm font-medium text-white">
              One-time admin credentials
            </p>
            <p className="mt-1 text-xs text-white/50">
              Share these with the business owner. They will not be shown again.
            </p>
            <dl className="mt-4 grid gap-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <dt className="text-xs uppercase text-white/40">Email</dt>
                  <dd className="mt-1 font-mono text-white">{creds.email}</dd>
                </div>
                <button
                  type="button"
                  onClick={() => void copy(creds.email)}
                  className="rounded-md border border-white/15 px-3 py-1 text-xs hover:bg-white/10"
                >
                  Copy
                </button>
              </div>
              {creds.password ? (
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <dt className="text-xs uppercase text-white/40">Password</dt>
                    <dd className="mt-1 font-mono text-white">{creds.password}</dd>
                  </div>
                  <button
                    type="button"
                    onClick={() => void copy(creds.password ?? "")}
                    className="rounded-md border border-white/15 px-3 py-1 text-xs hover:bg-white/10"
                  >
                    Copy
                  </button>
                </div>
              ) : null}
            </dl>
          </div>
        ) : (
          <p className="mt-4 text-sm text-white/70">
            Existing user <span className="font-mono text-white">{creds.email}</span> was attached
            as the business admin. They can sign in with their existing password.
          </p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onDone}
            className="rounded-lg bg-indigo-500 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-400"
          >
            Done
          </button>
        </div>
      </div>
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
