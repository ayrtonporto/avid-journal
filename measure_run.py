"""Measure an AViD /api/analyze run end-to-end: per-stage/per-block timings,
errors, and final verdicts. Streams the SSE and prints a timeline + summary.

Usage (server must already be running via run_local_demo.ps1):
    python measure_run.py                      # provider=claude-code, tiny example
    python measure_run.py <path.tex> <provider>
"""
import sys, time, json, re
import requests  # in the repo venv

BASE = "http://127.0.0.1:7860"
TEX = sys.argv[1] if len(sys.argv) > 1 else r"examples\tiny_even_numbers\paper.tex"
PROVIDER = sys.argv[2] if len(sys.argv) > 2 else "claude-code"

t0 = time.time()
def ts(): return time.time() - t0

print(f"POST {BASE}/api/analyze  file={TEX}  provider={PROVIDER}\n")

data = {"provider": PROVIDER, "model": ""}
with open(TEX, "rb") as fh:
    files = {"file": (TEX.split("\\")[-1], fh)}
    r = requests.post(f"{BASE}/api/analyze", data=data, files=files, stream=True, timeout=3600)
    r.raise_for_status()

# Track phase/block transitions to compute durations.
last_label = None
last_label_t = 0.0
durations = []       # (label, seconds)
errors = []          # (ts, msg)
verdicts = []        # final results
final = None

def close_label(now):
    global last_label, last_label_t
    if last_label is not None:
        durations.append((last_label, now - last_label_t))

for raw in r.iter_lines(decode_unicode=True):
    if not raw or not raw.startswith("data:"):
        continue
    try:
        d = json.loads(raw[5:].strip())
    except Exception:
        continue
    step = d.get("step", "")
    msg = d.get("msg", "")
    now = ts()

    if d.get("type") == "result" or step in ("result", "done") or "results" in d:
        final = d
        continue

    # A "label" = phase + block header (strip the round/heartbeat detail).
    m = re.match(r"(Formalizing \[\d+/\d+\][^—-]*|Checking novelty \[\d+/\d+\][^·]*|Starting[^—]*)", msg)
    label = (m.group(1).strip() if m else step)

    if step == "heartbeat":
        continue  # noise; durations come from label transitions

    if "error" in msg.lower() or "Lean errors" in msg:
        errors.append((now, msg[:120]))

    if label != last_label:
        close_label(now)
        last_label = label
        last_label_t = now
        print(f"[+{now:6.1f}s] {label[:80]}")

close_label(ts())

print("\n================ SUMMARY ================")
print(f"total wall time: {ts():.1f}s\n")
print("per-stage durations:")
for lbl, dur in durations:
    print(f"  {dur:7.1f}s  {lbl[:70]}")
print(f"\nerrors/retries seen: {len(errors)}")
for t, m in errors[:20]:
    print(f"  [+{t:6.1f}s] {m}")
if final:
    print("\nfinal payload (verdicts):")
    print(json.dumps(final, indent=2, ensure_ascii=False)[:2000])
