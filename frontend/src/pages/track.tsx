import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AppShell } from "../components/layout";

const API: string = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";
type R = { report_code: string; category: string; water_source: string; locality: string; pin_code: string | null; status: string; rejection_reason: string | null; observed_at: string; created_at: string; is_demo: boolean; verification_label: string };

const steps = [
  ["submitted", "Submitted"], ["under_review", "Under review"], ["verification_required", "Verification required"],
  ["verified", "Verified"], ["forwarded_to_authority", "Forwarded to authority"], ["resolved", "Resolved"],
];

export default function Track() {
  const { code } = useParams();
  const nav = useNavigate();
  const [input, setInput] = useState(code ?? "");
  const [r, setR] = useState<R | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!code) return;
    setR(null); setError("");
    fetch(`${API}/api/reports/${encodeURIComponent(code)}`)
      .then(async (res) => {
        if (res.status === 404) throw new Error("No report found with that ID. Check the ID and try again.");
        if (!res.ok) throw new Error("Could not load the report.");
        const report: R = await res.json();
        if (report.is_demo) throw new Error("This report is not a real submission and cannot be tracked.");
        setR(report);
      })
      .catch((e) => setError(e instanceof TypeError ? "Could not reach the WaterGuard backend. Start it with: uvicorn app.main:app --reload" : e.message));
  }, [code]);

  const idx = r ? steps.findIndex(([s]) => s === r.status) : -1;
  return (
    <AppShell title="Track a Report">
      <div className="mx-auto max-w-xl space-y-4">
        <form onSubmit={(e) => { e.preventDefault(); if (input.trim()) nav(`/track/${input.trim().toUpperCase()}`); }} className="flex gap-2 rounded-xl bg-white p-4 shadow">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Report ID, e.g. WG-A1B2C3" aria-label="Report ID" className="min-w-0 flex-1 rounded-lg border px-3 py-2" />
          <button className="rounded-lg bg-aqua-500 px-4 py-2 font-semibold text-white">Track</button>
        </form>
        {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {r && (
          <div className="rounded-xl bg-white p-5 shadow">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-bold text-navy-800">{r.report_code}</h2>
              <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">{r.status === "verified" || r.status === "forwarded_to_authority" || r.status === "resolved" ? "Reviewed by staff" : r.verification_label}</span>
            </div>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <div><dt className="font-semibold">Problem</dt><dd>{r.category.replace(/_/g, " ")}</dd></div>
              <div><dt className="font-semibold">Water source</dt><dd>{r.water_source}</dd></div>
              <div><dt className="font-semibold">Location</dt><dd>{r.locality}{r.pin_code && ` (PIN ${r.pin_code})`}</dd></div>
              <div><dt className="font-semibold">Observed</dt><dd>{new Date(r.observed_at).toLocaleString()}</dd></div>
              <div><dt className="font-semibold">Submitted</dt><dd>{new Date(r.created_at).toLocaleString()}</dd></div>
            </dl>
            {r.status === "rejected" ? (
              <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-800"><b>Rejected.</b> Reason: {r.rejection_reason}</p>
            ) : (
              <ol className="mt-4 space-y-2" aria-label="Report progress">
                {steps.map(([s, label], i) => (
                  <li key={s} className={`flex items-center gap-2 text-sm ${i <= idx ? "font-semibold text-navy-800" : "text-slate-400"}`}>
                    <span className={`h-3 w-3 rounded-full ${i < idx ? "bg-green-500" : i === idx ? "bg-aqua-500" : "bg-slate-200"}`} />{label}{i === idx && " (current)"}
                  </li>
                ))}
              </ol>
            )}
            <p className="mt-4 text-xs text-slate-500">Status updates are made by authorised staff. A report being under review does not confirm a contamination or outbreak.</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}