import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";

import { AuthStateContext } from "./auth-state-context";
import type { AuthContextValue, LoginApiResponse, SignupApiResponse, UserProfile } from "./auth-types";

import { apiJson } from "@/lib/api";
import { supabase } from "@/lib/supabase";

async function fetchProfile(accessToken: string): Promise<UserProfile | null> {
  try {
    return await apiJson<UserProfile>("/api/auth/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [session, setSession] = useState<AuthContextValue["session"]>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshProfile = useCallback(async () => {
    const { data } = await supabase.auth.getSession();
    const s = data.session;
    if (!s?.access_token) {
      setProfile(null);
      return;
    }
    setProfile(await fetchProfile(s.access_token));
  }, []);

  useEffect(() => {
    let cancelled = false;

    void supabase.auth.getSession().then(({ data: { session: s } }) => {
      if (cancelled) return;
      setSession(s);
      if (s?.access_token) {
        void fetchProfile(s.access_token).then((p) => {
          if (!cancelled) setProfile(p);
        });
      } else {
        setProfile(null);
      }
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      if (cancelled) return;
      setSession(s);
      if (s?.access_token) {
        void fetchProfile(s.access_token).then((p) => {
          if (!cancelled) setProfile(p);
        });
      } else {
        setProfile(null);
      }
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const body = await apiJson<LoginApiResponse>("/api/auth/login", {
      method: "POST",
      json: { email, password },
    });
    const { error } = await supabase.auth.setSession({
      access_token: body.session.access_token,
      refresh_token: body.session.refresh_token,
    });
    if (error) throw error;
    setProfile(body.user);
    return body.user;
  }, []);

  const signUp = useCallback(async (email: string, password: string, fullName: string) => {
    const body = await apiJson<SignupApiResponse>("/api/auth/signup", {
      method: "POST",
      json: { email, password, full_name: fullName },
    });
    if (body.session) {
      const { error } = await supabase.auth.setSession({
        access_token: body.session.access_token,
        refresh_token: body.session.refresh_token,
      });
      if (error) throw error;
      setProfile(body.user);
    } else {
      setProfile(null);
    }
    if (body.message) {
      return { message: body.message, user: null };
    }
    return { user: body.user };
  }, []);

  const signOut = useCallback(async () => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) {
      try {
        await apiJson("/api/auth/logout", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        /* still clear local session */
      }
    }
    await supabase.auth.signOut();
    setProfile(null);
    navigate("/login", { replace: true });
  }, [navigate]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user: session?.user ?? null,
      profile,
      loading,
      signIn,
      signUp,
      signOut,
      refreshProfile,
    }),
    [session, profile, loading, signIn, signUp, signOut, refreshProfile],
  );

  return <AuthStateContext.Provider value={value}>{children}</AuthStateContext.Provider>;
}
