"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { api, inr, type CaseRow, type Faults, type RunOut } from "@/lib/api";

function Kpi({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "gain" | "risk";
}) {
  const color = tone === "gain" ? "text-gain" : tone === "risk" ? "text-risk" : "text-white";
  return (
    <div className="border border-line bg-panel px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.14em] text-mute">{label}</div>
      <div className={`mt-1 font-mono text-2xl ${color}`}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-mute">{hint}</div> : null}
    </div>
  );
}

function Badge({ children, tone }: { children: string; tone?: "gain" | "risk" | "warn" | "mute" }) {
  const map = {
    gain: "text-gain border-gain/40",
    risk: "text-risk border-risk/40",
    warn: "text-warn border-warn/40",
    mute: "text-mute border-line",
  };
  return (
    <span className={`border px-1.5 py-0.5 font-mono text-[10px] uppercase ${map[tone || "mute"]}`}>{children}</span>
  );
}

export default function ConsolePage() {
  const [policy, setPolicy] = useState("balanced");
  const [locale, setLocale] = useState("en");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunOut | null>(null);
  const [selected, setSelected] = useState<CaseRow | null>(null);
  const [faults, setFaults] = useState<Faults>({ llm: "up", whatsapp: "ok" });
  const [msgLang, setMsgLang] = useState<"en" | "hinglish">("en");

  const cases = run?.cases || [];
  const metrics = run?.metrics;

  const buckets = useMemo(() => {
    const m: Record<string, number> = {};
    for (const row of cases) m[row.bucket || "other"] = (m[row.bucket || "other"] || 0) + 1;
    return m;
  }, [cases]);

  async function runBatch() {
    setBusy(true);
    setError(null);
    try {
      const out = await api.run(policy, locale);
      setRun(out);
      setSelected(out.cases?.[0] || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleLlm() {
    const next = faults.llm === "up" ? "down" : "up";
    setFaults(await api.setFaults({ llm: next }));
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-line px-6 py-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.2em] text-mute">Track 03 · AI Revenue Recovery</div>
          <h1 className="text-lg font-medium">PayRecover</h1>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <Link className="text-mute hover:text-white" href="/architecture">
            Architecture
          </Link>
          <button
            onClick={toggleLlm}
            className={`border px-3 py-1 font-mono text-xs ${faults.llm === "down" ? "border-warn text-warn" : "border-line text-mute"}`}
          >
            LLM {faults.llm === "down" ? "DOWN · rules fallback" : "UP"}
          </button>
        </div>
      </header>

      <main className="grid grid-cols-1 gap-6 px-6 py-6 xl:grid-cols-[1.4fr_1fr]">
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <p className="max-w-xl text-sm text-mute">
              Diagnose failed payments. Recover the ones that should come back. Stop the ones that should not.
            </p>
            <div className="flex items-center gap-2">
              <select value={policy} onChange={(e) => setPolicy(e.target.value)} className="border border-line bg-ink px-2 py-1 text-sm">
                <option value="conservative">conservative</option>
                <option value="balanced">balanced</option>
                <option value="aggressive">aggressive</option>
              </select>
              <select value={locale} onChange={(e) => setLocale(e.target.value)} className="border border-line bg-ink px-2 py-1 text-sm">
                <option value="en">English</option>
                <option value="hinglish">Hinglish</option>
              </select>
              <button
                onClick={runBatch}
                disabled={busy}
                className="bg-accent px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
              >
                {busy ? "Running…" : "Run recovery on sample batch (50)"}
              </button>
            </div>
          </div>

          {error ? <div className="border border-risk/50 bg-risk/10 px-3 py-2 text-sm text-risk">{error}</div> : null}

          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <Kpi label="Rs at risk" value={metrics ? inr(metrics.at_risk_paise) : "—"} tone="risk" />
            <Kpi label="Rs recovered" value={metrics ? inr(metrics.recovered_paise) : "—"} hint="Simulated on gold batch" tone="gain" />
            <Kpi label="Valid recs" value={metrics ? String(metrics.recommended_count) : "—"} hint={`${buckets.recommend || 0} recommend`} />
            <Kpi label="Human escalate" value={metrics ? String(metrics.escalated_count) : "—"} />
            <Kpi label="Policy stop" value={metrics ? String(metrics.stopped_count) : "—"} />
          </div>

          <div className="border border-line">
            <div className="flex items-center justify-between border-b border-line px-3 py-2 text-xs uppercase tracking-wider text-mute">
              <span>Cases</span>
              <span>{metrics?.policy_violations ?? 0} policy violations</span>
            </div>
            <div className="max-h-[520px] overflow-auto">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-panel text-[11px] uppercase text-mute">
                  <tr>
                    <th className="px-3 py-2">Event</th>
                    <th className="px-3 py-2">Method</th>
                    <th className="px-3 py-2">Diagnosis</th>
                    <th className="px-3 py-2">Action</th>
                    <th className="px-3 py-2">Outcome</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((row) => (
                    <tr
                      key={row.id}
                      onClick={() => setSelected(row)}
                      className={`cursor-pointer border-t border-line hover:bg-white/5 ${selected?.id === row.id ? "bg-white/5" : ""}`}
                    >
                      <td className="px-3 py-2 font-mono text-xs">{row.event_id}</td>
                      <td className="px-3 py-2">{row.method}</td>
                      <td className="px-3 py-2">{row.diagnosis_class}</td>
                      <td className="px-3 py-2">{row.action}</td>
                      <td className="px-3 py-2">
                        <Badge
                          tone={
                            row.outcome === "recovered"
                              ? "gain"
                              : row.bucket === "policy_stop"
                                ? "risk"
                                : row.bucket === "escalate"
                                  ? "warn"
                                  : "mute"
                          }
                        >
                          {row.outcome || row.bucket || "—"}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-right font-mono">{inr(row.amount_paise)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <aside className="border border-line bg-panel">
          {!selected ? (
            <div className="p-6 text-sm text-mute">Run the sample batch, then open a case. The audit trail is the product.</div>
          ) : (
            <div className="flex h-full flex-col">
              <div className="border-b border-line px-4 py-3">
                <div className="font-mono text-xs text-mute">{selected.event_id}</div>
                <div className="mt-1 flex flex-wrap gap-2">
                  <Badge>{selected.diagnosis_class || "—"}</Badge>
                  <Badge tone={selected.bucket === "policy_stop" ? "risk" : selected.bucket === "escalate" ? "warn" : "gain"}>
                    {selected.action || "—"}
                  </Badge>
                  {selected.degraded ? <Badge tone="warn">degraded</Badge> : null}
                </div>
              </div>
              <div className="space-y-4 overflow-auto p-4 text-sm">
                <p className="text-mute">{selected.diagnosis_rationale}</p>
                {selected.policy_reasons?.length ? (
                  <div>
                    <div className="text-[11px] uppercase tracking-wider text-mute">Policy</div>
                    <ul className="mt-1 space-y-1 font-mono text-xs">
                      {selected.policy_reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <div>
                  <div className="flex items-center justify-between">
                    <div className="text-[11px] uppercase tracking-wider text-mute">Customer message</div>
                    <button className="text-xs text-accent" onClick={() => setMsgLang(msgLang === "en" ? "hinglish" : "en")}>
                      {msgLang}
                    </button>
                  </div>
                  <p className="mt-2 border border-line bg-ink p-3 text-sm">
                    {msgLang === "en" ? selected.message_en : selected.message_hinglish}
                  </p>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-mute">Audit trail</div>
                  <ol className="mt-2 space-y-2">
                    {selected.audit.map((entry, i) => (
                      <li key={`${entry.ts}-${i}`} className="border-l border-line pl-3">
                        <div className="font-mono text-[11px] text-mute">
                          {entry.actor} · {entry.event_type} · {entry.severity}
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}
