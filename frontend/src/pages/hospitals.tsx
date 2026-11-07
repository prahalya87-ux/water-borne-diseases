import { useEffect, useRef, useState } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { AlertTriangle, Crosshair, ExternalLink, Navigation, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/layout";
import { API } from "../lib/api";

type Position = [number, number];
type Facility = {
  id: string;
  name: string;
  facility_type: string;
  address: string | null;
  phone: string | null;
  opening_hours: string | null;
  contact_verified: boolean;
  latitude: number;
  longitude: number;
  distance_km: number | null;
  beds: number | null;
  directions_url: string;
  source: string;
  is_demo: boolean;
};

function isFacility(value: unknown): value is Facility {
  if (typeof value !== "object" || value === null) return false;
  const facility = value as Record<string, unknown>;
  return typeof facility.id === "string"
    && typeof facility.name === "string"
    && typeof facility.facility_type === "string"
    && (facility.address === null || typeof facility.address === "string")
    && (facility.phone === null || typeof facility.phone === "string")
    && (facility.opening_hours === null || typeof facility.opening_hours === "string")
    && typeof facility.contact_verified === "boolean"
    && typeof facility.latitude === "number" && Number.isFinite(facility.latitude)
    && typeof facility.longitude === "number" && Number.isFinite(facility.longitude)
    && (facility.distance_km === null || typeof facility.distance_km === "number")
    && (facility.beds === null || typeof facility.beds === "number")
    && typeof facility.directions_url === "string"
    && typeof facility.source === "string"
    && typeof facility.is_demo === "boolean";
}

const hospitalIcon = L.divIcon({
  className: "",
  html: '<div style="background:#2563eb;color:#fff;width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">+</div>',
  iconSize: [30, 30],
  iconAnchor: [15, 15],
});
const userIcon = L.divIcon({
  className: "",
  html: '<div style="background:#0f172a;color:#fff;width:18px;height:18px;border-radius:50%;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

function MapCenter({ center }: { center: Position | null }) {
  const map = useMap();
  useEffect(() => {
    if (center) map.flyTo(center, 13);
  }, [center, map]);
  return null;
}

function FitFacilities({ facilities, userPosition }: { facilities: Facility[]; userPosition: Position | null }) {
  const map = useMap();
  useEffect(() => {
    const points: Position[] = facilities.map((facility) => [facility.latitude, facility.longitude]);
    if (userPosition) points.push(userPosition);
    if (points.length) map.fitBounds(points, { padding: [30, 30], maxZoom: 13 });
  }, [facilities, map, userPosition]);
  return null;
}

function googleMapsHospitalSearch(position: Position | null, place: string) {
  const query = position
    ? `hospitals near ${position[0]},${position[1]}`
    : place.trim() ? `hospitals near ${place.trim()}` : "";
  return query ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}` : null;
}

export default function Hospitals() {
  const [radius, setRadius] = useState(10);
  const [query, setQuery] = useState("");
  const [center, setCenter] = useState<Position | null>(null);
  const [userPosition, setUserPosition] = useState<Position | null>(null);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const requestId = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const mapsSearchUrl = googleMapsHospitalSearch(center, query);

  useEffect(() => () => activeRequest.current?.abort(), []);

  function beginRequest() {
    activeRequest.current?.abort();
    activeRequest.current = null;
    requestId.current += 1;
    return requestId.current;
  }

  async function loadHospitals(position: Position, distance: number, currentRequest: number) {
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setBusy(true);
    setMessage("Searching source-listed hospitals near this location...");
    try {
      const params = new URLSearchParams({
        lat: String(position[0]),
        lon: String(position[1]),
        radius_km: String(distance),
        limit: "50",
        facility_type: "hospital",
      });
      setCenter(position);
      const response = await fetch(`${API}/api/facilities/nearby?${params}`, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(response.status === 503
          ? "Live hospital listings are temporarily unavailable. Please try again shortly."
          : `Hospital search failed (${response.status}). Please try again.`);
      }
      const data: unknown = await response.json();
      if (!Array.isArray(data) || !data.every(isFacility)) {
        throw new Error("Hospital search returned an invalid response. Please try again.");
      }
      if (currentRequest !== requestId.current) return;
      const realFacilities = data.filter((facility) => !facility.is_demo);
      setFacilities(realFacilities);
      setMessage(realFacilities.length
        ? ""
        : `No hospital listings were found within ${distance} km. Directory coverage may be incomplete; try a larger radius or another nearby place.`);
    } catch (error) {
      if (currentRequest !== requestId.current) return;
      setFacilities([]);
      setMessage(error instanceof DOMException && error.name === "AbortError"
        ? ""
        : error instanceof TypeError
          ? "Could not connect to the hospital service. Start the backend and open the site through Vite (which proxies /api), or configure VITE_API_URL for your deployed API."
        : error instanceof Error ? error.message : "Could not load nearby hospitals. Please try again.");
    } finally {
      if (currentRequest === requestId.current) {
        activeRequest.current = null;
        setBusy(false);
      }
    }
  }

  function requestLocation() {
    const currentRequest = beginRequest();
    setCenter(null);
    setQuery("");
    setUserPosition(null);
    setFacilities([]);
    if (!navigator.geolocation) {
      setMessage("Your browser does not support location. Search for a city, district, state or PIN code instead.");
      setBusy(false);
      return;
    }
    setBusy(true);
    setMessage("Please allow location access in your browser to find nearby hospitals.");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (currentRequest !== requestId.current) return;
        const position: Position = [coords.latitude, coords.longitude];
        setUserPosition(position);
        setCenter(position);
        void loadHospitals(position, radius, currentRequest);
      },
      (error) => {
        if (currentRequest !== requestId.current) return;
        setMessage(error.code === error.PERMISSION_DENIED
          ? "Location access was denied. You can still search for a city, district, state or PIN code."
          : error.code === error.TIMEOUT
            ? "Location lookup timed out. Try again or search for a place."
            : "Could not get your location. Check your device location settings or search for a place.");
        setBusy(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  }

  async function searchPlace(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const place = query.trim();
    if (!place) return;
    const currentRequest = beginRequest();
    setBusy(true);
    setMessage("Searching for location...");
    setFacilities([]);
    setCenter(null);
    setUserPosition(null);
    const controller = new AbortController();
    activeRequest.current = controller;
    try {
      const params = new URLSearchParams({ format: "json", limit: "1", countrycodes: "in", q: place });
      const response = await fetch(`https://nominatim.openstreetmap.org/search?${params}`, { signal: controller.signal });
      if (!response.ok) throw new Error("Location search is unavailable. Please try again.");
      const results: { lat: string; lon: string; display_name: string }[] = await response.json();
      if (currentRequest !== requestId.current) return;
      if (!results.length) {
        setMessage("Place not found. Try a city, district, state or PIN code in India.");
        return;
      }
      const position: Position = [Number(results[0].lat), Number(results[0].lon)];
      if (!position.every(Number.isFinite)) throw new Error("Location search returned invalid coordinates. Try another place.");
      setCenter(position);
      await loadHospitals(position, radius, currentRequest);
    } catch (error) {
      if (currentRequest === requestId.current) {
        setMessage(error instanceof DOMException && error.name === "AbortError"
          ? ""
          : error instanceof Error ? error.message : "Location search is unavailable. Please try again.");
      }
    } finally {
      if (currentRequest === requestId.current) {
        activeRequest.current = null;
        setBusy(false);
      }
    }
  }

  return (
    <AppShell title="Nearby Hospitals">
      <div className="mx-auto max-w-6xl space-y-5">
        <section className="rounded-xl bg-white p-4 shadow">
          <h2 className="text-lg font-bold text-navy-800">Find nearby hospitals for water-related illness</h2>
          <p className="mt-1 text-sm text-slate-600">
            Search source-labelled hospital listings near your location or a place you choose. Results are ordered by straight-line distance; use Directions for a road route.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={requestLocation} disabled={busy} className="flex items-center gap-2 rounded-lg bg-aqua-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
              <Crosshair size={16} /> Use my location
            </button>
            <form onSubmit={searchPlace} className="flex min-w-[min(100%,20rem)] flex-1 gap-2">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search a city, district, state or PIN code"
                aria-label="Search a city, district, state or PIN code"
                className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm"
              />
              <button disabled={busy} className="flex items-center gap-1 rounded-lg border border-aqua-500 px-3 py-2 text-sm font-semibold text-aqua-700 disabled:opacity-60">
                <Search size={16} /> Search
              </button>
            </form>
            <label className="flex items-center gap-2 text-sm">
              Radius
              <select
                value={radius}
                onChange={(event) => {
                  const nextRadius = Number(event.target.value);
                  setRadius(nextRadius);
                  if (center) void loadHospitals(center, nextRadius, beginRequest());
                }}
                className="rounded-lg border px-2 py-2"
              >
                {[5, 10, 25, 50].map((distance) => <option key={distance} value={distance}>{distance} km</option>)}
              </select>
            </label>
          </div>
          {message && (
            <div role="status" aria-live="polite" className={`mt-3 rounded-lg p-3 text-sm ${/failed|unavailable|could not|invalid/i.test(message) ? "bg-red-50 text-red-800" : "bg-amber-50 text-amber-900"}`}>
              <p>{message}</p>
              {(center || query.trim()) && (
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
                  {center && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void loadHospitals(center, radius, beginRequest())}
                      className="font-semibold underline disabled:opacity-60"
                    >
                      Retry directory search
                    </button>
                  )}
                  {mapsSearchUrl && (
                    <a href={mapsSearchUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold underline">
                      Search hospitals on Google Maps <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              )}
              {mapsSearchUrl && /unavailable|failed|could not/i.test(message) && (
                <p className="mt-2 text-xs">The external map search is a fallback and is not verified by this directory. Confirm the facility and its emergency services before travelling when possible.</p>
              )}
            </div>
          )}
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
            <h2 className="flex items-center gap-2 font-bold text-navy-800"><AlertTriangle size={18} className="text-blue-700" />When to seek urgent care</h2>
            <p className="mt-2 text-sm text-slate-700">Seek prompt medical help for severe or persistent diarrhoea or vomiting, blood in stool, signs of dehydration (very little urine, extreme thirst, drowsiness), high fever, or jaundice. Infants, older adults and pregnant people may become seriously ill faster.</p>
            <p className="mt-2 text-xs text-slate-600">For a life-threatening emergency, contact your local emergency service. Do not delay urgent care to use this directory.</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="font-bold text-navy-800">What these listings can confirm</h2>
            <p className="mt-2 text-sm text-slate-700">Map data identifies hospitals; it does not confirm current emergency availability or treatment for cholera, typhoid, hepatitis, or dehydration. Call ahead when possible and ask whether the facility can assess your symptoms. Facility contact details may be missing or out of date.</p>
            <Link to="/diseases" className="mt-2 inline-flex text-sm font-semibold text-aqua-700 underline">Read about waterborne diseases and care</Link>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="h-[460px] overflow-hidden rounded-xl shadow" aria-label="Map of nearby hospitals" aria-busy={busy}>
            <MapContainer center={[22.5, 79]} zoom={5} className="h-full w-full">
              <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <MapCenter center={center} />
              <FitFacilities facilities={facilities} userPosition={userPosition} />
              {facilities.map((facility) => (
                <Marker key={facility.id} position={[facility.latitude, facility.longitude]} icon={hospitalIcon}>
                  <Popup>
                    <strong>{facility.name}</strong><br />
                    {facility.distance_km !== null && `${facility.distance_km} km away`}<br />
                    <a href={facility.directions_url} target="_blank" rel="noreferrer">Get directions</a>
                  </Popup>
                </Marker>
              ))}
              {userPosition && <Marker position={userPosition} icon={userIcon}><Popup>You are here</Popup></Marker>}
            </MapContainer>
          </section>

          <section className="rounded-xl bg-white p-4 shadow">
            <h2 className="font-bold text-navy-800">Nearby hospitals{facilities.length > 0 && <span className="ml-2 text-sm font-normal text-slate-500">{facilities.length} found</span>}</h2>
            {!message && !facilities.length && <p className="mt-3 text-sm text-slate-500">Allow location access or search for a place to see nearby hospitals.</p>}
            {facilities.length > 0 && (
              <ul className="mt-3 max-h-[420px] space-y-2 overflow-y-auto">
                {facilities.map((facility) => (
                  <li key={facility.id} className="rounded-lg border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-slate-800">{facility.name}</h3>
                      {facility.distance_km !== null && (
                        <span className="shrink-0 rounded-full bg-cyan-50 px-2 py-1 text-sm font-semibold text-cyan-800">
                          {facility.distance_km} km
                        </span>
                      )}
                    </div>
                    <a className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-aqua-700 underline" href={facility.directions_url} target="_blank" rel="noreferrer">
                      <Navigation size={14} /> Get directions in Google Maps <ExternalLink size={12} />
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
        <p className="text-xs text-slate-500">Hospital names and locations come from OpenStreetMap and may be incomplete or out of date. Distances are straight-line estimates. Google Maps opens directions from your selected location to the hospital.</p>
      </div>
    </AppShell>
  );
}
