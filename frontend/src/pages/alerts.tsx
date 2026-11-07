import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, BellRing, ExternalLink } from "lucide-react";
import { AppShell } from "../components/layout";
import { apiFetch, useAuth } from "../lib/auth";

type Alert = { id: string; title: string; locality: string; district: string | null; severity: string; description: string; recommended_action: string; source: string; source_url: string | null; verification_status: string; is_demo: boolean; published_at: string };
type Note = { id: string; title: string; body: string; severity: string; link: string | null; is_read: boolean; created_at: string };
type Sub = { id: string; locality: string };

const sevStyle: Record<string, string> = {
  critical: "border-red-400 bg-red-50 text-red-800", warning: "border-orange-400 bg-orange-50 text-orange-800",
  advisory: "border-amber-300 bg-amber-50 text-amber-900", info: "border-blue-300 bg-blue-50 text-blue-800",
};
const verLabel: Record<string, string> = {
  official: "Official advisory", unverified_draft: "Unverified - not an official advisory",
};

export default function Alerts() {
  const { user, token } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [subs, setSubs] = useState<Sub[]>([]);
  const [locality, setLocality] = useState("");
  const [sev, setSev] = useState("all");
  const [newSub, setNewSub] = useState("");
  const [msg, setMsg] = useState("");
  const [loadError, setLoadError] = useState("");

  const load = useCallback(async () => {
    try {
      const q = locality.trim() ? `?locality=${encodeURIComponent(locality.trim())}` : "";
      const a = await apiFetch(`/api/alerts${q}`, null);
      if (!a.ok) throw new Error(`Alerts request failed (${a.status}). Check the API service and its logs.`);
      setAlerts((await a.json()).filter((alert: Alert) => !alert.is_demo));
      if (token) {
        const n = await apiFetch("/api/notifications", token);
        if (!n.ok) throw new Error(`Notifications request failed (${n.status}). Sign in again if your session has expired.`);
        setNotes((await n.json()).filter((note: Note) => !note.title.startsWith("[DEMO EXAMPLE] ")));
        const s = await apiFetch("/api/subscriptions", token);
        if (!s.ok) throw new Error(`Subscriptions request failed (${s.status}). Sign in again if your session has expired.`);
        setSubs(await s.json());
      }
      setLoadError("");
    } catch (error) {
      setLoadError(error instanceof TypeError
        ? "Unable to connect to the WaterGuard API. For local development, open the Vite site with the backend running; for deployment, check VITE_API_URL."
        : error instanceof Error ? error.message : "The alerts request failed for an unknown reason.");
    }
  }, [locality, token]);

  useEffect(() => { load(); }, [load]);

  async function subscribe(e: React.FormEvent) {
    e.preventDefault();
    if (newSub.trim().length < 2) return;
    const r = await apiFetch("/api/subscriptions", token, { method: "POST", body: JSON.stringify({ locality: newSub.trim() }) });
    setMsg(r.ok ? `You will be notified about alerts for ${newSub.trim()}.` : r.status === 409 ? "You already follow this area." : "Could not subscribe.");
    if (r.ok) setNewSub("");
    load();
  }
  async function unsubscribe(id: string) { await apiFetch(`/api/subscriptions/${id}`, token, { method: "DELETE" }); load(); }
  async function markRead(id: string) { await apiFetch(`/api/notifications/${id}/read`, token, { method: "POST" }); load(); }

  const shown = alerts.filter((a) => sev === "all" || a.severity === sev);
  const unread = notes.filter((n) => !n.is_read).length;

  return (
    <AppShell title="Alerts & Notifications">
      {loadError && <p role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{loadError}</p>}
      <div className="grid gap-6 xl:grid-cols-3">
        <section className="space-y-3 xl:col-span-2">
          <div className="flex flex-wrap gap-3 rounded-xl bg-white p-3 shadow">
            <input value={locality} onChange={(e) => setLocality(e.target.value)} placeholder="Filter by area name (exact match)" aria-label="Filter by area" className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm" />
            <select value={sev} onChange={(e) => setSev(e.target.value)} aria-label="Filter by severity" className="rounded-lg border px-2 py-2 text-sm">
              <option value="all">All severities</option><option value="critical">Critical</option><option value="warning">Warning</option><option value="advisory">Advisory</option><option value="info">Info</option>
            </select>
          </div>
          {!shown.length && !loadError && (
            <div className="rounded-xl bg-white p-6 text-sm text-slate-600 shadow">
              No published alerts{locality || sev !== "all" ? " match these filters" : " right now"}. Alerts appear here only after an administrator approves them. No alert does not guarantee safe water: check with your local water authority.
            </div>
          )}
          {shown.map((a) => (
            <article key={a.id} className={`rounded-xl border-2 p-4 ${sevStyle[a.severity] ?? sevStyle.info}`}>
              <div className="flex flex-wrap items-center gap-2 text-xs font-semibold">
                <span className="flex items-center gap-1 rounded-full bg-white/70 px-2 py-0.5"><BellRing size={12} />{a.severity.toUpperCase()}</span>
                <span className="rounded-full bg-white/70 px-2 py-0.5">{verLabel[a.verification_status] ?? a.verification_status}</span>
              </div>
              <h2 className="mt-2 text-lg font-bold">{a.title}</h2>
              <p className="text-sm">{a.locality}{a.district && `, ${a.district}`} - {new Date(a.published_at).toLocaleString()}</p>
              <p className="mt-2 text-sm">{a.description}</p>
              <p className="mt-2 rounded bg-white/70 p-2 text-sm"><b>Recommended action:</b> {a.recommended_action}</p>
              <p className="mt-2 text-xs">Source: {a.source_url ? <a className="inline-flex items-center gap-1 underline" href={a.source_url} target="_blank" rel="noreferrer">{a.source} <ExternalLink size={12} /></a> : a.source}</p>
            </article>
          ))}
        </section>

        <aside className="space-y-4">
          {!user ? (
            <div className="rounded-xl bg-white p-4 text-sm shadow">
              <h2 className="flex items-center gap-2 font-bold text-navy-800"><Bell size={16} />Get alerts for your area</h2>
              <p className="mt-2">It is free. <Link className="text-aqua-600 underline" to="/login">Sign in or create an account</Link> to follow an area and see your notifications.</p>
            </div>
          ) : (
            <>
              <section className="rounded-xl bg-white p-4 shadow">
                <h2 className="flex items-center gap-2 font-bold text-navy-800"><Bell size={16} />Areas you follow</h2>
                <form onSubmit={subscribe} className="mt-2 flex gap-2">
                  <input value={newSub} onChange={(e) => setNewSub(e.target.value)} placeholder="Area name, e.g. Kurla" aria-label="Area to follow" maxLength={160} className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm" />
                  <button className="rounded-lg bg-aqua-500 px-3 py-2 text-sm font-semibold text-white">Follow</button>
                </form>
                {msg && <p role="status" className="mt-2 text-sm text-slate-600">{msg}</p>}
                <ul className="mt-2 space-y-1 text-sm">
                  {subs.map((s) => <li key={s.id} className="flex items-center justify-between rounded border px-2 py-1">{s.locality}<button onClick={() => unsubscribe(s.id)} className="text-red-600 underline">Unfollow</button></li>)}
                  {!subs.length && <li className="text-slate-500">You are not following any area yet. Use the same spelling as the alert's area name.</li>}
                </ul>
              </section>
              <section className="rounded-xl bg-white p-4 shadow">
                <h2 className="font-bold text-navy-800">Your notifications {unread > 0 && <span className="ml-1 rounded-full bg-red-500 px-2 py-0.5 text-xs text-white">{unread} new</span>}</h2>
                {!notes.length && <p className="mt-2 text-sm text-slate-500">No notifications yet.</p>}
                <ul className="mt-2 space-y-2 text-sm">
                  {notes.map((n) => (
                    <li key={n.id} className={`rounded border p-2 ${n.is_read ? "bg-white text-slate-600" : "border-aqua-500 bg-cyan-50"}`}>
                      <div className="font-semibold">{n.title}</div>
                      <div>{n.body}</div>
                      <div className="mt-1 flex items-center gap-3 text-xs text-slate-500">{new Date(n.created_at).toLocaleString()}
                        {n.link?.startsWith("/track/") && <Link className="text-aqua-600 underline" to={n.link}>Open report</Link>}
                        {!n.is_read && <button onClick={() => markRead(n.id)} className="text-aqua-600 underline">Mark as read</button>}</div>
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}
          <p className="rounded-xl bg-white p-4 text-xs text-slate-500 shadow">Notifications appear inside the website only; email and browser push are not available. Unverified notices are not official advisories.</p>
        </aside>
      </div>
    </AppShell>
  );
}