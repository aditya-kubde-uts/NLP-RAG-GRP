import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "@/context/use-auth";
import { useBusinessBySlug } from "@/hooks/useBusinessBySlug";
import { ApiError, apiJson } from "@/lib/api";

type KnowledgeStats = {
  total_chunks: number;
  by_source_type: Record<string, number>;
};

type SourceRow = {
  source_url: string | null;
  source_type: string | null;
  title: string | null;
  chunk_count: number;
  latest_chunk_at: string | null;
};

type ChunkRow = {
  id: string;
  title: string | null;
  source_url: string | null;
  source_type: string | null;
  metadata: Record<string, unknown>;
  content: string;
  llm_summary: string | null;
  created_at: string;
};

type ChunkListResponse = {
  items: ChunkRow[];
  page: number;
  page_size: number;
  total: number;
};

type IngestTask = {
  task_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  stage: string | null;
  message: string | null;
  error: string | null;
  result: { chunks_created?: number; chunks_processed?: number } | null;
};

const SOURCES_PER_PAGE = 6;
const CHUNKS_PER_PAGE = 10;

export default function KnowledgeBasePage() {
  const { slug } = useParams<{ slug: string }>();
  const { session } = useAuth();
  const token = session?.access_token;
  const { business, loading, error } = useBusinessBySlug(slug);

  const [uploading, setUploading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [query, setQuery] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [sourcePage, setSourcePage] = useState(1);
  const [chunkPage, setChunkPage] = useState(1);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [chunks, setChunks] = useState<ChunkListResponse | null>(null);
  const [task, setTask] = useState<IngestTask | null>(null);

  const [editingChunkId, setEditingChunkId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editContent, setEditContent] = useState("");
  const [findText, setFindText] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [previewMode, setPreviewMode] = useState(false);
  const [savingChunkId, setSavingChunkId] = useState<string | null>(null);
  const [deletingChunkId, setDeletingChunkId] = useState<string | null>(null);
  const [deletingSourceUrl, setDeletingSourceUrl] = useState<string | null>(null);
  const [selectedSourceUrls, setSelectedSourceUrls] = useState<Set<string>>(new Set());
  const [deletingSelectedSources, setDeletingSelectedSources] = useState(false);

  const sourceTypeOptions = useMemo(() => {
    const set = new Set<string>();
    for (const src of sources) {
      if (src.source_type) set.add(src.source_type);
    }
    return Array.from(set).sort();
  }, [sources]);

  const totalSourcePages = Math.max(1, Math.ceil(sources.length / SOURCES_PER_PAGE));
  const displaySourcePage = Math.min(sourcePage, totalSourcePages);
  const totalChunkPages = Math.max(1, Math.ceil((chunks?.total ?? 0) / CHUNKS_PER_PAGE));
  const displayChunkPage = Math.min(chunkPage, totalChunkPages);
  const pagedSources = useMemo(() => {
    const start = (displaySourcePage - 1) * SOURCES_PER_PAGE;
    return sources.slice(start, start + SOURCES_PER_PAGE);
  }, [displaySourcePage, sources]);

  useEffect(() => {
    if (!business) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset local pagination on workspace change
    setSourcePage(1);
    setChunkPage(1);
    void refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when business identity changes
  }, [business?.id]);

  useEffect(() => {
    if (!business) return;
    void refreshData();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional refetch when chunk page changes
  }, [chunkPage]);

  async function apiAuth<T>(path: string, init?: RequestInit & { json?: unknown }) {
    if (!token) throw new ApiError(401, "unauthorized", "Please sign in again.");
    return apiJson<T>(path, {
      ...init,
      headers: { ...(init?.headers ?? {}), Authorization: `Bearer ${token}` },
    });
  }

  async function refreshData() {
    if (!business) return;
    setRefreshing(true);
    try {
      const bid = business.id;
      const [s, src, list] = await Promise.all([
        apiAuth<KnowledgeStats>(`/api/business/${bid}/knowledge/stats`),
        apiAuth<SourceRow[]>(`/api/business/${bid}/knowledge/sources`),
        apiAuth<ChunkListResponse>(
          `/api/business/${bid}/knowledge/chunks?page=${displayChunkPage}&page_size=${CHUNKS_PER_PAGE}&q=${encodeURIComponent(query)}${
            sourceType ? `&source_type=${encodeURIComponent(sourceType)}` : ""
          }`,
        ),
      ]);
      setStats(s);
      setSources(src);
      setChunks(list);
      setEditingChunkId(null);
      setSelectedSourceUrls((prev) => {
        const valid = new Set(src.map((row) => row.source_url).filter((url): url is string => !!url));
        return new Set(Array.from(prev).filter((url) => valid.has(url)));
      });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Failed to load knowledge base.");
    } finally {
      setRefreshing(false);
    }
  }

  async function pollTask(taskId: string, businessId: string) {
    const maxAttempts = 40;
    for (let i = 0; i < maxAttempts; i += 1) {
      try {
        const t = await apiAuth<IngestTask>(`/api/business/${businessId}/knowledge/tasks/${taskId}`);
        setTask(t);
        if (t.status === "completed") {
          toast.success(`Ingestion complete (${t.result?.chunks_created ?? 0} new chunks).`);
          await refreshData();
          return;
        }
        if (t.status === "failed") {
          toast.error(t.error ?? "Ingestion failed.");
          return;
        }
      } catch (e) {
        toast.error(e instanceof ApiError ? e.message : "Could not read ingestion progress.");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    toast.message("Ingestion still running. Refresh in a moment to see final state.");
  }

  async function onUpload(file: File) {
    if (!business || !token) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("enrich_summary", "true");
      const res = await fetch(`/api/business/${business.id}/knowledge/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const data = (await res.json()) as { task_id?: string; error?: { message?: string } };
      if (!res.ok || !data.task_id) {
        throw new Error(data.error?.message ?? "Upload failed.");
      }
      toast.success("Upload accepted. Processing started.");
      await pollTask(data.task_id, business.id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function onScrapeSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!business || !scrapeUrl.trim()) return;
    setScraping(true);
    try {
      const resp = await apiAuth<{ task_id: string }>(`/api/business/${business.id}/knowledge/scrape`, {
        method: "POST",
        json: { url: scrapeUrl.trim(), enrich_summary: true },
      });
      toast.success("Scrape accepted. Processing started.");
      setScrapeUrl("");
      await pollTask(resp.task_id, business.id);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Scrape failed.");
    } finally {
      setScraping(false);
    }
  }

  async function onDeleteChunk(chunkId: string) {
    if (!business) return;
    if (deletingChunkId) return;
    if (!window.confirm("Delete this chunk? This cannot be undone.")) return;
    setDeletingChunkId(chunkId);
    try {
      await apiAuth<void>(`/api/business/${business.id}/knowledge/chunks/${chunkId}`, { method: "DELETE" });
      toast.success("Chunk deleted.");
      await refreshData();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Delete failed.");
    } finally {
      setDeletingChunkId(null);
    }
  }

  async function onDeleteSource(sourceUrl: string) {
    if (!business) return;
    if (deletingSourceUrl || deletingSelectedSources) return;
    if (!window.confirm("Delete all chunks from this source?")) return;
    setDeletingSourceUrl(sourceUrl);
    try {
      await apiAuth<{ deleted: number }>(`/api/business/${business.id}/knowledge/chunks/batch`, {
        method: "DELETE",
        json: { source_url: sourceUrl },
      });
      toast.success("Source chunks deleted.");
      await refreshData();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Batch delete failed.");
    } finally {
      setDeletingSourceUrl(null);
    }
  }

  function toggleSourceSelection(sourceUrl: string) {
    setSelectedSourceUrls((prev) => {
      const next = new Set(prev);
      if (next.has(sourceUrl)) {
        next.delete(sourceUrl);
      } else {
        next.add(sourceUrl);
      }
      return next;
    });
  }

  function toggleSelectVisibleSources() {
    const visible = pagedSources
      .map((src) => src.source_url)
      .filter((url): url is string => !!url);
    if (visible.length === 0) return;
    const allVisibleSelected = visible.every((url) => selectedSourceUrls.has(url));
    setSelectedSourceUrls((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) {
        for (const url of visible) next.delete(url);
      } else {
        for (const url of visible) next.add(url);
      }
      return next;
    });
  }

  async function onDeleteSelectedSources() {
    if (!business) return;
    if (selectedSourceUrls.size === 0) return;
    if (deletingSourceUrl || deletingSelectedSources) return;
    const urls = Array.from(selectedSourceUrls);
    if (!window.confirm(`Delete all chunks for ${urls.length} selected source(s)?`)) return;
    setDeletingSelectedSources(true);
    try {
      await Promise.all(
        urls.map((sourceUrl) =>
          apiAuth<{ deleted: number }>(`/api/business/${business.id}/knowledge/chunks/batch`, {
            method: "DELETE",
            json: { source_url: sourceUrl },
          }),
        ),
      );
      toast.success(`Deleted chunks from ${urls.length} source(s).`);
      setSelectedSourceUrls(new Set());
      await refreshData();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Batch delete failed.");
    } finally {
      setDeletingSelectedSources(false);
    }
  }

  function startEdit(chunk: ChunkRow) {
    setEditingChunkId(chunk.id);
    setEditTitle(chunk.title ?? "");
    setEditSummary(chunk.llm_summary ?? "");
    setEditContent(chunk.content);
    setFindText("");
    setReplaceText("");
    setPreviewMode(false);
  }

  function cancelEdit() {
    setEditingChunkId(null);
    setEditTitle("");
    setEditSummary("");
    setEditContent("");
    setFindText("");
    setReplaceText("");
    setPreviewMode(false);
  }

  function applyFindReplace() {
    const find = findText.trim();
    if (!find) {
      toast.error("Enter text to find.");
      return;
    }
    const next = editContent.split(find).join(replaceText);
    if (next === editContent) {
      toast.message("No matches found.");
      return;
    }
    setEditContent(next);
    toast.success("Replaced matching text in current chunk.");
  }

  async function saveEdit(chunk: ChunkRow) {
    if (!business || !editContent.trim()) return;
    setSavingChunkId(chunk.id);
    try {
      await apiAuth<ChunkRow>(`/api/business/${business.id}/knowledge/chunks/${chunk.id}`, {
        method: "PUT",
        json: {
          content: editContent.trim(),
          title: editTitle.trim() || null,
          llm_summary: editSummary.trim() || null,
          metadata: chunk.metadata,
        },
      });
      toast.success("Chunk updated and re-embedded.");
      await refreshData();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Save failed.");
    } finally {
      setSavingChunkId(null);
    }
  }

  if (!slug) return <ShellState title="Missing workspace" body="No slug in URL." />;
  if (loading) return <ShellState title="Loading knowledge base" body="Fetching business context..." />;
  if (!business) return <ShellState title="Business not found" body={error ?? "You do not have access."} />;

  return (
    <div className="dark min-h-screen bg-[#0f0f23] text-foreground">
      <main className="mx-auto max-w-6xl space-y-6 px-6 py-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-white/40">Knowledge base</p>
            <h1 className="text-xl font-semibold text-white">{business.name}</h1>
            <p className="text-sm text-white/55">Upload files, scrape pages, and manage chunks.</p>
          </div>
          <div className="flex items-center gap-3">
            <Link to={`/b/${business.slug}/admin`} className="text-sm text-indigo-300 hover:underline">
              Settings
            </Link>
            <button
              type="button"
              onClick={() => void refreshData()}
              className="rounded-lg border border-white/15 px-3 py-2 text-sm text-white/90 hover:bg-white/5"
              disabled={refreshing}
            >
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-white/10 bg-[#12122a] p-5">
            <h2 className="text-sm font-medium text-white/70">Upload file</h2>
            <p className="mt-1 text-xs text-white/50">PDF, TXT, or Markdown.</p>
            <input
              type="file"
              accept=".pdf,.txt,.md,.markdown,text/plain,application/pdf,text/markdown"
              className="mt-4 block w-full rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-white"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void onUpload(file);
                e.currentTarget.value = "";
              }}
              disabled={uploading}
            />
            <p className="mt-2 text-xs text-white/45">{uploading ? "Uploading and queueing..." : " "}</p>
          </div>

          <form onSubmit={onScrapeSubmit} className="rounded-xl border border-white/10 bg-[#12122a] p-5">
            <h2 className="text-sm font-medium text-white/70">Scrape URL</h2>
            <p className="mt-1 text-xs text-white/50">Ingest a public webpage via Jina Reader.</p>
            <input
              value={scrapeUrl}
              onChange={(e) => setScrapeUrl(e.target.value)}
              placeholder="https://example.com/page"
              className="mt-4 w-full rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400"
            />
            <button
              type="submit"
              disabled={scraping || !scrapeUrl.trim()}
              className="mt-3 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-400 disabled:opacity-60"
            >
              {scraping ? "Scraping..." : "Scrape and ingest"}
            </button>
          </form>
        </section>

        {task ? (
          <section className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4">
            <p className="text-sm font-medium text-indigo-200">
              Task `{task.task_id.slice(0, 8)}` - {task.status}
            </p>
            <p className="mt-1 text-xs text-indigo-100/80">
              {task.stage ?? "pending"}{task.message ? ` - ${task.message}` : ""}
            </p>
          </section>
        ) : null}

        <section className="grid gap-4 md:grid-cols-3">
          <CardStat label="Total chunks" value={String(stats?.total_chunks ?? "-")} />
          <CardStat
            label="Source types"
            value={stats ? Object.keys(stats.by_source_type).length.toString() : "-"}
          />
          <CardStat label="Sources" value={String(sources.length)} />
        </section>

        <section className="rounded-xl border border-white/10 bg-[#12122a] p-5">
          <div className="flex flex-wrap items-center gap-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search chunk content..."
              className="min-w-60 flex-1 rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-white outline-none focus:border-indigo-400"
            />
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="rounded border border-white/15 bg-black/20 px-3 py-2 text-sm text-white"
            >
              <option value="">All source types</option>
              {sourceTypeOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setChunkPage(1);
                void refreshData();
              }}
              className="rounded-lg bg-white/10 px-3 py-2 text-sm text-white hover:bg-white/15"
            >
              Apply
            </button>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-white/10 bg-[#12122a] p-5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-sm font-medium text-white/70">Sources</h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="rounded border border-white/15 px-2 py-1 text-xs text-white/85 hover:bg-white/10 disabled:opacity-50"
                  onClick={toggleSelectVisibleSources}
                  disabled={pagedSources.length === 0 || deletingSelectedSources || !!deletingSourceUrl}
                >
                  Select visible
                </button>
                <button
                  type="button"
                  className="rounded border border-red-400/40 px-2 py-1 text-xs text-red-300 hover:bg-red-500/10 disabled:opacity-50"
                  onClick={() => void onDeleteSelectedSources()}
                  disabled={
                    selectedSourceUrls.size === 0 || deletingSelectedSources || !!deletingSourceUrl
                  }
                >
                  {deletingSelectedSources
                    ? "Deleting selected..."
                    : `Delete selected (${selectedSourceUrls.size})`}
                </button>
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {pagedSources.length === 0 ? (
                <p className="text-sm text-white/45">No sources yet.</p>
              ) : (
                pagedSources.map((src) => (
                  <div key={`${src.source_url}-${src.source_type}`} className="rounded border border-white/10 p-3">
                    {src.source_url ? (
                      <label className="mb-2 flex items-center gap-2 text-xs text-white/60">
                        <input
                          type="checkbox"
                          checked={selectedSourceUrls.has(src.source_url)}
                          onChange={() => toggleSourceSelection(src.source_url!)}
                          disabled={deletingSelectedSources || !!deletingSourceUrl}
                        />
                        Select for batch delete
                      </label>
                    ) : null}
                    <p className="text-xs text-white/40">{src.source_type ?? "unknown"}</p>
                    <p className="truncate text-sm text-white/85">{src.source_url ?? "N/A"}</p>
                    <p className="mt-1 text-xs text-white/50">{src.chunk_count} chunks</p>
                    {src.source_url ? (
                      <button
                        type="button"
                        className="mt-2 text-xs text-red-300 hover:underline disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed"
                        onClick={() => void onDeleteSource(src.source_url!)}
                        disabled={
                          deletingSourceUrl === src.source_url ||
                          !!deletingSourceUrl ||
                          deletingSelectedSources
                        }
                      >
                        {deletingSourceUrl === src.source_url ? "Deleting..." : "Delete source chunks"}
                      </button>
                    ) : null}
                  </div>
                ))
              )}
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-white/60">
              <span>
                Page {displaySourcePage} of {totalSourcePages}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-white/15 px-2 py-1 hover:bg-white/10 disabled:opacity-40"
                  disabled={displaySourcePage <= 1}
                  onClick={() => setSourcePage((p) => Math.max(1, p - 1))}
                >
                  Prev
                </button>
                <button
                  type="button"
                  className="rounded border border-white/15 px-2 py-1 hover:bg-white/10 disabled:opacity-40"
                  disabled={displaySourcePage >= totalSourcePages}
                  onClick={() => setSourcePage((p) => Math.min(totalSourcePages, p + 1))}
                >
                  Next
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-[#12122a] p-5">
            <h2 className="text-sm font-medium text-white/70">Chunks</h2>
            <div className="mt-3 space-y-3">
              {!chunks || chunks.items.length === 0 ? (
                <p className="text-sm text-white/45">No chunks found.</p>
              ) : (
                chunks.items.map((chunk) => {
                  const isEditing = editingChunkId === chunk.id;
                  return (
                    <div key={chunk.id} className="rounded border border-white/10 p-3">
                      <p className="text-xs text-white/40">{chunk.source_type ?? "unknown"}</p>
                      {isEditing ? (
                        <div className="mt-2 space-y-2">
                          <input
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            placeholder="Title"
                            className="w-full rounded border border-white/15 bg-black/20 px-2 py-1 text-sm text-white"
                          />
                          <input
                            value={editSummary}
                            onChange={(e) => setEditSummary(e.target.value)}
                            placeholder="LLM summary"
                            className="w-full rounded border border-white/15 bg-black/20 px-2 py-1 text-sm text-white"
                          />
                          <div className="rounded border border-white/10 p-2">
                            <p className="mb-2 text-xs uppercase tracking-wide text-white/45">Find & Replace</p>
                            <div className="grid gap-2 sm:grid-cols-2">
                              <input
                                value={findText}
                                onChange={(e) => setFindText(e.target.value)}
                                placeholder="Find text"
                                className="rounded border border-white/15 bg-black/20 px-2 py-1 text-sm text-white"
                              />
                              <input
                                value={replaceText}
                                onChange={(e) => setReplaceText(e.target.value)}
                                placeholder="Replace with"
                                className="rounded border border-white/15 bg-black/20 px-2 py-1 text-sm text-white"
                              />
                            </div>
                            <div className="mt-2 flex items-center justify-between">
                              <button
                                type="button"
                                className="rounded border border-white/20 px-2 py-1 text-xs text-white/85 hover:bg-white/10"
                                onClick={applyFindReplace}
                              >
                                Replace all in this chunk
                              </button>
                              <button
                                type="button"
                                className="rounded border border-white/20 px-2 py-1 text-xs text-white/85 hover:bg-white/10"
                                onClick={() => setPreviewMode((v) => !v)}
                              >
                                {previewMode ? "Edit mode" : "Preview mode"}
                              </button>
                            </div>
                          </div>
                          {previewMode ? (
                            <div className="max-h-64 overflow-auto whitespace-pre-wrap rounded border border-white/15 bg-black/20 px-2 py-2 text-sm text-white/90">
                              {editContent}
                            </div>
                          ) : (
                            <textarea
                              value={editContent}
                              onChange={(e) => setEditContent(e.target.value)}
                              rows={7}
                              className="w-full rounded border border-white/15 bg-black/20 px-2 py-1 text-sm text-white"
                            />
                          )}
                          <div className="flex items-center justify-end gap-2">
                            <button
                              type="button"
                              className="rounded border border-white/20 px-2 py-1 text-xs text-white/80 hover:bg-white/10"
                              onClick={cancelEdit}
                              disabled={savingChunkId === chunk.id}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              className="rounded bg-indigo-500 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-400 disabled:opacity-60"
                              onClick={() => void saveEdit(chunk)}
                              disabled={savingChunkId === chunk.id || !editContent.trim()}
                            >
                              {savingChunkId === chunk.id ? "Saving..." : "Save & re-embed"}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <p className="line-clamp-3 text-sm text-white/85">{chunk.content}</p>
                          <div className="mt-2 flex items-center justify-between">
                            <p className="text-xs font-mono text-white/45">{chunk.id.slice(0, 8)}</p>
                            <div className="flex items-center gap-3">
                              <button
                                type="button"
                                className="text-xs text-indigo-300 hover:underline disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed"
                                onClick={() => startEdit(chunk)}
                                disabled={deletingChunkId === chunk.id}
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                className="inline-flex items-center gap-1 text-xs text-red-300 hover:underline disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed"
                                onClick={() => void onDeleteChunk(chunk.id)}
                                disabled={deletingChunkId === chunk.id || !!deletingChunkId}
                              >
                                {deletingChunkId === chunk.id ? (
                                  <>
                                    <Spinner /> Deleting...
                                  </>
                                ) : (
                                  "Delete"
                                )}
                              </button>
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })
              )}
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-white/60">
              <span>
                Page {displayChunkPage} of {totalChunkPages} - {chunks?.total ?? 0} chunks
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-white/15 px-2 py-1 hover:bg-white/10 disabled:opacity-40"
                  disabled={displayChunkPage <= 1}
                  onClick={() => setChunkPage((p) => Math.max(1, p - 1))}
                >
                  Prev
                </button>
                <button
                  type="button"
                  className="rounded border border-white/15 px-2 py-1 hover:bg-white/10 disabled:opacity-40"
                  disabled={displayChunkPage >= totalChunkPages}
                  onClick={() => setChunkPage((p) => Math.min(totalChunkPages, p + 1))}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="inline-block h-3 w-3 animate-spin rounded-full border border-white/30 border-t-transparent"
    />
  );
}

function CardStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#12122a] p-4">
      <p className="text-xs uppercase tracking-wide text-white/40">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function ShellState({ title, body }: { title: string; body: string }) {
  return (
    <div className="dark flex min-h-screen items-center justify-center bg-[#0f0f23] px-6 text-center">
      <div className="max-w-lg rounded-xl border border-white/10 bg-[#12122a] p-8">
        <h1 className="text-lg font-semibold text-white">{title}</h1>
        <p className="mt-2 text-sm text-white/60">{body}</p>
      </div>
    </div>
  );
}
