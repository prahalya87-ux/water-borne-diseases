import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { LayoutDashboard, Home as HomeIcon, Map as MapIcon, FlaskConical, ClipboardList, Search, ShieldCheck, LogIn, LogOut, Bell, MessageCircle, TrendingUp, BookOpen, Hospital } from "lucide-react";
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
  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-white/20 text-white" : "text-blue-100 hover:bg-white/10"}`;

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen md:flex">
      <aside className="bg-gradient-to-b from-blue-700 to-blue-900 p-4 md:min-h-screen md:w-60">
        <div className="mb-6"><Logo /></div>
        <nav className="flex gap-2 md:flex-col" aria-label="Main">
          <NavLink to="/" end className={link}><HomeIcon size={18} /> Home</NavLink>
          <NavLink to="/dashboard" className={link}><LayoutDashboard size={18} /> Dashboard</NavLink>
          <NavLink to="/map" className={link}><MapIcon size={18} /> Interactive Map</NavLink>
          <NavLink to="/hospitals" className={link}><Hospital size={18} /> Nearby Hospitals</NavLink>
          <NavLink to="/water-quality" className={link}><FlaskConical size={18} /> Water Quality</NavLink>
          <NavLink to="/report" className={link}><ClipboardList size={18} /> Report Water Issue</NavLink>
          <NavLink to="/track" className={link}><Search size={18} /> Track Report</NavLink>
          <NavLink to="/alerts" className={link}><Bell size={18} /> Alerts</NavLink>
          <NavLink to="/prediction" className={link}><TrendingUp size={18} /> Risk Prediction</NavLink>
          <NavLink to="/assistant" className={link}><MessageCircle size={18} /> AI Assistant</NavLink>
          <NavLink to="/diseases" className={link}><BookOpen size={18} /> Disease Info</NavLink>
          {user && (user.role === "administrator" || user.role === "field_inspector") && <NavLink to="/admin" className={link}><ShieldCheck size={18} /> Admin</NavLink>}
          {user ? <button onClick={logout} className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-blue-100 hover:bg-white/10"><LogOut size={18} /> Sign out ({user.full_name})</button> : <NavLink to="/login" className={link}><LogIn size={18} /> Sign in</NavLink>}
        </nav>
      </aside>
      <div className="flex-1">
        <header className="bg-gradient-to-r from-aqua-500 to-cyan-400 px-6 py-4 text-white shadow">
          <h1 className="text-xl font-bold">{title}</h1>
        </header>
        <main className="p-6">{children}</main>
        <footer className="px-6 pb-8 text-xs text-slate-500">
          Risk information is an estimate and does not replace official health advisories or professional medical advice.
        </footer>
      </div>
    </div>
  );
}