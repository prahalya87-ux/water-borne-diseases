import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink, Siren } from "lucide-react";
import { AppShell } from "../components/layout";
import { diseases } from "../data/diseases";

function UrgentBanner() {
  return (
    <div role="note" className="flex gap-3 rounded-xl border-2 border-red-300 bg-red-50 p-4 text-sm text-red-900">
      <Siren className="shrink-0" />
      <p><b>Emergency?</b> Call 112 or go to the nearest hospital for blood in stool, constant vomiting, seizures, fainting, confusion, very little urine, or severe weakness. Babies, young children, older adults and pregnant women can become seriously ill quickly.</p>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return <section><h3 className="font-bold text-navy-800">{title}</h3><ul className="mt-1 list-disc space-y-1 pl-5 text-sm">{items.map((i) => <li key={i}>{i}</li>)}</ul></section>;
}

export default function Diseases() {
  const { slug } = useParams();
  const d = diseases.find((x) => x.slug === slug);

  if (slug && !d) {
    return <AppShell title="Disease Information Centre"><p className="rounded-xl bg-white p-6 shadow">That topic was not found. <Link className="text-aqua-600 underline" to="/diseases">Back to all topics</Link></p></AppShell>;
  }

  if (d) {
    return (
      <AppShell title={d.name}>
        <article className="mx-auto max-w-3xl space-y-5">
          <Link to="/diseases" className="flex items-center gap-1 text-sm text-aqua-600 underline"><ArrowLeft size={14} />All diseases</Link>
          <div className="rounded-xl bg-white p-5 shadow">
            <p className="text-sm text-slate-500">Caused by: {d.cause}</p>
            <p className="mt-2">{d.explanation}</p>
            <p className="mt-2 text-sm"><b>Time from infection to symptoms:</b> {d.incubation}</p>
          </div>
          <UrgentBanner />
          <div className="grid gap-5 rounded-xl bg-white p-5 shadow md:grid-cols-2">
            <List title="How it spreads" items={d.transmission} />
            <List title="Common symptoms" items={d.symptoms} />
            <List title="When to get medical care" items={d.seekCare} />
            <List title="How to prevent it" items={d.prevention} />
          </div>
          <div className="space-y-2 rounded-xl bg-white p-5 text-sm shadow">
            <p><b>Treatment:</b> {d.treatment}</p>
            <p><b>Vaccine:</b> {d.vaccine}</p>
            <p className="text-slate-600">This page is general information, not a diagnosis. Only a doctor and tests can tell which illness a person has. Home water checks cannot replace laboratory testing: see the <Link className="text-aqua-600 underline" to="/water-quality">Water Quality checker</Link>.</p>
          </div>
          <div className="rounded-xl bg-white p-5 text-sm shadow">
            <h3 className="font-bold text-navy-800">References</h3>
            <ul className="mt-1 space-y-1">{d.references.map((r) => <li key={r.url}><a className="inline-flex items-center gap-1 text-aqua-600 underline" href={r.url} target="_blank" rel="noreferrer">{r.label} <ExternalLink size={12} /></a></li>)}</ul>
            <p className="mt-2 text-xs text-slate-500">Last reviewed: {d.lastReviewed}. Medical guidance changes, so please also check the current pages linked above and follow advice from your doctor and local health authority.</p>
          </div>
        </article>
      </AppShell>
    );
  }

  return (
    <AppShell title="Disease Information Centre">
      <p className="mb-4 max-w-3xl text-sm text-slate-600">Plain-language guidance on the main water-related diseases: how they spread, what to look for, how to prevent them, and when to get care. Each page lists its sources and when it was last reviewed.</p>
      <div className="mb-5 max-w-3xl"><UrgentBanner /></div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {diseases.map((x) => (
          <Link key={x.slug} to={`/diseases/${x.slug}`} className="rounded-xl bg-white p-5 shadow transition hover:shadow-lg">
            <h2 className="text-lg font-bold text-navy-800">{x.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{x.tagline}</p>
            <p className="mt-3 text-xs text-slate-400">Incubation: {x.incubation}</p>
            <span className="mt-2 inline-block text-sm font-semibold text-aqua-600">Read more</span>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}