#!/usr/bin/env python3
"""Measure a route's real context window and output limit through CPA.

Context: prompts of " hello" x N (one token each on the tested tokenizers), binary search on N between --lo and --hi
until the accepted and rejected sizes are within --tol tokens. A rejection that names the limit ("... > 1000000
maximum") ends the search early. Only accepted requests cost quota; each asks for a 16-token reply.

Output: one request with a huge max_tokens; the error usually names the maximum. Free when rejected.

Every request is appended to --out as JSON lines. Usage tokens come from the response, so the reported window is the
provider's own count (prompt tokens incl. the small wrapper), not N.
"""
import argparse, json, re, sys, time, urllib.request, urllib.error

KEY = json.load(open("~/.pi/agent/cliproxyapi.json"))["apiKey"]
BASE = "http://127.0.0.1:8317"


def post(path, body, timeout=600):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json",
                                          "anthropic-version": "2023-06-01"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}"), time.time() - t
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw), time.time() - t
        except Exception:
            return e.code, {"raw": raw[:2000]}, time.time() - t


def request(fmt, model, n, max_tokens=16, effort="low"):
    text = "Reply with just OK." + " hello" * n
    if fmt == "messages":
        body = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": text}]}
        return post("/v1/messages", body)
    if fmt == "responses":
        body = {"model": model, "input": text, "max_output_tokens": max_tokens, "reasoning": {"effort": effort}}
        return post("/v1/responses", body)
    body = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": text}]}
    return post("/v1/chat/completions", body)


def prompt_tokens(fmt, data):
    u = data.get("usage") or {}
    if fmt == "messages":
        return (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
    return u.get("input_tokens") or u.get("prompt_tokens") or 0


def message(data):
    err = data.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err)
    return str(err or data.get("raw") or data)[:600]


LIMIT_PATTERNS = [
    r"\d[\d,]*\s*>\s*(\d[\d,]*),?\s*which is the maximum",          # Anthropic output: max_tokens: 10000000 > 128000, which is the maximum
    r"(\d[\d,]*)\s*tokens?\s*>\s*(\d[\d,]*)\s*maximum",          # Anthropic: prompt is too long: 1000123 tokens > 1000000 maximum
    r"maximum context length is\s*(\d[\d,]*)",                    # OpenAI-style
    r"context (?:window|length) (?:of|is)\s*(\d[\d,]*)",
    r"max(?:imum)?[^0-9]{0,40}(\d[\d,]{3,})",
]


def named_limit(msg):
    for pat in LIMIT_PATTERNS:
        m = re.search(pat, msg, re.I)
        if m:
            return int(m.groups()[-1].replace(",", ""))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--format", choices=["messages", "responses", "chat"], required=True)
    ap.add_argument("--lo", type=int, required=True, help="N expected to be accepted")
    ap.add_argument("--hi", type=int, required=True, help="N expected to be rejected")
    ap.add_argument("--tol", type=int, default=2000)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-output", action="store_true", help="skip the output-limit check")
    ap.add_argument("--no-confirm", action="store_true", help="when the error names the limit, don't send an accepted request")
    a = ap.parse_args()
    log = open(a.out, "a")

    def rec(kind, n, code, data, secs, extra=None):
        row = {"kind": kind, "model": a.model, "n": n, "status": code, "seconds": round(secs, 1),
               "promptTokens": prompt_tokens(a.format, data) if code == 200 else None,
               "message": None if code == 200 else message(data), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if extra:
            row.update(extra)
        log.write(json.dumps(row) + "\n"); log.flush()
        print(json.dumps(row)[:400], flush=True)
        return row

    if not a.no_output:
        code, data, secs = request(a.format, a.model, 10, max_tokens=10_000_000)
        r = rec("output", 10, code, data, secs)
        if code != 200:
            lim = named_limit(r["message"] or "")
            print(f"OUTPUT LIMIT named: {lim}", flush=True)

    lo, hi = a.lo, a.hi
    lo_tokens = None
    # Make sure hi is rejected; the rejection may name the window.
    code, data, secs = request(a.format, a.model, hi)
    r = rec("context", hi, code, data, secs)
    if code == 200:
        print("hi was accepted; raise --hi", flush=True)
        return
    named = named_limit(r["message"] or "")
    if named:
        print(f"CONTEXT LIMIT named: {named}", flush=True)
        if a.no_confirm:
            return
        # Confirm just under the named limit. The error's own count gives the tokens per " hello" (2 on Claude's
        # tokenizer); keep ~1k tokens of room for the wrapper and the reply.
        counted = re.search(r"(\d[\d,]*)\s*tokens?\s*>", r["message"] or "")
        per = int(counted.group(1).replace(",", "")) / hi if counted else 1.0
        n = int((named - 1000) / per)
        code, data, secs = request(a.format, a.model, n)
        rec("confirm", n, code, data, secs, {"named": named})
        return
    while hi - lo > a.tol:
        mid = (lo + hi) // 2
        code, data, secs = request(a.format, a.model, mid)
        r = rec("context", mid, code, data, secs)
        if code == 200:
            lo, lo_tokens = mid, r["promptTokens"]
        elif code in (400, 413, 422) or "context" in (r["message"] or "").lower() or "too long" in (r["message"] or "").lower():
            hi = mid
            n2 = named_limit(r["message"] or "")
            if n2:
                print(f"CONTEXT LIMIT named: {n2}", flush=True)
        else:
            print(f"unexpected status {code}; stopping", flush=True)
            return
    print(f"CONTEXT: accepted N={lo} ({lo_tokens} prompt tokens), rejected N={hi}", flush=True)


if __name__ == "__main__":
    main()
