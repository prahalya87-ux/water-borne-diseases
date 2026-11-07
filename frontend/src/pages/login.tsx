import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppShell } from "../components/layout";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (mode === "register" && password.length < 8) return setError("Password must be at least 8 characters.");
    setBusy(true);
    try {
      const u = mode === "login" ? await login(email.trim(), password) : await register(name.trim(), email.trim(), password);
      nav(u.role === "administrator" || u.role === "field_inspector" ? "/admin" : "/");
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  const input = "mt-1 w-full rounded-lg border px-3 py-2";
  return (
    <AppShell title={mode === "login" ? "Sign in" : "Create account"}>
      <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-xl bg-white p-6 shadow">
        {mode === "register" && (
          <label className="block text-sm font-medium">Full name
            <input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} className={input} autoComplete="name" /></label>
        )}
        <label className="block text-sm font-medium">Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className={input} autoComplete="email" /></label>
        <label className="block text-sm font-medium">Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className={input} autoComplete={mode === "login" ? "current-password" : "new-password"} /></label>
        {error && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-aqua-500 px-4 py-2 font-semibold text-white hover:bg-aqua-600 disabled:opacity-60">{busy ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }} className="w-full text-sm text-aqua-600 underline">
          {mode === "login" ? "New here? Create an account" : "Already have an account? Sign in"}
        </button>
        <p className="text-xs text-slate-500">New accounts are citizen accounts. Administrator and inspector access is granted only by an administrator.</p>
      </form>
    </AppShell>
  );
}