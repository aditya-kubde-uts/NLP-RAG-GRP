import type { Session, User } from "@supabase/supabase-js";

export type UserProfile = {
  id: string;
  email: string;
  full_name: string | null;
  is_super_admin: boolean;
  businesses: { id: string; name: string; slug: string; role: string }[];
};

type LoginApiResponse = {
  session: {
    access_token: string;
    refresh_token: string;
    expires_in: number;
    token_type: string;
  };
  user: UserProfile;
};

type SignupApiResponse = {
  user: UserProfile;
  session: LoginApiResponse["session"] | null;
  message: string | null;
};

export type AuthContextValue = {
  session: Session | null;
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<UserProfile | null>;
  signUp: (
    email: string,
    password: string,
    fullName: string,
  ) => Promise<{ message?: string; user?: UserProfile | null }>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
};

export type { LoginApiResponse, SignupApiResponse };
