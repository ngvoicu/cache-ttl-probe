#!/usr/bin/env python3
"""Context limit of a route with as few accepted (= billed) requests as possible.

Walks down a list of candidate sizes; a rejection is free, so the walk stops at the first accepted size, then
halves the gap to the smallest rejected size until it is under --tol. Rows have the format of harness/limits.py.
"""
import json, sys, time
sys.path.insert(0, "harness")
import limits as L

model, out = sys.argv[1], sys.argv[2]
tol = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
CANDIDATES = [930_000, 915_000, 880_000, 865_000, 510_000, 495_000, 380_000, 365_000, 280_000, 265_000, 130_000]
log = open(out, "a")

def ask(kind, n):
    code, data, secs = L.request("responses", model, n)
    row = {"kind": kind, "model": model, "n": n, "status": code, "seconds": round(secs, 1),
           "promptTokens": L.prompt_tokens("responses", data) if code == 200 else None,
           "message": None if code == 200 else L.message(data), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    log.write(json.dumps(row) + "\n"); log.flush(); print(json.dumps(row)[:260], flush=True)
    return code == 200

rejected = None
accepted = None
for n in CANDIDATES:
    if ask("context", n):
        accepted = n
        break
    rejected = n
if accepted is None or rejected is None:
    sys.exit("no boundary found in the candidate range")
while rejected - accepted > tol:
    mid = (accepted + rejected) // 2
    if ask("context", mid):
        accepted = mid
    else:
        rejected = mid
print(f"RESULT {model}: accepted N={accepted}, rejected N={rejected}", flush=True)
