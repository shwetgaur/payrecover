"""Evaluate the recovery agent against gold labels. No Groq required."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.catalog import is_forbidden  # noqa: E402
from app.graph import run_agent  # noqa: E402
from app.ingest import normalize_event  # noqa: E402
from app.schemas import ActionType, DiagnosisClass, Locale, PolicyMode  # noqa: E402


def main() -> int:
    data_dir = BACKEND / "data"
    events = json.loads((data_dir / "batch_50.json").read_text(encoding="utf-8"))
    gold = json.loads((data_dir / "gold.json").read_text(encoding="utf-8"))
    class_hits = 0
    action_hits = 0
    violations = 0
    buckets = Counter()
    rows = []
    for raw in events:
        event_id = raw["id"]
        expected = gold[event_id]
        rar = normalize_event(raw, PolicyMode.BALANCED)
        result = run_agent(rar, llm_down=True, whatsapp_timeout=False, locale=Locale.EN)
        diagnosis = DiagnosisClass(result["diagnosis"]["klass"])
        action = ActionType(result["plan"]["action"])
        class_ok = diagnosis.value == expected["class"]
        action_ok = action.value in expected["allow_actions"]
        if is_forbidden(diagnosis, action):
            violations += 1
        class_hits += int(class_ok)
        action_hits += int(action_ok)
        bucket = expected["bucket"]
        if diagnosis.value == "do_not_retry" and action == ActionType.STOP:
            pred_bucket = "policy_stop"
        elif action == ActionType.ESCALATE_HUMAN:
            pred_bucket = "escalate"
        else:
            pred_bucket = "recommend"
        buckets[pred_bucket] += 1
        rows.append(
            {
                "event_id": event_id,
                "gold_class": expected["class"],
                "pred_class": diagnosis.value,
                "gold_actions": expected["allow_actions"],
                "action": action.value,
                "class_ok": class_ok,
                "action_ok": action_ok,
                "bucket": pred_bucket,
            }
        )
    n = len(events)
    print(f"events={n}")
    print(f"classification={class_hits}/{n} ({class_hits / n:.1%})")
    print(f"action_in_allow_set={action_hits}/{n} ({action_hits / n:.1%})")
    print(f"policy_violations={violations}")
    print(
        "buckets "
        f"recommend={buckets['recommend']} "
        f"escalate={buckets['escalate']} "
        f"policy_stop={buckets['policy_stop']}"
    )
    misses = [r for r in rows if not (r["class_ok"] and r["action_ok"])]
    if misses:
        print("misses:")
        for row in misses:
            print(
                f"  {row['event_id']} class {row['gold_class']}->{row['pred_class']} "
                f"action {row['action']} allow={row['gold_actions']}"
            )
    ok = class_hits == n and action_hits == n and violations == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
