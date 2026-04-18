import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  console.warn(
    "[rag-factory] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY — auth will not work until .env is configured.",
  );
}

/** Browser Supabase client (anon key, RLS-aware). */
export const supabase = createClient(url ?? "", anonKey ?? "");
