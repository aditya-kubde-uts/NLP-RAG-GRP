import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/context/use-auth";
import { ApiError, apiJson } from "@/lib/api";
import type { BusinessDetail } from "@/types/super-admin";

/**
 * Resolve a business-admin workspace by URL slug.
 *
 * Hits ``GET /api/business/by-slug/{slug}`` which:
 * - returns the business detail when the signed-in user is a member admin, OR
 * - returns the business detail when the signed-in user is a platform super admin
 *   (super admins are not in ``business_members`` so client-side lookups via
 *   ``profile.businesses`` don't find them; the server-side check does).
 *
 * Shared by Phase 6/7/8 business-admin sub-pages so they don't duplicate the
 * slug→id plumbing.
 */
export type UseBusinessBySlug = {
  business: BusinessDetail | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
};

export function useBusinessBySlug(slug: string | undefined): UseBusinessBySlug {
  const { session } = useAuth();
  const token = session?.access_token;

  const [business, setBusiness] = useState<BusinessDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(slug));
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!slug) {
      setBusiness(null);
      setLoading(false);
      return;
    }
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const d = await apiJson<BusinessDetail>(
        `/api/business/by-slug/${encodeURIComponent(slug)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      setBusiness(d);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to load business.";
      setError(msg);
      setBusiness(null);
    } finally {
      setLoading(false);
    }
  }, [slug, token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional fetch-on-mount
    void load();
  }, [load]);

  return { business, loading, error, reload: load };
}
