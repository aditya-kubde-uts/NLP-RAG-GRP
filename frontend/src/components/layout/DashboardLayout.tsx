import { Building2, Home, LayoutDashboard, LogOut, Plus } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "@/context/use-auth";
import { cn } from "@/lib/utils";

const navCls = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-white/10 text-white"
      : "text-white/60 hover:bg-white/5 hover:text-white",
  );

export default function DashboardLayout() {
  const { profile, signOut } = useAuth();

  return (
    <div className="flex min-h-screen bg-[#0a0a1a] text-white">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-60 flex-col border-r border-white/10 bg-[#12122a] px-3 py-6">
        <Link to="/dashboard" className="mb-8 flex items-center gap-2 px-2">
          <Building2 className="h-7 w-7 text-indigo-400" />
          <span className="text-lg font-semibold tracking-tight">RAG Factory</span>
        </Link>

        <nav className="flex flex-1 flex-col gap-1">
          <NavLink to="/dashboard" end className={navCls}>
            <LayoutDashboard className="h-4 w-4 shrink-0" />
            Dashboard
          </NavLink>
          <NavLink to="/dashboard/businesses/new" className={navCls}>
            <Plus className="h-4 w-4 shrink-0" />
            New business
          </NavLink>
          <Link
            to="/"
            className="mt-2 flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-white/50 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Home className="h-4 w-4" />
            Public home
          </Link>
        </nav>

        <div className="mt-auto space-y-2 border-t border-white/10 pt-4">
          <div className="truncate px-2 text-xs text-white/50">
            <p className="font-medium text-white/80">{profile?.full_name || profile?.email}</p>
            <p className="truncate">{profile?.email}</p>
          </div>
          <button
            type="button"
            onClick={() => void signOut()}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-white/70 transition-colors hover:bg-white/5 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <div className="ml-60 flex min-h-screen flex-1 flex-col">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-[#0a0a1a]/90 px-8 py-4 backdrop-blur">
          <p className="text-xs uppercase tracking-wider text-white/40">Super admin</p>
          <h1 className="text-lg font-semibold text-white">Platform</h1>
        </header>
        <main className="flex-1 px-8 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
