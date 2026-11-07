import { useEffect, useState } from "react";
import { Download, FlaskConical } from "lucide-react";
import { AppShell } from "../components/layout";

const API: string = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";

type Param = { parameter: string; label: string; value: number | string | null; unit: string; guideline: string; status: string; severity: "ok" | "caution" | "action_required" | "unknown"; message: string; source: string };
type Result = { overall: string; parameters: Param[]; lab_test_recommended: boolean; lab_test_reasons: string[]; advice: string[]; disclaimer: string; standard_sources: string[]; report_text: string };
type Stored = { id: string; sample_id: string; locality: string; tested_at: string; organization: string; verification_status: string; classification: string; is_demo: boolean };

const overallStyle: Record<string, { box: string; text: string }> = {
  action_required: { box: "border-red-400 bg-red-50 text-red-800", text: "ACTION REQUIRED - at least one result needs urgent attention." },
  caution: { box: "border-amber-400 bg-amber-50 text-amber-900", text: "CAUTION - one or more values are outside the guideline." },
  no_exceedance_found: { box: "border-green-400 bg-green-50 text-green-800", text: "No limit exceeded in the values entered. This is not a guarantee that the water is safe." },
  insufficient_data: { box: "border-slate-300 bg-slate-50 text-slate-700", text: "Not enough data to assess. Enter at least one value." },
};
const sevDot = { ok: "bg-green-500", caution: "bg-amber-500", action_required: "bg-red-600", unknown: "bg-slate-300" };

// Visual ranges for the bars: [min, max, goodFrom, goodTo, permissibleTo]
const ranges: Record<string, [number, number, number, number, number | null]> = {
  ph: [0, 14, 6.5, 8.5, null],
  turbidity_ntu: [0, 10, 0, 1, 5],
  tds_mg_l: [0, 3000, 0, 500, 2000],
  residual_chlorine_mg_l: [0, 2, 0.2, 1, null],
};

function RangeBar({ p }: { p: Param }) {
  const r = ranges[p.parameter];
  if (!r || typeof p.value !== "number") return null;
  const [min, max, g1, g2, perm] = r;
  const pct = (v: number) => Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100));
  return (
    <div className="relative mt-2 h-3 rounded-full bg-red-200" aria-hidden>
      {perm && <div className="absolute h-3 rounded-full bg-amber-200" style={{ left: `${pct(g1)}%`, width: `${pct(perm) - pct(g1)}%` }} />}
      <div className="absolute h-3 rounded-full bg-green-300" style={{ left: `${pct(g1)}%`, width: `${pct(g2) - pct(g1)}%` }} />
      <div className="absolute -top-1 h-5 w-1.5 rounded bg-navy-800" style={{ left: `calc(${pct(p.value)}% - 3px)` }} />
    </div>
  );
}

const fields = [
  { key: "ph", label: "pH", hint: "0 to 14", step: "0.1" },
  { key: "turbidity_ntu", label: "Turbidity (NTU)", hint: "cloudiness", step: "0.1" },
  { key: "tds_mg_l", label: "TDS (mg/L)", hint: "total dissolved solids", step: "1" },
  { key: "residual_chlorine_mg_l", label: "Residual chlorine (mg/L)", hint: "chlorinated supply only", step: "0.01" },
] as const;

export default function WaterQuality() {
  const [vals, setVals] = useState<Record<string, string>>({});
  const [ecoli, setEcoli] = useState("not_tested");
  const [source, setSource] = useState("tap");
  const [lab, setLab] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stored, setStored] = useState<{ items: Stored[]; message: string | null } | null>(null);

  useEffect(() => {
    fetch(`${API}/api/water-quality`).then((r) => r.json()).then((data) => {
      setStored({ ...data, items: data.items.filter((item: Stored) => !item.is_demo) });
    }).catch(() => setStored(null));
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setResult(null);
    const body: Record<string, unknown> = { ecoli, source_type: source, from_laboratory_report: lab };
    for (const f of fields) {
      const s = (vals[f.key] ?? "").trim();
      if (s === "") continue;
      const n = Number(s);
      if (Number.isNaN(n)) { setError(`${f.label} must be a number.`); return; }
      body[f.key] = n;
    }
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/water-quality/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (res.status === 422) { setError("One of the values is outside the allowed range (for example pH must be 0 to 14)."); return; }
      if (!res.ok) throw new Error();
      setResult(await res.json());
    } catch {
      setError("Could not reach the WaterGuard backend. Start it with: uvicorn app.main:app --reload (inside the backend folder).");
    } finally { setBusy(false); }
  }

  function download() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([result.report_text], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url; a.download = "waterguard-water-quality-report.txt"; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <AppShell title="Water Quality Monitoring">
      <div className="grid gap-6 xl:grid-cols-3">
        <form onSubmit={submit} className="space-y-3 rounded-xl bg-white p-5 shadow">
          <h2 className="flex items-center gap-2 font-bold text-navy-800"><FlaskConical size={18} />Water Quality Risk Checker</h2>
          <p className="text-sm text-slate-600">Enter the test results you have. Leave blank any you don't have.</p>
          {fields.map((f) => (
            <label key={f.key} className="block text-sm">
              <span className="font-medium">{f.label}</span> <span className="text-slate-400">({f.hint})</span>
              <input type="number" step={f.step} inputMode="decimal" value={vals[f.key] ?? ""} onChange={(e) => setVals({ ...vals, [f.key]: e.target.value })} className="mt-1 w-full rounded-lg border px-3 py-2" />
            </label>
          ))}
          <label className="block text-sm"><span className="font-medium">E. coli test result</span>
            <select value={ecoli} onChange={(e) => setEcoli(e.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2">
              <option value="not_tested">Not tested</option><option value="absent">Absent (not detected)</option><option value="present">Present (detected)</option>
            </select></label>
          <label className="block text-sm"><span className="font-medium">Water source</span>
            <select value={source} onChange={(e) => setSource(e.target.value)} className="mt-1 w-full rounded-lg border px-3 py-2">
              {["tap", "borewell", "tank", "river", "other"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select></label>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={lab} onChange={(e) => setLab(e.target.checked)} />These values come from a laboratory report</label>
          {error && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
          <button disabled={busy} className="w-full rounded-lg bg-aqua-500 px-4 py-2 font-semibold text-white hover:bg-aqua-600 disabled:opacity-60">{busy ? "Checking..." : "Check my water"}</button>
        </form>

        <div className="space-y-4 xl:col-span-2">
          {!result && <div className="rounded-xl bg-white p-6 text-sm text-slate-600 shadow">Your result appears here, with each value compared against the BIS IS 10500:2012 and WHO guidelines. This tool never says water is "safe": only a laboratory test can confirm microbiological safety.</div>}
          {result && (
            <>
              <div className={`rounded-xl border-2 p-4 font-semibold ${overallStyle[result.overall].box}`}>{overallStyle[result.overall].text}</div>
              <div className="grid gap-3 sm:grid-cols-2">
                {result.parameters.map((p) => (
                  <div key={p.parameter} className="rounded-xl bg-white p-4 shadow">
                    <div className="flex items-center gap-2"><span className={`h-3 w-3 rounded-full ${sevDot[p.severity]}`} /><h3 className="font-bold text-navy-800">{p.label}</h3></div>
                    <div className="text-2xl font-bold">{p.value === null ? "Not provided" : `${p.value} ${p.unit}`}</div>
                    <div className="text-xs text-slate-500">Guideline: {p.guideline}</div>
                    <RangeBar p={p} />
                    <p className="mt-2 text-sm">{p.message}</p>
                  </div>
                ))}
              </div>
              <div className={`rounded-xl border p-4 text-sm ${result.lab_test_recommended ? "border-amber-300 bg-amber-50" : "border-green-300 bg-green-50"}`}>
                <h3 className="font-bold">Professional laboratory test: {result.lab_test_recommended ? "recommended" : "not urgently needed"}</h3>
                <ul className="mt-1 list-disc pl-5">{result.lab_test_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              </div>
              {result.advice.length > 0 && <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm"><h3 className="font-bold text-red-800">What to do now</h3><ul className="mt-1 list-disc pl-5">{result.advice.map((a) => <li key={a}>{a}</li>)}</ul></div>}
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                <button onClick={download} className="flex items-center gap-1 rounded-lg border border-aqua-500 px-3 py-2 text-sm font-semibold text-aqua-600"><Download size={16} />Download report</button>
                <span>Sources: {result.standard_sources.join("; ")}. {result.disclaimer}</span>
              </div>
            </>
          )}

          <section className="rounded-xl bg-white p-5 shadow">
            <h2 className="font-bold text-navy-800">Recorded laboratory results</h2>
            {!stored && <p className="mt-2 text-sm text-slate-500">Results could not be loaded. Start the backend to see recorded tests.</p>}
            {stored?.message && <p className="mt-2 rounded bg-slate-50 p-2 text-sm text-slate-600">{stored.message}</p>}
            <ul className="mt-2 space-y-2 text-sm">
              {stored?.items.map((t) => (
                <li key={t.id} className="rounded border p-2">
                  <b>{t.sample_id}</b> - {t.locality} - {t.organization} - {new Date(t.tested_at).toLocaleDateString()}
                  <div className="text-slate-600">{t.verification_status.replace(/_/g, " ")} - classification: {t.classification.replace(/_/g, " ")}</div>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </AppShell>
  );
}