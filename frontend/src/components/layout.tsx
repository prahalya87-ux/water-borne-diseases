import { useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { LayoutDashboard, Home as HomeIcon, Map as MapIcon, FlaskConical, ClipboardList, Search, ShieldCheck, LogIn, LogOut, Bell, MessageCircle, TrendingUp, BookOpen, Hospital, Menu, X } from "lucide-react";
import { APP_NAME } from "../data/incidents";
import { useAuth } from "../lib/auth";

export function Logo({ light = true }: { light?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
        <path d="M16 2 4 7v8c0 7 5 12 12 15 7-3 12-8 12-15V7L16 2Z" fill="#06b6d4" />
        <path d="M16 8c3 4 5 6 5 9a5 5 0 0 1-10 0c0-3 2-5 5-9Z" fill="#fff" />
        <path d="M16 15v5M13.5 17.5h5" stroke="#06b6d4" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <span className={`font-bold tracking-tight ${light ? "text-white" : "text-navy-800"}`}>{APP_NAME}</span>
    </Link>
  );
}

const link = ({ isActive }: { isActive: boolean }) =>
  `flex min-w-0 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-white/20 text-white" : "text-blue-100 hover:bg-white/10"}`;

function Navigation({ onNavigate, className }: { onNavigate?: () => void; className: string }) {
  const { user, logout } = useAuth();
  const items = [
    { to: "/", end: true, icon: HomeIcon, label: "Home" },
    { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/map", icon: MapIcon, label: "Interactive Map" },
    { to: "/hospitals", icon: Hospital, label: "Nearby Hospitals" },
    { to: "/water-quality", icon: FlaskConical, label: "Water Quality" },
    { to: "/report", icon: ClipboardList, label: "Report Water Issue" },
    { to: "/track", icon: Search, label: "Track Report" },
    { to: "/alerts", icon: Bell, label: "Alerts" },
    { to: "/prediction", icon: TrendingUp, label: "Risk Prediction" },
    { to: "/assistant", icon: MessageCircle, label: "AI Assistant" },
    { to: "/diseases", icon: BookOpen, label: "Disease Info" },
    ...(user && (user.role === "administrator" || user.role === "field_inspector")
      ? [{ to: "/admin", icon: ShieldCheck, label: "Admin" }]
      : []),
  ];

  return (
    <nav className={className} aria-label="Main">
      {items.map(({ to, end, icon: Icon, label }) => (
        <NavLink key={to} to={to} end={end} onClick={onNavigate} className={link}>
          <Icon size={18} className="shrink-0" />
          <span className="truncate">{label}</span>
        </NavLink>
      ))}
      {user
        ? <button onClick={() => { logout(); onNavigate?.(); }} className="flex min-w-0 items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-blue-100 hover:bg-white/10"><LogOut size={18} className="shrink-0" /><span className="truncate">Sign out ({user.full_name})</span></button>
        : <NavLink to="/login" onClick={onNavigate} className={link}><LogIn size={18} className="shrink-0" /><span className="truncate">Sign in</span></NavLink>}
    </nav>
  );
}

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="min-h-screen md:flex">
      <div className="bg-gradient-to-b from-blue-700 to-blue-900 p-4 md:hidden">
        <div className="flex items-center justify-between gap-3">
          <Logo />
          <button
            type="button"
            className="rounded-lg p-2 text-white hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
        {menuOpen && <Navigation onNavigate={() => setMenuOpen(false)} className="mt-4 grid max-h-[65vh] grid-cols-2 gap-1 overflow-y-auto sm:grid-cols-3" />}
      </div>
      <aside className="hidden bg-gradient-to-b from-blue-700 to-blue-900 p-4 md:sticky md:top-0 md:block md:h-screen md:w-60 md:shrink-0 md:overflow-y-auto">
        <div className="mb-6"><Logo /></div>
        <Navigation className="flex flex-col gap-1" />
      </aside>
      <div className="min-w-0 flex-1">
        <header className="bg-gradient-to-r from-aqua-500 to-cyan-400 px-4 py-3 text-white shadow sm:px-6 sm:py-4">
          <h1 className="text-xl font-bold">{title}</h1>
        </header>
        <main className="min-w-0 p-4 sm:p-6">{children}</main>
        <footer className="px-4 pb-8 text-xs text-slate-500 sm:px-6">
          Risk information is an estimate and does not replace official health advisories or professional medical advice.
        </footer>
      </div>
    </div>
  );
}