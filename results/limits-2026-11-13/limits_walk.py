#!/usr/bin/env python3
"""Context limit of a route with as few accepted requests as possible.

    python3 results/limits-2026-11-13/limits_walk.py <model> <out.jsonl> <candidates, largest first> [tol] [timeout_s]

The walk of ../gpt6-2026-11-11/limits_walk.py with the candidate sizes and a time limit given by the caller. It goes
down the candidates; a refusal is free, so it stops at the first accepted size, then halves the gap to the smallest
refused size until it is under tol. A request with no answer inside the time limit is written as a row with
status null and ends the walk: it is neither an acceptance nor a refusal. Rows have the format of harness/limits.py.
"""
import json, sys, time
sys.path.insert(0, "harness")
import limits as L

model, out = sys.argv[1], sys.argv[2]
candidates = [int(x) for x in sys.argv[3].split(",")]
tol = int(sys.argv[4]) if len(sys.argv) > 4 else 8000
limit_s = int(sys.argv[5]) if len(sys.argv) > 5 else 600
fmt = "responses"
log = open(out, "a")


def ask(n):
    text = "Reply with just OK." + " hello" * n
    body = {"model": model, "input": text, "max_output_tokens": 16, "reasoning": {"effort": "low"}}
    started = time.time()
    try:
        code, data, secs = L.post("/v1/responses", body, timeout=limit_s)
    except Exception as err:  # no answer: a time limit or a dropped connection
        code, data, secs = None, {"error": f"no answer in {limit_s} s ({type(err).__name__})"}, time.time() - started
    row = {"kind": "context", "model": model, "n": n, "status": code, "seconds": round(secs, 1),
           "promptTokens": L.prompt_tokens(fmt, data) if code == 200 else None,
           "message": None if code == 200 else L.message(data), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    log.write(json.dumps(row) + "\n"); log.flush(); print(json.dumps(row)[:300], flush=True)
    if code is None:
        sys.exit("no answer: stopping the walk")
    return code == 200


rejected = accepted = None
for n in candidates:
    if ask(n):
        accepted = n
        break
    rejected = n
if accepted is None or rejected is None:
    sys.exit("no boundary found in the candidate range")
while rejected - accepted > tol:
    mid = (accepted + rejected) // 2
    if ask(mid):
        accepted = mid
    else:
        rejected = mid
print(f"RESULT {model}: accepted N={accepted}, rejected N={rejected}", flush=True)
