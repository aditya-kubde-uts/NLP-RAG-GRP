export type PlatformStats = {
  total_businesses: number;
  total_users: number;
  total_chat_messages: number;
  estimated_api_cost_usd: number;
};

export type BusinessRow = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  industry: string;
  logo_url: string | null;
  settings: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  chunk_count: number;
  chat_count: number;
  admin_count: number;
};

export type AdminCredentials = {
  email: string;
  password: string | null;
  was_created: boolean;
};

export type BusinessCreateResponse = BusinessRow & {
  admin: AdminCredentials | null;
};

export type BusinessAdminSummary = {
  user_id: string;
  email: string | null;
  full_name: string | null;
  role: string;
  created_at: string | null;
};

export type BusinessSettings = {
  user_login_required: boolean;
  custom_system_prompt: string;
  welcome_message: string;
  primary_color: string;
  max_chunks_per_query: number;
  confidence_threshold: number;
};

export type BusinessDetail = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  industry: string;
  logo_url: string | null;
  settings: Partial<BusinessSettings> & Record<string, unknown>;
  is_active: boolean;
  created_at: string;
};
