/**
 * JSON API helpers. Prefer same-origin `/api` (Vite dev proxy → FastAPI).
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

type ErrorBody = {
  error?: { code?: string; message?: string };
  detail?: unknown;
};

function formatFastApiDetail(detail: unknown): string | null {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const o = item as { loc?: unknown[]; msg?: string };
        const loc = Array.isArray(o.loc) ? o.loc.filter(Boolean).join(".") : "";
        return loc ? `${loc}: ${o.msg ?? "invalid"}` : (o.msg ?? "invalid");
      }
      return JSON.stringify(item);
    });
    return parts.join("; ");
  }
  return null;
}

export async function apiJson<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const { json, headers: hdrs, ...rest } = init ?? {};
  const headers = new Headers(hdrs);
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const err = (data ?? {}) as ErrorBody;
    const code = err.error?.code ?? "http_error";
    const fromBody = err.error?.message;
    const fromDetail = formatFastApiDetail(err.detail);
    const message = fromBody ?? fromDetail ?? res.statusText;
    throw new ApiError(res.status, code, message);
  }

  return data as T;
}
