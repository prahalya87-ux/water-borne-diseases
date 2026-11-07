import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "../components/layout";
import { apiFetch, useAuth } from "../lib/auth";

type Dash = {
  reports: { total: number; pending_review: number; verified: number; escalated: number; by_status: Record<string, number> };
  resolution: { resolved: number; open: number; rejected: number; resolution_rate: number | null };
  reports_by_location: { locality: string; count: number }[];
  water_quality: { classification_counts: Record<string, number>; laboratory_confirmed: number };
  disease_trends: { weeks: { week_start: string; records: number; cases: number }[] };
  alerts_awaiting_approval: { count: number };
};
type Alert = { id: string; title: string; locality: string; severity: string; description: string; verification_status: string };
type Rep = { report_code: string; category: string; water_source: string; locality: string; pin_code: string | null; status: string; description: string; contact_info: string | null; latitude: number | null; longitude: number | null; escalated_at: string | null; escalation_reason: string | null; possible_duplicate_of: string | null; created_at: string };

const statuses = ["submitted", "under_review", "verification_required", "verified", "forwarded_to_authority", "resolved", "rejected"];
const pretty = (s: string) => s.replace(/_/g, " ");

function Stat({ label, value, tone }: { label: string; value: string | number; tone: string }) {
  return <div className={`rounded-xl p-4 text-white shadow ${tone}`}><div className="text-2xl font-bold">{value}</div><div className="text-sm opacity-90">{label}</div></div>;
}

export default function Admin() {
  const { user, token } = useAuth();
  const [dash, setDash] = useState<Dash | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [reports, setReports] = useState<Rep[]>([]);
  const [filter, setFilter] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [photos, setPhotos] = useState<Record<string, string[]>>({});
  const [msg, setMsg] = useState("");
  const isAdmin = user?.role === "administrator";
  const allowed = isAdmin || user?.role === "field_inspector";

  const load = useCallback(async () => {
    try {
      const q = filter ? `?status_filter=${filter}` : "";
      const r = await apiFetch(`/api/admin/reports${q}`, token);
      if (r.ok) setReports(await r.json());
      if (isAdmin) {
        const d = await apiFetch("/api/admin/dashboard", token); if (d.ok) setDash(await d.json());
        const a = await apiFetch("/api/admin/alerts/pending", token); if (a.ok) setAlerts(await a.json());
      }
    } catch { setMsg("Could not reach the backend. Start it with: uvicorn app.main:app --reload"); }
  }, [token, filter, isAdmin]);

  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!user) return <AppShell title="Admin & Public Health Dashboard"><p className="rounded-xl bg-white p-6 shadow">Please <Link className="text-aqua-600 underline" to="/login">sign in</Link> with an authorised account.</p></AppShell>;
  if (!allowed) return <AppShell title="Admin & Public Health Dashboard"><p className="rounded-xl bg-white p-6 shadow">Your account does not have access to this area.</p></AppShell>;

  async function setStatus(code: string, status: string) {
    let reason: string | undefined;
    if (status === "rejected") { reason = window.prompt("Reason for rejecting this report (required):")?.trim(); if (!reason) return; }
    const r = await apiFetch(`/api/admin/reports/${code}`, token, { method: "PATCH", body: JSON.stringify({ status, rejection_reason: reason ?? null }) });
    setMsg(r.ok ? `${code} updated to ${pretty(status)}.` : "Update failed."); load();
  }

  async function decide(id: string, approve: boolean) {
    let init: RequestInit = { method: "POST", body: approve ? undefined : "" };
    if (!approve) { const reason = window.prompt("Reason for rejecting this alert (required):")?.trim(); if (!reason) return; init = { method: "POST", body: JSON.stringify({ reason }) }; }
    const r = await apiFetch(`/api/admin/alerts/${id}/${approve ? "approve" : "reject"}`, token, init);
    setMsg(r.ok ? (approve ? "Alert approved and published." : "Alert rejected.") : "Action failed."); load();
  }

  async function showPhotos(code: string) {
    setOpen(open === code ? null : code);
    if (photos[code]) return;
    const list = await (await apiFetch(`/api/admin/reports/${code}/evidence`, token)).json();
    const urls: string[] = [];
    for (const e of list) { const r = await apiFetch(`/api/admin/evidence/${e.evidence_id}`, token); if (r.ok) urls.push(URL.createObjectURL(await r.blob())); }
    setPhotos((p) => ({ ...p, [code]: urls }));
  }

  return (
    <AppShell title="Admin & Public Health Dashboard">
      {msg && <p role="status" className="mb-4 rounded bg-blue-50 p-3 text-sm text-blue-900">{msg}</p>}
      {dash && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            <Stat label="Total reports" value={dash.reports.total} tone="bg-gradient-to-br from-aqua-500 to-cyan-400" />
            <Stat label="Pending review" value={dash.reports.pending_review} tone="bg-gradient-to-br from-orange-500 to-amber-400" />
            <Stat label="Verified" value={dash.reports.verified} tone="bg-gradient-to-br from-green-600 to-emerald-400" />
            <Stat label="Escalated" value={dash.reports.escalated} tone="bg-gradient-to-br from-red-500 to-rose-400" />
            <Stat label="Resolution rate" value={dash.resolution.resolution_rate === null ? "n/a" : `${Math.round(dash.resolution.resolution_rate * 100)}%`} tone="bg-gradient-to-br from-blue-600 to-blue-400" />
            <Stat label="Alerts awaiting approval" value={dash.alerts_awaiting_approval.count} tone="bg-gradient-to-br from-slate-700 to-slate-500" />
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl bg-white p-4 shadow"><h2 className="font-bold text-navy-800">Reports by location</h2>
              {dash.reports_by_location.length ? <div className="mt-2 h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={dash.reports_by_location}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="locality" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill="#06b6d4" /></BarChart></ResponsiveContainer></div> : <p className="mt-2 text-sm text-slate-500">No reports yet.</p>}</section>
            <section className="rounded-xl bg-white p-4 shadow"><h2 className="font-bold text-navy-800">Disease-report trend (cases per week)</h2>
              {dash.disease_trends.weeks.length ? <div className="mt-2 h-56"><ResponsiveContainer width="100%" height="100%"><LineChart data={dash.disease_trends.weeks}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="week_start" /><YAxis allowDecimals={false} /><Tooltip /><Line dataKey="cases" stroke="#ef4444" /></LineChart></ResponsiveContainer></div> : <p className="mt-2 text-sm text-slate-500">No disease records in the last 12 weeks.</p>}</section>
            <section className="rounded-xl bg-white p-4 shadow text-sm"><h2 className="font-bold text-navy-800">Water-quality readings</h2>
              <p className="mt-1">Laboratory-confirmed tests: {dash.water_quality.laboratory_confirmed}</p>
              <ul className="mt-1 list-disc pl-5">{Object.entries(dash.water_quality.classification_counts).map(([k, v]) => <li key={k}>{pretty(k)}: {v}</li>)}</ul>
              {!Object.keys(dash.water_quality.classification_counts).length && <p className="text-slate-500">No test results recorded.</p>}</section>
            <section className="rounded-xl bg-white p-4 shadow text-sm"><h2 className="font-bold text-navy-800">Report resolution status</h2>
              <p className="mt-1">Open: {dash.resolution.open} | Resolved: {dash.resolution.resolved} | Rejected: {dash.resolution.rejected}</p>
              <p className="mt-2 text-xs text-slate-500">Counts include unverified citizen reports and are not confirmed cases.</p></section>
          </div>
        </>
      )}

      {isAdmin && (
        <section className="mt-6 rounded-xl bg-white p-4 shadow"><h2 className="font-bold text-navy-800">Alerts awaiting approval</h2>
          {!alerts.length && <p className="mt-2 text-sm text-slate-500">Nothing is waiting for approval.</p>}
          <ul className="mt-2 space-y-3">{alerts.map((a) => (
            <li key={a.id} className="rounded border p-3 text-sm">
              <div className="font-semibold">{a.title} <span className="font-normal text-slate-500">- {a.locality} - {a.severity} - {pretty(a.verification_status)}</span></div>
              <p className="mt-1">{a.description}</p>
              <div className="mt-2 flex gap-2">
                <button onClick={() => decide(a.id, true)} className="rounded bg-green-600 px-3 py-1 text-white">Approve and publish</button>
                <button onClick={() => decide(a.id, false)} className="rounded bg-red-600 px-3 py-1 text-white">Reject</button>
              </div></li>))}</ul></section>
      )}

      <section className="mt-6 rounded-xl bg-white p-4 shadow">
        <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-bold text-navy-800">Report verification</h2>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter by status" className="rounded border px-2 py-1 text-sm"><option value="">All statuses</option>{statuses.map((s) => <option key={s} value={s}>{pretty(s)}</option>)}</select></div>
        {!reports.length && <p className="mt-2 text-sm text-slate-500">No reports match.</p>}
        <ul className="mt-3 space-y-3">{reports.map((r) => (
          <li key={r.report_code} className="rounded border p-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div><b>{r.report_code}</b> - {pretty(r.category)} - {r.locality} {r.escalated_at && <span className="ml-1 rounded bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">ESCALATED</span>}</div>
              <select value={r.status} onChange={(e) => setStatus(r.report_code, e.target.value)} aria-label={`Status for ${r.report_code}`} className="rounded border px-2 py-1">{statuses.map((s) => <option key={s} value={s}>{pretty(s)}</option>)}</select>
            </div>
            <button onClick={() => showPhotos(r.report_code)} className="mt-1 text-aqua-600 underline">{open === r.report_code ? "Hide details" : "Details and photos"}</button>
            {open === r.report_code && (
              <div className="mt-2 space-y-1 border-t pt-2">
                <p><b>Source:</b> {r.water_source}{r.pin_code && ` | PIN ${r.pin_code}`}{r.latitude !== null && ` | ${r.latitude}, ${r.longitude}`}</p>
                <p><b>Description:</b> {r.description || "None given"}</p>
                <p><b>Contact (private):</b> {r.contact_info ?? "None given"}</p>
                {r.escalation_reason && <p className="text-red-700"><b>Escalation reason:</b> {r.escalation_reason}</p>}
                {r.possible_duplicate_of && <p className="text-amber-800"><b>Possible duplicate of:</b> {r.possible_duplicate_of}</p>}
                <div className="flex flex-wrap gap-2">{(photos[r.report_code] ?? []).map((u) => <img key={u} src={u} alt="Uploaded evidence" className="h-24 rounded border" />)}</div>
                {photos[r.report_code]?.length === 0 && <p className="text-slate-500">No photos uploaded.</p>}
              </div>)}
          </li>))}</ul>
      </section>
    </AppShell>
  );
}