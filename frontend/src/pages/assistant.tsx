import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Send, Siren } from "lucide-react";
import { AppShell } from "../components/layout";
import { apiFetch } from "../lib/auth";

type Msg = { role: "user" | "bot"; text: string; emergency?: boolean; links?: { label: string; to: string }[]; notes?: string[] };
const suggestions = [
  "What precautions should I take if my water source may be contaminated?",
  "How do I interpret a water-quality report?",
  "What are the common signs of waterborne illness?",
  "How can I report contaminated water?",
  "Where can I find nearby hospitals?",
  "What should I do during a local water-safety advisory?",
  "What should I do if I have watery diarrhoea and vomiting?",
  "How do I prepare ORS safely?",
  "What should I do after flooding?",
  "How can I prevent typhoid?",
  "How do I care for dehydration from diarrhoea?",
];

export default function Assistant() {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "bot", text: "Hi, I'm the WaterGuard Assistant. I can answer general questions about safe water, water-quality reports and water-related illness. I cannot diagnose illness. In an emergency, call 112 or go to the nearest hospital." }]);
  const [text, setText] = useState("");
  const [locality, setLocality] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function send(q: string) {
    const message = q.trim();
    if (!message || busy) return;
    setMsgs((m) => [...m, { role: "user", text: message }]); setText(""); setBusy(true);
    try {
      const res = await apiFetch("/api/assistant/chat", null, { method: "POST", body: JSON.stringify({ message, locality: locality.trim() || null }) });
      if (res.status === 429) throw new Error("You are sending messages too quickly. Please wait a moment.");
      if (!res.ok) throw new Error("The assistant could not answer that. Please try again.");
      const d = await res.json();
      setMsgs((m) => [...m, { role: "bot", text: d.answer, emergency: d.emergency, links: d.links, notes: [...(d.context_notes ?? []), d.disclaimer] }]);
    } catch (e) {
      const offline = e instanceof TypeError;
      setMsgs((m) => [...m, { role: "bot", text: offline ? "I could not reach the WaterGuard backend. Start it with: uvicorn app.main:app --reload" : (e as Error).message }]);
    } finally { setBusy(false); }
  }

  return (
    <AppShell title="AI Assistant">
      <div className="mx-auto grid max-w-5xl gap-4 lg:grid-cols-3">
        <div className="flex h-[70vh] flex-col rounded-xl bg-white shadow lg:col-span-2">
          <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
            {msgs.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex"}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${m.role === "user" ? "bg-aqua-500 text-white" : m.emergency ? "border-2 border-red-400 bg-red-50 text-red-900" : "bg-slate-100"}`}>
                  {m.emergency && <p className="mb-1 flex items-center gap-1 font-bold"><Siren size={16} />Possible emergency</p>}
                  <p>{m.text}</p>
                  {m.links && m.links.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{m.links.map((l) => <Link key={l.to} to={l.to} className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-aqua-600 underline">{l.label}</Link>)}</div>}
                  {m.notes?.map((n, k) => <p key={k} className="mt-2 border-t pt-1 text-xs text-slate-600">{n}</p>)}
                </div>
              </div>
            ))}
            {busy && <p className="text-sm text-slate-500">Thinking...</p>}
            <div ref={end} />
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(text); }} className="flex gap-2 border-t p-3">
            <input value={text} onChange={(e) => setText(e.target.value)} maxLength={500} placeholder="Ask about water safety..." aria-label="Your question" className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm" />
            <button disabled={busy} className="flex items-center gap-1 rounded-lg bg-aqua-500 px-4 py-2 font-semibold text-white disabled:opacity-60"><Send size={16} />Send</button>
          </form>
        </div>
        <aside className="space-y-4">
          <section className="rounded-xl bg-white p-4 shadow">
            <h2 className="font-bold text-navy-800">Suggested questions</h2>
            <div className="mt-2 flex flex-col gap-2">{suggestions.map((s) => <button key={s} onClick={() => send(s)} className="rounded-lg border px-3 py-2 text-left text-sm hover:bg-cyan-50">{s}</button>)}</div>
          </section>
          <section className="rounded-xl bg-white p-4 text-sm shadow">
            <h2 className="font-bold text-navy-800">Your area (optional)</h2>
            <p className="mt-1 text-slate-600">Add an area name so answers can mention published alerts for it.</p>
            <input value={locality} onChange={(e) => setLocality(e.target.value)} maxLength={160} placeholder="e.g. Kurla" aria-label="Your area" className="mt-2 w-full rounded-lg border px-3 py-2" />
          </section>
          <p className="rounded-xl bg-white p-4 text-xs text-slate-500 shadow">Answers come from a curated knowledge base. Conversations are not saved. The assistant never reports live local conditions it does not have.</p>
        </aside>
      </div>
    </AppShell>
  );
}