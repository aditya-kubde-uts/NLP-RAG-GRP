import { Building2, Database, MessageSquare, Pencil, Trash2, Users } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "@/context/use-auth";
import { ApiError, apiJson } from "@/lib/api";
import type { BusinessRow, PlatformStats } from "@/types/super-admin";

const INDUSTRIES = [
  "Education",
  "Restaurant",
  "Healthcare",
  "Retail",
  "Legal",
  "Technology",
  "Other",
] as const;

function authHeaders(token: string | undefined): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export default function DashboardPage() {
  const { session } = useAuth();
  const token = session?.access_token;

  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [businesses, setBusinesses] = useState<BusinessRow[]>([]);
  const [editing, setEditing] = useState<BusinessRow | null>(null);
  const [editSaving, setEditSaving] = useState(false);

  const totalChunks = useMemo(
    () => businesses.reduce((sum, b) => sum + b.chunk_count, 0),
    [businesses],
  );

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const h = authHeaders(token);
      const [s, b] = await Promise.all([
        apiJson<PlatformStats>("/api/super-admin/stats", { headers: h }),
        apiJson<BusinessRow[]>("/api/super-admin/businesses", { headers: h }),
      ]);
      setStats(s);
      setBusinesses(b);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to load dashboard.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    // Mount / token change: load dashboard data (sets state in async callbacks).
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional client fetch
    void load();
  }, [load]);

  async function onDelete(b: BusinessRow) {
    if (!token) return;
    const ok = window.confirm(
      `Deactivate “${b.name}”? The business will be hidden (soft delete) but data is retained.`,
    );
    if (!ok) return;
    try {
      await apiJson(`/api/super-admin/businesses/${b.id}`, {
        method: "DELETE",
        headers: authHeaders(token),
      });
      toast.success("Business deactivated.");
      void load();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Delete failed.");
    }
  }

  async function onSaveEdit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editing || !token) return;
    const fd = new FormData(e.currentTarget);
    const name = String(fd.get("name") || "").trim();
    const description = String(fd.get("description") || "") || null;
    const industry = String(fd.get("industry") || "Other");
    const is_active = fd.get("is_active") === "on";
    setEditSaving(true);
    try {
      await apiJson<BusinessRow>(`/api/super-admin/businesses/${editing.id}`, {
        method: "PUT",
        headers: authHeaders(token),
        json: { name, description, industry, is_active },
      });
      toast.success("Business updated.");
      setEditing(null);
      void load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Update failed.");
    } finally {
      setEditSaving(false);
    }
  }

  return (
    <div className="space-y-10">
      <section>
        <h2 className="mb-4 text-sm font-medium text-white/60">Overview</h2>
        {loading && !stats ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-28 animate-pulse rounded-xl bg-white/5 ring-1 ring-indigo-500/20"
              />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={<Building2 className="h-5 w-5" />}
              label="Businesses"
              value={stats?.total_businesses ?? 0}
            />
            <StatCard
              icon={<Database className="h-5 w-5" />}
              label="Knowledge chunks"
              value={totalChunks}
              hint="Sum across listed businesses"
            />
            <StatCard
              icon={<MessageSquare className="h-5 w-5" />}
              label="Chat messages"
              value={stats?.total_chat_messages ?? 0}
            />
            <StatCard
              icon={<Users className="h-5 w-5" />}
              label="Users"
              value={stats?.total_users ?? 0}
            />
          </div>
        )}
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-sm font-medium text-white/60">Businesses</h2>
            <p className="text-lg font-semibold text-white">All tenants</p>
          </div>
          <Link
            to="/dashboard/businesses/new"
            className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-indigo-500/25 transition hover:bg-indigo-400"
          >
            Create business
          </Link>
        </div>

        {loading && businesses.length === 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 animate-pulse rounded-xl bg-white/5" />
            ))}
          </div>
        ) : businesses.length === 0 ? (
          <div className="rounded-xl border border-dashed border-white/15 bg-[#1a1a3e]/50 px-8 py-16 text-center">
            <Building2 className="mx-auto mb-4 h-12 w-12 text-indigo-400/60" />
            <p className="text-lg font-medium text-white">Create your first business</p>
            <p className="mt-1 text-sm text-white/50">
              Businesses isolate knowledge, chats, and admins per customer.
            </p>
            <Link
              to="/dashboard/businesses/new"
              className="mt-6 inline-flex rounded-lg bg-indigo-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-400"
            >
              New business
            </Link>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {businesses.map((b) => (
              <article
                key={b.id}
                className="group rounded-xl border border-white/10 bg-[#1a1a3e] p-5 shadow-lg transition hover:-translate-y-0.5 hover:border-indigo-500/40 hover:shadow-indigo-500/10"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-white">{b.name}</h3>
                    <span className="mt-1 inline-block rounded-full bg-indigo-500/15 px-2 py-0.5 text-xs text-indigo-200">
                      {b.industry}
                    </span>
                  </div>
                  <span
                    className={
                      b.is_active
                        ? "rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300"
                        : "rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/50"
                    }
                  >
                    {b.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <dl className="mt-4 grid grid-cols-3 gap-2 text-center text-xs text-white/50">
                  <div>
                    <dt className="font-normal">Chunks</dt>
                    <dd className="text-sm font-semibold text-white">{b.chunk_count}</dd>
                  </div>
                  <div>
                    <dt className="font-normal">Chats</dt>
                    <dd className="text-sm font-semibold text-white">{b.chat_count}</dd>
                  </div>
                  <div>
                    <dt className="font-normal">Admins</dt>
                    <dd className="text-sm font-semibold text-white">{b.admin_count}</dd>
                  </div>
                </dl>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Link
                    to={`/b/${b.slug}/admin`}
                    className="rounded-md border border-white/15 px-3 py-1.5 text-xs font-medium text-white/80 transition hover:border-indigo-400/50 hover:text-white"
                  >
                    Manage
                  </Link>
                  <button
                    type="button"
                    onClick={() => setEditing(b)}
                    className="inline-flex items-center gap-1 rounded-md border border-white/15 px-3 py-1.5 text-xs font-medium text-white/80 transition hover:border-indigo-400/50 hover:text-white"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => void onDelete(b)}
                    disabled={!b.is_active}
                    className="inline-flex items-center gap-1 rounded-md border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-300 transition hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Deactivate
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {editing ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-white/10 bg-[#12122a] p-6 shadow-2xl">
            <h3 className="text-lg font-semibold text-white">Edit business</h3>
            <form className="mt-4 space-y-4" onSubmit={onSaveEdit}>
              <div>
                <label className="text-xs text-white/50">Name</label>
                <input
                  name="name"
                  required
                  defaultValue={editing.name}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs text-white/50">Description</label>
                <textarea
                  name="description"
                  rows={3}
                  defaultValue={editing.description ?? ""}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs text-white/50">Industry</label>
                <select
                  name="industry"
                  defaultValue={editing.industry}
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none focus:border-indigo-500"
                >
                  {INDUSTRIES.map((i) => (
                    <option key={i} value={i}>
                      {i}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-white/80">
                <input type="checkbox" name="is_active" defaultChecked={editing.is_active} />
                Active
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditing(null)}
                  className="rounded-lg px-4 py-2 text-sm text-white/70 hover:bg-white/5"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSaving}
                  className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 disabled:opacity-50"
                >
                  {editSaving ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: number | string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl bg-gradient-to-br from-indigo-500/20 via-purple-500/10 to-transparent p-[1px] shadow-lg shadow-indigo-500/5">
      <div className="h-full rounded-[11px] bg-[#1a1a3e] p-4">
        <div className="flex items-center gap-2 text-indigo-300">{icon}</div>
        <p className="mt-3 text-xs uppercase tracking-wide text-white/40">{label}</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums text-white">{value}</p>
        {hint ? <p className="mt-1 text-xs text-white/40">{hint}</p> : null}
      </div>
    </div>
  );
}
