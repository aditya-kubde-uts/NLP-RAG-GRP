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
