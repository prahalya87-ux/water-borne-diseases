import { Link } from "react-router-dom";
import { Droplets, ShieldCheck, Activity } from "lucide-react";
import { Logo } from "../components/layout";
import { incidents, nationalContext } from "../data/incidents";

export default function Home() {
  const stats = [
    { icon: Activity, big: String(incidents.length), label: "Source-reported incidents shown" },
    { icon: Droplets, big: "436*", label: "Hospital admissions reported, Indore, Dec 2025 to Jan 2026" },
    { icon: ShieldCheck, big: "5,500+", label: "Reported ill from contaminated tap water, India, Jan 2025 to 7 Jan 2026" },
  ];
  return (
    <div className="min-h-screen bg-gradient-to-b from-navy-900 via-navy-800 to-navy-700 text-white">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo />
        <Link to="/dashboard" className="rounded-full bg-aqua-500 px-5 py-2 text-sm font-semibold hover:bg-aqua-600">Open dashboard</Link>
      </nav>
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 py-14 md:grid-cols-2">
        <div>
          <h1 className="text-4xl font-extrabold leading-tight md:text-5xl">
            Predict Water Risks.<br />Prevent Disease.<br /><span className="text-aqua-400">Protect Communities.</span>
          </h1>
          <p className="mt-5 max-w-lg text-blue-100">
            An AI-assisted platform for water-borne disease surveillance, water-quality screening and community reporting.
            Risk estimates are decision support, never a diagnosis or a confirmed outbreak.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/dashboard" className="rounded-lg bg-aqua-500 px-6 py-3 font-semibold shadow-lg shadow-cyan-500/30 hover:bg-aqua-600">Explore Dashboard</Link>
            <a href="#how" className="rounded-lg border border-aqua-400 px-6 py-3 font-semibold text-aqua-400 hover:bg-white/5">How it works</a>
          </div>
        </div>
        <div className="flex justify-center" aria-hidden>
          <div className="relative flex h-72 w-72 items-center justify-center rounded-full bg-cyan-400/10 ring-1 ring-cyan-400/40">
            <div className="absolute inset-6 rounded-full ring-1 ring-cyan-400/30" />
            <svg width="150" height="150" viewBox="0 0 32 32">
              <path d="M16 2 4 7v8c0 7 5 12 12 15 7-3 12-8 12-15V7L16 2Z" fill="#06b6d4" />
              <path d="M16 8c3 4 5 6 5 9a5 5 0 0 1-10 0c0-3 2-5 5-9Z" fill="#fff" />
            </svg>
          </div>
        </div>
      </section>
      <section className="mx-auto grid max-w-6xl gap-4 px-6 pb-12 md:grid-cols-3">
        {stats.map(({ icon: Icon, big, label }) => (
          <div key={label} className="rounded-xl border border-cyan-400/30 bg-white/5 p-5 backdrop-blur">
            <Icon className="text-aqua-400" />
            <div className="mt-2 text-3xl font-bold">{big}</div>
            <div className="text-sm text-blue-100">{label}</div>
          </div>
        ))}
        <p className="text-xs text-blue-200 md:col-span-3">Sources: {nationalContext.source} and the incident sources listed on the dashboard. *Source-reported admissions, not lab-confirmed cases.</p>
      </section>
      <section id="how" className="mx-auto max-w-6xl px-6 pb-20">
        <h2 className="mb-4 text-2xl font-bold">How it works</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {["Monitor: collect sourced incidents, lab results and citizen reports.", "Analyse: flag potential hotspots with transparent rules and clear limitations.", "Act: show precautions, nearby care and advisories, always labelled by verification level."].map((t) => (
            <div key={t} className="rounded-xl bg-white/5 p-5 text-blue-100">{t}</div>
          ))}
        </div>
      </section>
    </div>
  );
}