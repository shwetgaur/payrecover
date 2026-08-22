import Link from "next/link";

export default function ArchitecturePage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/" className="text-sm text-mute hover:text-white">
        ← Console
      </Link>
      <h1 className="mt-4 text-3xl font-medium">Architecture</h1>
      <p className="mt-3 text-mute">
        PayRecover is a merchant recovery control plane. Razorpay already retries blindly. This agent diagnoses,
        gates, acts once, and writes an audit ledger.
      </p>
      <pre className="mt-8 overflow-auto border border-line bg-panel p-4 font-mono text-xs leading-6">
{`webhook / CSV / sample batch
        │
        ▼
 HMAC + idempotency (event.id)
        │
        ▼
 Normalize → RevenueAtRisk
        │
        ▼
 LangGraph
   diagnose (rules first, Groq rationale)
        │
   policy gate (code, not prompt)
        │
   plan bounded action
        │
   compose EN / Hinglish
        │
   act (simulated adapters)
        │
   observe outcome
        │
        ▼
 Append-only audit ledger  →  merchant console`}
      </pre>
      <h2 className="mt-10 text-xl">Hard stops</h2>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-mute">
        <li>Never retry stolen/fraud/blocked instruments.</li>
        <li>Never auto-debit a revoked mandate.</li>
        <li>WhatsApp only with consent. Quiet hours queue, they do not send.</li>
        <li>LLM never bypasses policy. Groq down still classifies via rules.</li>
      </ul>
      <p className="mt-8 text-sm text-mute">
        Eval on the gold 50: 50/50 class match, 50/50 action in allow-set, 0 policy violations. Headline: 42 valid
        recovery recommendations, 5 human escalate, 3 policy-stop.
      </p>
    </div>
  );
}
