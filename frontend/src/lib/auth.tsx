import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { API } from "./api";
export type Role = "citizen" | "healthcare_worker" | "field_inspector" | "administrator";
export type User = { id: string; email: string; full_name: string; role: Role };

export async function apiFetch(path: string, token: string | null, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  return fetch(`${API}${path}`, { ...init, headers });
}

async function errorText(res: Response) {
  try { const j = await res.json(); return Array.isArray(j.detail) ? j.detail.map((d: { message: string }) => d.message).join("; ") : j.error ?? "Request failed"; }
  catch { return "Request failed"; }
}

type Ctx = {
  user: User | null; token: string | null;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string) => Promise<User>;
  logout: () => void;
};
const AuthContext = createContext<Ctx>(null as unknown as Ctx);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  // sessionStorage: the sign-in ends when the browser tab is closed.
  const [token, setToken] = useState<string | null>(sessionStorage.getItem("wg_token"));
  const [user, setUser] = useState<User | null>(() => { try { return JSON.parse(sessionStorage.getItem("wg_user") ?? "null"); } catch { return null; } });

  const save = (t: string | null, u: User | null) => {
    setToken(t); setUser(u);
    if (t && u) { sessionStorage.setItem("wg_token", t); sessionStorage.setItem("wg_user", JSON.stringify(u)); }
    else { sessionStorage.removeItem("wg_token"); sessionStorage.removeItem("wg_user"); }
  };

  useEffect(() => {
    if (!token) return;
    apiFetch("/api/auth/me", token).then(async (r) => { if (r.status === 401) save(null, null); else if (r.ok) setUser(await r.json()); }).catch(() => {});
  }, []); // validate the stored token once on load

  async function authCall(path: string, body: object) {
    let res: Response;
    try { res = await apiFetch(path, null, { method: "POST", body: JSON.stringify(body) }); }
    catch { throw new Error("Could not connect to WaterGuard. In local development, start the backend and open the site through the Vite frontend server; for deployment, configure VITE_API_URL to the backend URL."); }
    if (!res.ok) throw new Error(res.status === 429 ? "Too many attempts. Please wait a minute." : await errorText(res));
    const data = await res.json();
    save(data.access_token, data.user);
    return data.user as User;
  }

  return (
    <AuthContext.Provider value={{
      user, token,
      login: (email, password) => authCall("/api/auth/login", { email, password }),
      register: (full_name, email, password) => authCall("/api/auth/register", { full_name, email, password }),
      logout: () => save(null, null),
    }}>{children}</AuthContext.Provider>
  );
}