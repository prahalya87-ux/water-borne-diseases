import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "../components/layout";
import { apiFetch, useAuth } from "../lib/auth";

type Item = { id: string; locality: string; category: string; score: number | null; confidence: string; factors: { factor: string; points: number; detail: string }[]; missing_data: string[]; recommendation: string; limitations: string; is_demo: boolean; analysed_at: string; period_start: string | null; period_end: string | null };
type Data = { items: Item[]; method: { name: string; validated: boolean; description: string; rules: { factor: string; points: string }[]; categories: string }; limitations: string; disclaimer: string; last_analysis: string | null; current_inputs: { citizen_reports_14d: number; water_tests_30d: number; disease_reports_56d: number }; historical_context: { source_reported_incidents_on_file: number; disease_record_window_days: number } };

function requestError(error: unknown) {
  if (error instanceof TypeError) {
    return "Unable to connect to the WaterGuard API. For local development, open the Vite site with the backend running; for deployment, check VITE_API_URL.";
  }
  return error instanceof Error ? error.message : "The risk request failed for an unknown reason.";
}

const catStyle: Record<string, string> = {
  high: "bg-red-100 text-red-700 border-red-300", moderate: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-green-100 text-green-700 border-green-300", insufficient_data: "bg-slate-100 text-slate-600 border-slate-300",
};
const label = (c: string) => (c === "insufficient_data" ? "INSUFFICIENT DATA" : c.toUpperCase());

export default function Prediction() {
  const { user, token } = useAuth();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await apiFetch("/api/risk/assessments", null);
      if (!r.ok) throw new Error(`Risk data request failed (${r.status}). Check the API service and its logs.`);
      setData(await r.json());
      setError("");
    } catch (e) { setError(requestError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function run() {
    setBusy(true);
    try {
      const r = await apiFetch("/api/admin/risk/run", token, { method: "POST" });
      if (!r.ok) throw new Error(`Analysis failed (${r.status}). Confirm administrator access and check the API service logs.`);
      setData(await r.json());
      setError("");
    } catch (e) { setError(requestError(e)); }
    finally { setBusy(false); }
  }

  const items = (data?.items ?? []).filter((i) => !i.is_demo);
  const chart = items.filter((i) => i.score !== null).map((i) => ({ locality: i.locality, score: i.score }));
  const inputs = data?.current_inputs;
  const currentInputTotal = inputs ? inputs.citizen_reports_14d + inputs.water_tests_30d + inputs.disease_reports_56d : 0;
  return (
    <AppShell title="AI Disease Prediction Dashboard">
      <p className="mb-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">These are screening estimates that help staff decide where to investigate first. They are <b>not</b> diagnoses, probabilities, or confirmed outbreaks, and the method has not been validated against real outbreaks.</p>
      {error && <p role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {user?.role === "administrator" ? <button onClick={run} disabled={busy} className="rounded-lg bg-aqua-500 px-4 py-2 font-semibold text-white disabled:opacity-60">{busy ? "Running..." : "Run analysis now"}</button>
          : <span className="text-sm text-slate-600">Only administrators can run a new analysis. {!user && <Link className="text-aqua-600 underline" to="/login">Sign in</Link>}</span>}
        <span className="text-sm text-slate-500">Last analysis: {data?.last_analysis ? new Date(data.last_analysis).toLocaleString() : "none yet"}</span>
      </div>

      {inputs && <section aria-label="Current risk data inputs" className="mb-4 rounded-xl bg-white p-4 shadow">
        <h2 className="font-bold text-navy-800">Current non-demo inputs in the screening windows</h2>
        <p className="mt-1 text-sm text-slate-600">{inputs.citizen_reports_14d} citizen reports (14 days) · {inputs.water_tests_30d} water tests (30 days) · {inputs.disease_reports_56d} disease reports (56 days). Synthetic/demo records are excluded; citizen reports may be unverified.</p>
        {data?.historical_context && <p className="mt-2 text-sm text-slate-600">{data.historical_context.source_reported_incidents_on_file} sourced historical incidents are on file. Disease reports can affect the risk score only within the latest {data.historical_context.disease_record_window_days} days; older reports are shown as history, not treated as current outbreaks.</p>}
      </section>}

      {data && !items.length && !error && <div className="rounded-xl bg-white p-6 text-sm shadow">
        {currentInputTotal === 0
          ? "No current non-demo observations are available in the screening windows, so there is no defensible current risk estimate. Historical incidents are shown separately and are not treated as present-day outbreaks. New real reports, water tests, or disease reports are needed before analysis."
          : "No saved analysis is available for the current inputs. An administrator can run an analysis now; historical incidents outside the screening windows are not treated as current outbreaks."}
      </div>}

      {chart.length > 0 && (
        <section className="mb-6 rounded-xl bg-white p-4 shadow"><h2 className="font-bold text-navy-800">Risk score by area <span className="text-xs font-normal text-slate-500">(rule-based points, not probabilities)</span></h2>
          <div className="mt-2 h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="locality" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="score" fill="#06b6d4" /></BarChart></ResponsiveContainer></div></section>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {items.map((i) => (
          <article key={i.id} className="rounded-xl bg-white p-5 shadow">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${catStyle[i.category]}`}>{label(i.category)}</span>
              <span className="text-xs text-slate-500">Data confidence: {i.confidence}</span>
            </div>
            <h2 className="mt-2 text-lg font-bold text-navy-800">{i.locality}</h2>
            <p className="text-sm text-slate-600">{i.score === null ? "No score: not enough data" : `Score: ${i.score} points`} | Period: {i.period_start} to {i.period_end} | Analysed {new Date(i.analysed_at).toLocaleString()}</p>
            {i.factors.length > 0 && <div className="mt-3 text-sm"><h3 className="font-semibold">Contributing factors</h3><ul className="list-disc pl-5">{i.factors.map((f) => <li key={f.factor}><b>+{f.points}</b> {f.factor} <span className="text-slate-500">({f.detail})</span></li>)}</ul></div>}
            <div className="mt-3 text-sm"><h3 className="font-semibold">Missing or limited data</h3><ul className="list-disc pl-5 text-slate-600">{i.missing_data.map((m) => <li key={m}>{m}</li>)}</ul></div>
            <p className="mt-3 rounded bg-cyan-50 p-2 text-sm"><b>Suggested next step:</b> {i.recommendation}</p>
            <p className="mt-2 text-xs text-slate-500">{i.limitations}</p>
          </article>
        ))}
      </div>

      {data && (
        <section className="mt-6 rounded-xl bg-white p-5 text-sm shadow"><h2 className="font-bold text-navy-800">How the score works ({data.method.name})</h2>
          <p className="mt-1">{data.method.description}</p>
          <table className="mt-2 w-full text-left"><thead><tr className="border-b"><th className="py-1">Signal</th><th>Points</th></tr></thead>
            <tbody>{data.method.rules.map((r) => <tr key={r.factor} className="border-b"><td className="py-1">{r.factor}</td><td>{r.points}</td></tr>)}</tbody></table>
          <p className="mt-2 text-slate-600">Categories: {data.method.categories}.</p></section>
      )}
    </AppShell>
  );
}