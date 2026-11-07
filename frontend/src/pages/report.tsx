import { useState } from "react";
import { Link } from "react-router-dom";
import { Crosshair } from "lucide-react";
import { AppShell } from "../components/layout";
import { API } from "../lib/api";
const categories = [
  ["unusual_color", "Unusual colour"], ["unusual_odor", "Unusual smell"],
  ["visible_contamination", "Visible contamination"], ["suspected_illness_cluster", "Suspected illness cluster (several people sick)"],
];
const sources = ["tap", "borewell", "tank", "river", "other"];

const nowLocal = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16); };

async function readError(res: Response): Promise<string> {
  if (res.status === 429) return "Too many submissions. Please wait a minute and try again.";
  try {
    const j = await res.json();
    if (Array.isArray(j.detail)) return j.detail.map((d: { field: string; message: string }) => `${d.field}: ${d.message}`).join("; ");
    return j.error ?? "Request failed";
  } catch { return "Request failed"; }
}

export default function Report() {
  const [category, setCategory] = useState("unusual_odor");
  const [source, setSource] = useState("tap");
  const [locality, setLocality] = useState("");
  const [pin, setPin] = useState("");
  const [pos, setPos] = useState<[number, number] | null>(null);
  const [observed, setObserved] = useState(nowLocal());
  const [desc, setDesc] = useState("");
  const [contact, setContact] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ code: string; photoNote: string } | null>(null);

  function locate() {
    navigator.geolocation?.getCurrentPosition(
      (p) => setPos([p.coords.latitude, p.coords.longitude]),
      () => setError("Location permission was not granted. Enter a locality or PIN code instead.")
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!locality.trim() && !pin.trim() && !pos) return setError("Enter a locality, a 6-digit PIN code, or use your location.");
    if (pin.trim() && !/^[1-9][0-9]{5}$/.test(pin.trim())) return setError("PIN code must be 6 digits.");
    if (new Date(observed).getTime() > Date.now() + 60000) return setError("The date and time cannot be in the future.");
    if (photo && !["image/jpeg", "image/png", "image/webp"].includes(photo.type)) return setError("Photo must be a JPEG, PNG or WebP image.");
    if (photo && photo.size > 5 * 1024 * 1024) return setError("Photo must be 5 MB or smaller.");
    if (!consent) return setError("Please tick the consent box to submit.");
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/reports`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category, water_source: source, description: desc.trim() || null, locality: locality.trim() || null,
          pin_code: pin.trim() || null, latitude: pos?.[0] ?? null, longitude: pos?.[1] ?? null,
          observed_at: new Date(observed).toISOString(), contact_info: contact.trim() || null, consent_given: true,
        }),
      });
      if (!res.ok) return setError(await readError(res));
      const { report_code } = await res.json();
      let photoNote = "";
      if (photo) {
        const fd = new FormData(); fd.append("file", photo);
        const up = await fetch(`${API}/api/reports/${report_code}/evidence`, { method: "POST", body: fd });
        photoNote = up.ok ? "Your photo was uploaded." : `Your report was saved, but the photo could not be uploaded: ${await readError(up)}`;
      }
      setDone({ code: report_code, photoNote });
    } catch {
      setError("Could not connect to WaterGuard. In local development, start the backend and open the site through the Vite frontend server; for deployment, configure VITE_API_URL to the backend URL.");
    } finally { setBusy(false); }
  }

  if (done) {
    return (
      <AppShell title="Community Reporting Portal">
        <div className="mx-auto max-w-xl rounded-xl bg-white p-6 shadow">
          <h2 className="text-xl font-bold text-navy-800">Report submitted</h2>
          <p className="mt-3">Your report ID is</p>
          <p className="my-2 rounded-lg bg-cyan-50 p-3 text-center text-3xl font-extrabold tracking-wider text-aqua-600">{done.code}</p>
          <p className="text-sm">Save this ID. Your report is marked <b>Unverified</b> until an authorised reviewer checks it. {done.photoNote}</p>
          <p className="mt-3 rounded bg-red-50 p-3 text-sm text-red-800">If anyone has severe diarrhoea, repeated vomiting, blood in stool, high fever or signs of dehydration, seek medical care now. Do not wait for this report to be reviewed.</p>
          <div className="mt-4 flex gap-3">
            <Link to={`/track/${done.code}`} className="rounded-lg bg-aqua-500 px-4 py-2 font-semibold text-white">Track this report</Link>
            <button onClick={() => { setDone(null); setDesc(""); setPhoto(null); setConsent(false); }} className="rounded-lg border px-4 py-2">Submit another</button>
          </div>
        </div>
      </AppShell>
    );
  }

  const input = "mt-1 w-full rounded-lg border px-3 py-2";
  return (
    <AppShell title="Community Reporting Portal">
      <form onSubmit={submit} className="mx-auto max-w-2xl space-y-4 rounded-xl bg-white p-6 shadow">
        <p className="text-sm text-slate-600">Report suspicious water conditions. Reports are reviewed by authorised staff and shown on the map only as unverified until checked. Your contact details are never shown publicly.</p>
        <label className="block text-sm font-medium">Problem
          <select value={category} onChange={(e) => setCategory(e.target.value)} className={input}>{categories.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
        <label className="block text-sm font-medium">Water source
          <select value={source} onChange={(e) => setSource(e.target.value)} className={input}>{sources.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium">Locality / area
            <input value={locality} onChange={(e) => setLocality(e.target.value)} maxLength={160} className={input} placeholder="e.g. Kurla West" /></label>
          <label className="block text-sm font-medium">PIN code
            <input value={pin} onChange={(e) => setPin(e.target.value)} inputMode="numeric" maxLength={6} className={input} placeholder="6 digits" /></label>
        </div>
        <div className="text-sm">
          <button type="button" onClick={locate} className="flex items-center gap-1 rounded-lg border border-aqua-500 px-3 py-2 font-semibold text-aqua-600"><Crosshair size={16} />Add my current location (optional)</button>
          {pos && <p className="mt-1 text-slate-600">Location added. It is saved with your report and shown on the public map rounded to about 100 m.</p>}
        </div>
        <label className="block text-sm font-medium">Date and time observed
          <input type="datetime-local" value={observed} max={nowLocal()} onChange={(e) => setObserved(e.target.value)} className={input} required /></label>
        <label className="block text-sm font-medium">Description (optional)
          <textarea value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={2000} rows={3} className={input} placeholder="What did you notice? How many people are affected?" /></label>
        <label className="block text-sm font-medium">Photo (optional, JPEG/PNG/WebP, up to 5 MB)
          <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} className={input} /></label>
        <label className="block text-sm font-medium">Contact (optional, for follow-up only)
          <input value={contact} onChange={(e) => setContact(e.target.value)} maxLength={255} className={input} placeholder="Phone or email" /></label>
        <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1" />
          I agree that this report, and my location if added, may be stored and reviewed by public-health staff. My contact details will not be published.</label>
        {error && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-aqua-500 px-4 py-3 font-semibold text-white hover:bg-aqua-600 disabled:opacity-60">{busy ? "Submitting..." : "Submit report"}</button>
      </form>
    </AppShell>
  );
}