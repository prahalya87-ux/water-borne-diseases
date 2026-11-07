import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { AppShell } from "../components/layout";
import { incidents, nationalContext, type Incident } from "../data/incidents";

const sev = {
  high: "bg-red-100 text-red-700 border-red-300",
  moderate: "bg-amber-100 text-amber-800 border-amber-300",
  low: "bg-green-100 text-green-700 border-green-300",
};

function Kpi({ label, value, tone }: { label: string; value: string | number; tone: string }) {
  return (
    <div className={`rounded-xl p-5 text-white shadow ${tone}`}>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-sm opacity-90">{label}</div>
    </div>
  );
}

function IncidentCard({ i }: { i: Incident }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="rounded-xl bg-white p-5 shadow">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-blue-300 bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">SOURCE-REPORTED</span>
        <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${sev[i.severity]}`}>{i.severity.toUpperCase()}</span>
        <span className="text-xs text-slate-500">{i.date}</span>
      </div>
      <h3 className="mt-2 flex items-center gap-2 text-lg font-bold text-navy-800"><AlertTriangle size={18} className="text-red-500" />{i.title}</h3>
      <p className="text-sm text-slate-600">{i.locality}, {i.state}</p>
      <p className="mt-2 text-sm">{i.summary}</p>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div><dt className="font-semibold">Disease</dt><dd>{i.disease}</dd></div>
        <div><dt className="font-semibold">Water source</dt><dd>{i.waterSource}</dd></div>
        <div><dt className="font-semibold">Cases</dt><dd>{i.cases ?? "Not stated"} <span className="text-slate-500">- {i.casesNote}</span></dd></div>
        <div><dt className="font-semibold">Status</dt><dd>{i.status}</dd></div>
      </dl>
      <button onClick={() => setOpen(!open)} className="mt-3 flex items-center gap-1 text-sm font-semibold text-aqua-600" aria-expanded={open}>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />} {open ? "Hide details" : "Full details"}
      </button>
      {open && (
        <div className="mt-3 space-y-3 border-t pt-3 text-sm">
          <div><h4 className="font-semibold">Suspected cause</h4><p>{i.suspectedCause}</p></div>
          <div><h4 className="font-semibold">Timeline</h4><ul className="list-disc pl-5">{i.timeline.map((t) => <li key={t.date}><strong>{t.date}:</strong> {t.event}</li>)}</ul></div>
          <div><h4 className="font-semibold">General precautions</h4><ul className="list-disc pl-5">{i.precautions.map((p) => <li key={p}>{p}</li>)}</ul></div>
          <p className="rounded bg-amber-50 p-2 text-amber-900"><strong>Note:</strong> {i.caveat}</p>
          <p>Source: {i.sourceUrl ? <a className="inline-flex items-center gap-1 text-aqua-600 underline" href={i.sourceUrl} target="_blank" rel="noreferrer">{i.source} <ExternalLink size={12} /></a> : i.source}</p>
        </div>
      )}
    </article>
  );
}

export default function Dashboard() {
  return (
    <AppShell title="Main Dashboard">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Source-reported incidents shown" value={incidents.length} tone="bg-gradient-to-br from-aqua-500 to-cyan-400" />
        <Kpi label="Incidents with linked sources" value={incidents.filter((i) => i.sourceUrl).length} tone="bg-gradient-to-br from-blue-600 to-indigo-500" />
        <Kpi label="Reported hospital admissions (Indore)" value="436*" tone="bg-gradient-to-br from-red-500 to-rose-400" />
        <Kpi label="High-severity reports" value={incidents.filter((i) => i.severity === "high").length} tone="bg-gradient-to-br from-orange-500 to-amber-400" />
      </div>
      <p className="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-900">{nationalContext.text} <a className="underline" href={nationalContext.url} target="_blank" rel="noreferrer">{nationalContext.source}</a>. *The Indore figure is a source-reported admission count, not a lab-confirmed case count.</p>

      <section id="incidents" className="mt-6">
        <h2 className="mb-3 text-lg font-bold text-navy-800">Source-reported incidents</h2>
        <p className="mb-3 text-sm text-slate-600">These reports are linked to their publishers and have not been independently verified by WaterGuard. A report is not proof of an outbreak.</p>
        <div className="grid gap-4 lg:grid-cols-2">{incidents.map((i) => <IncidentCard key={i.id} i={i} />)}</div>
      </section>
    </AppShell>
  );
}