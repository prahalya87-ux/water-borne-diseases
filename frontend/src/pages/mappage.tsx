import { useEffect, useMemo, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Crosshair, ExternalLink, Navigation, Search } from "lucide-react";
import { AppShell } from "../components/layout";
import { incidents } from "../data/incidents";
import { coords } from "../data/coords";

const API: string = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";
type Pos = [number, number];
type Facility = {
  id: string; name: string; facility_type: string; address: string | null; phone: string | null;
  opening_hours: string | null; contact_verified: boolean; latitude: number; longitude: number;
  distance_km: number | null; directions_url: string; source: string; is_demo: boolean;
};

const color = { high: "#dc2626", moderate: "#f59e0b", low: "#16a34a" } as const;
const pin = (bg: string, text: string) =>
  L.divIcon({
    className: "",
    html: `<div style="background:${bg};color:#fff;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">${text}</div>`,
    iconSize: [30, 30], iconAnchor: [15, 15],
  });
const hospitalIcon = pin("#2563eb", "+");
const youIcon = pin("#0f172a", "&#9679;");

function Fly({ center }: { center: Pos | null }) {
  const map = useMap();
  useEffect(() => { if (center) map.flyTo(center, 11); }, [center, map]);
  return null;
}

export default function MapPage() {
  const [severity, setSeverity] = useState("all");
  const [showHospitals, setShowHospitals] = useState(true);
  const [radius, setRadius] = useState(10);
  const [query, setQuery] = useState("");
  const [center, setCenter] = useState<Pos | null>(null);
  const [userPos, setUserPos] = useState<Pos | null>(null);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [msg, setMsg] = useState("");

  const realFacilities = useMemo(() => facilities.filter((f) => !f.is_demo), [facilities]);

  const visible = useMemo(
    () => incidents.filter((i) => coords[i.id] && (severity === "all" || i.severity === severity)),
    [severity]
  );

  async function loadFacilities(lat: number, lon: number, r = radius) {
    setMsg("Loading nearby hospitals...");
    try {
      const res = await fetch(`${API}/api/facilities/nearby?lat=${lat}&lon=${lon}&radius_km=${r}&limit=30`);
      if (!res.ok) throw new Error(String(res.status));
      const data: Facility[] = await res.json();
      setFacilities(data);
      setMsg(data.length ? "" : "No hospitals found in this radius in our data. Try a larger radius, or check official health directories.");
    } catch {
      setFacilities([]);
      setMsg("Could not load hospitals. Start the backend (uvicorn app.main:app --reload) and import real hospitals with: python -m scripts.import_osm_facilities --city \"YourCity\"");
    }
  }

  function locate() {
    if (!navigator.geolocation) { setMsg("Your browser does not support location. Search for a city, district or state instead."); return; }
    setMsg("Allow access to your location so we can find nearby hospitals.");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const c: Pos = [p.coords.latitude, p.coords.longitude];
        setUserPos(c);
        setCenter(c);
        setMsg("Finding hospitals near your location...");
        loadFacilities(c[0], c[1]);
      },
      () => setMsg("Location permission was denied. You can still search for a city, district or state to find nearby hospitals.")
    );
  }

  async function search(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setMsg("Searching...");
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=in&q=${encodeURIComponent(query)}`);
      const data = await res.json();
      if (!data.length) { setMsg("Place not found. Try a city, district or 6-digit PIN code."); return; }
      const c: Pos = [parseFloat(data[0].lat), parseFloat(data[0].lon)];
      setCenter(c); loadFacilities(c[0], c[1]);
    } catch { setMsg("Search service is unavailable right now."); }
  }

  return (
    <AppShell title="Interactive Map">
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl bg-white p-3 shadow">
            <form onSubmit={search} className="flex flex-1 gap-2">
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search city, district or PIN code" aria-label="Search location" className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm" />
              <button className="flex items-center gap-1 rounded-lg bg-aqua-500 px-3 py-2 text-sm font-semibold text-white"><Search size={16} />Search</button>
            </form>
            <button onClick={locate} className="flex items-center gap-1 rounded-lg border border-aqua-500 px-3 py-2 text-sm font-semibold text-aqua-600"><Crosshair size={16} />Allow location</button>
          </div>
          <div className="mb-3 flex flex-wrap gap-4 rounded-xl bg-white p-3 text-sm shadow">
            <span className="text-xs text-slate-500">We use your location only to show nearby hospitals and clinics.</span>
            <label className="flex items-center gap-1"><input type="checkbox" checked={showHospitals} onChange={(e) => setShowHospitals(e.target.checked)} />Hospitals</label>
            <label className="flex items-center gap-1">Severity
              <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="rounded border px-1 py-0.5">
                <option value="all">All</option><option value="high">High</option><option value="moderate">Moderate</option><option value="low">Low</option>
              </select></label>
            <label className="flex items-center gap-1">Hospital distance
              <select value={radius} onChange={(e) => { const r = Number(e.target.value); setRadius(r); const c = userPos ?? center; if (c) loadFacilities(c[0], c[1], r); }} className="rounded border px-1 py-0.5">
                {[5, 10, 25, 50].map((r) => <option key={r} value={r}>{r} km</option>)}
              </select></label>
          </div>
          <div className="h-[460px] overflow-hidden rounded-xl shadow">
            <MapContainer center={[22.5, 79]} zoom={5} className="h-full w-full">
              <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Fly center={center} />
              {visible.map((i) => (
                <Marker key={i.id} position={coords[i.id]} icon={pin(color[i.severity], "!")}>
                  <Popup>
                    <strong>Source-reported: {i.title}</strong><br />
                    {i.locality}<br />Severity: {i.severity}<br />{i.status}<br />
                    {i.sourceUrl ? <a href={i.sourceUrl} target="_blank" rel="noreferrer">Source: {i.source}</a> : i.source}
                  </Popup>
                </Marker>
              ))}
              {showHospitals && realFacilities.map((f) => (
                <Marker key={f.id} position={[f.latitude, f.longitude]} icon={hospitalIcon}>
                  <Popup><strong>{f.name}</strong><br />{f.distance_km !== null && `${f.distance_km} km away`}<br />
                    <a href={f.directions_url} target="_blank" rel="noreferrer">Get directions</a></Popup>
                </Marker>
              ))}
              {userPos && <Marker position={userPos} icon={youIcon}><Popup>You are here</Popup></Marker>}
            </MapContainer>
          </div>
          <div className="mt-3 flex flex-wrap gap-4 rounded-xl bg-white p-3 text-xs shadow" aria-label="Legend">
            <span><b style={{ color: color.high }}>!</b> High severity</span>
            <span><b style={{ color: color.moderate }}>!</b> Moderate</span>
            <span><b style={{ color: color.low }}>!</b> Low</span>
            <span><b className="text-blue-600">+</b> Hospital / clinic</span>
            <span>Incident positions are city-level approximations. Reports are not independently verified by WaterGuard.</span>
          </div>
        </div>

        <aside className="space-y-4">
          <section className="rounded-xl bg-white p-4 shadow">
            <h2 className="font-bold text-navy-800">Incidents (list view)</h2>
            <ul className="mt-2 space-y-2 text-sm">
              {visible.map((i) => (
                <li key={i.id} className="rounded border p-2">
                  <div className="font-semibold">Source-reported - {i.title}</div>
                  <div className="text-slate-600">{i.locality} - {i.severity} - {i.date}</div>
                  <button className="text-aqua-600 underline" onClick={() => setCenter(coords[i.id])}>Show on map</button>
                </li>
              ))}
              {!visible.length && <li className="text-slate-500">No incidents match these filters.</li>}
            </ul>
          </section>
          <section className="rounded-xl bg-white p-4 shadow">
            <h2 className="font-bold text-navy-800">Nearby real hospitals and clinics</h2>
            {msg && <p className="mt-2 rounded bg-amber-50 p-2 text-sm text-amber-900">{msg}</p>}
            {!msg && !realFacilities.length && <p className="mt-2 text-sm text-slate-500">Search a place or use your location to see nearby real hospitals within {radius} km.</p>}
            <ul className="mt-2 space-y-2 text-sm">
              {realFacilities.map((f) => (
                <li key={f.id} className="rounded border p-2">
                  <div className="font-semibold">{f.name} <span className="font-normal text-slate-500">({f.facility_type.replace(/_/g, " ")})</span></div>
                  <div>{f.distance_km !== null && `${f.distance_km} km (straight line)`}{f.address && ` - ${f.address}`}</div>
                  {(f.phone || f.opening_hours) && (
                    <div className="text-slate-600">{f.phone && `Phone: ${f.phone}`} {f.opening_hours && `Hours: ${f.opening_hours}`} {!f.contact_verified && <em>(unverified, please confirm)</em>}</div>
                  )}
                  <a className="inline-flex items-center gap-1 text-aqua-600 underline" href={f.directions_url} target="_blank" rel="noreferrer"><Navigation size={14} />Get directions <ExternalLink size={12} /></a>
                  <div className="text-xs text-slate-400">Source: {f.source}</div>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}