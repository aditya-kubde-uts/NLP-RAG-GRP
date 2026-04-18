import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "@/context/use-auth";
import { useBusinessBySlug } from "@/hooks/useBusinessBySlug";
import { ApiError, apiJson } from "@/lib/api";
import type { BusinessDetail, BusinessSettings } from "@/types/super-admin";

const INDUSTRIES = [
  "Education",
  "Restaurant",
  "Healthcare",
  "Retail",
  "Legal",
  "Technology",
  "Other",
] as const;

const DEFAULT_SETTINGS: BusinessSettings = {
  user_login_required: false,
  custom_system_prompt: "",
  welcome_message: "Hello! How can I help you today?",
  primary_color: "#6366f1",
  max_chunks_per_query: 8,
  confidence_threshold: 0.15,
};

function authHeaders(token: string | undefined): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export default function BusinessAdminDashboard() {
  const { slug } = useParams<{ slug: string }>();
  const { session, profile, signOut } = useAuth();
  const token = session?.access_token;

  const { business: detail, loading, error, reload } = useBusinessBySlug(slug);
  const businessId = detail?.id ?? null;

  const [saving, setSaving] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [industry, setIndustry] = useState<(typeof INDUSTRIES)[number]>("Other");
  const [settings, setSettings] = useState<BusinessSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    if (!detail) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate form from fetched detail
    setName(detail.name);
    setDescription(detail.description ?? "");
    const ind = (detail.industry as (typeof INDUSTRIES)[number]) || "Other";
    setIndustry(INDUSTRIES.includes(ind) ? ind : "Other");
    setSettings({ ...DEFAULT_SETTINGS, ...(detail.settings as Partial<BusinessSettings>) });
  }, [detail]);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !businessId) return;
    setSaving(true);
    try {
      await apiJson<BusinessDetail>(`/api/business/${businessId}`, {
        method: "PUT",
        headers: authHeaders(token),
        json: {
          name: name.trim(),
          description: description.trim() || null,
          industry,
          settings,
        },
      });
      toast.success("Settings saved.");
      await reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  const chatUrl = detail ? `/b/${detail.slug}` : "#";

  return (
    <div
      className="dark min-h-screen bg-[#0f0f23] text-foreground"
      style={{ "--brand": settings.primary_color } as React.CSSProperties}
    >
      <header className="border-b border-white/10 bg-[#12122a]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-white/40">Business admin</p>
            <h1 className="text-lg font-semibold text-white">
              {detail?.name ||
                profile?.businesses.find((b) => b.slug === slug)?.name ||
                "Workspace"}
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <Link to={chatUrl} className="text-indigo-300 hover:underline">
              Chat portal ↗
            </Link>
            {profile?.is_super_admin ? (
              <Link to="/dashboard" className="text-white/70 hover:underline">
                Super admin
              </Link>
            ) : null}
            <button
              type="button"
              onClick={() => void signOut()}
              className="text-white/60 hover:text-white hover:underline"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-8 px-6 py-10">
        {!slug ? (
          <EmptyState title="Missing workspace" body="No slug in URL." />
        ) : loading && !detail ? (
          <div className="h-64 animate-pulse rounded-xl bg-white/5" />
        ) : !detail ? (
          <EmptyState
            title="Business not found"
            body={
              error ??
              "We couldn't load this business. It may be inactive, renamed, or outside your access."
            }
          />
        ) : (
          <>
            <section className="rounded-xl border border-white/10 bg-[#12122a] p-6">
              <h2 className="text-sm font-medium text-white/60">Overview</h2>
              <dl className="mt-4 grid gap-4 sm:grid-cols-3">
                <Stat label="Slug" value={<span className="font-mono">{detail?.slug}</span>} />
                <Stat label="Status" value={detail?.is_active ? "Active" : "Inactive"} />
                <Stat label="Industry" value={detail?.industry ?? "—"} />
              </dl>
            </section>

            <form
              onSubmit={onSave}
              className="space-y-6 rounded-xl border border-white/10 bg-[#12122a] p-6 shadow-xl"
            >
              <h2 className="text-sm font-medium text-white/60">Business profile</h2>

              <Field label="Business name" required>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[var(--brand)]"
                />
              </Field>

              <Field label="Description">
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[var(--brand)]"
                />
              </Field>

              <Field label="Industry">
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value as (typeof INDUSTRIES)[number])}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[var(--brand)]"
                >
                  {INDUSTRIES.map((i) => (
                    <option key={i} value={i}>
                      {i}
                    </option>
                  ))}
                </select>
              </Field>

              <div className="border-t border-white/10 pt-6">
                <h3 className="text-sm font-medium text-white/60">Chat settings</h3>

                <label className="mt-4 flex items-center gap-2 text-sm text-white/85">
                  <input
                    type="checkbox"
                    checked={settings.user_login_required}
                    onChange={(e) =>
                      setSettings((s) => ({ ...s, user_login_required: e.target.checked }))
                    }
                  />
                  Require end-user login for chat
                </label>

                <Field label="Welcome message" className="mt-4">
                  <textarea
                    value={settings.welcome_message}
                    onChange={(e) =>
                      setSettings((s) => ({ ...s, welcome_message: e.target.value }))
                    }
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[var(--brand)]"
                  />
                </Field>

                <Field label="Custom system prompt" className="mt-4">
                  <textarea
                    value={settings.custom_system_prompt}
                    onChange={(e) =>
                      setSettings((s) => ({ ...s, custom_system_prompt: e.target.value }))
                    }
                    rows={3}
                    placeholder="Optional — prepended to the RAG prompt (tone, personality, constraints)."
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[var(--brand)]"
                  />
                </Field>

                <Field label="Primary brand color" className="mt-4">
                  <div className="mt-1 flex items-center gap-3">
                    <input
                      type="color"
                      value={settings.primary_color}
                      onChange={(e) =>
                        setSettings((s) => ({ ...s, primary_color: e.target.value }))
                      }
                      className="h-10 w-14 cursor-pointer rounded border border-white/10 bg-transparent"
                    />
                    <input
                      value={settings.primary_color}
                      onChange={(e) =>
                        setSettings((s) => ({ ...s, primary_color: e.target.value }))
                      }
                      className="flex-1 rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm text-white outline-none focus:border-[var(--brand)]"
                    />
                  </div>
                </Field>

                <Field label="Max chunks per query" className="mt-4">
                  <input
                    type="number"
                    min={1}
                    max={32}
                    value={settings.max_chunks_per_query}
                    onChange={(e) =>
                      setSettings((s) => ({
                        ...s,
                        max_chunks_per_query: Number(e.target.value),
                      }))
                    }
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-[var(--brand)]"
                  />
                </Field>

                <Field
                  label={`Confidence threshold (${settings.confidence_threshold.toFixed(2)})`}
                  className="mt-4"
                >
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={settings.confidence_threshold}
                    onChange={(e) =>
                      setSettings((s) => ({
                        ...s,
                        confidence_threshold: Number(e.target.value),
                      }))
                    }
                    className="mt-2 w-full accent-[var(--brand)]"
                  />
                </Field>
              </div>

              <div className="flex justify-end gap-3 border-t border-white/10 pt-6">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-lg bg-[var(--brand)] px-5 py-2 text-sm font-medium text-white shadow-lg shadow-indigo-500/20 transition hover:opacity-90 disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save changes"}
                </button>
              </div>
            </form>

            <section className="rounded-xl border border-dashed border-white/15 bg-[#12122a]/60 p-6">
              <h2 className="text-sm font-medium text-white/60">Coming next</h2>
              <p className="mt-2 text-sm text-white/55">
                Knowledge base uploads, alerts, analytics, and chat history will land in upcoming
                phases.
              </p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/15 bg-[#12122a] p-10 text-center">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <p className="mt-2 text-sm text-white/55">{body}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-white/40">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-white">{value}</dd>
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
