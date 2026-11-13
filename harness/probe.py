#!/usr/bin/env python3
"""Cache-lifetime probe through real coding harnesses (Codex CLI, Devin CLI, Muse Code, pi).

Each sample starts a new harness session whose first message carries a unique block of ~N tokens, then, after a fixed
age, resumes that session with a short message and reads the cached-token count the harness reports. Harnesses share a
large system prompt between sessions, so a check is warm only when the cache covers the shared part *and* at least half
of the sample's unique block: cached >= baseline + unique / 2, where baseline is the prompt size of a session without
the block (measured once at start). One check per sample, like the TypeScript probe in src/.

Usage:
  harness/probe.py --harness codex|devin|muse|pi --model ID --ages 5m,15m,1h --replicas 3 --label H1 --out DIR
"""
import argparse, glob, heapq, json, os, random, subprocess, sys, threading, time, uuid
from datetime import datetime, timezone

OK_PROMPT = "Reply with OK only. Do not use any tools."


def parse_age(s):
    s = s.strip()
    if s.endswith("h"): return float(s[:-1]) * 3600
    if s.endswith("m"): return float(s[:-1]) * 60
    if s.endswith("s"): return float(s[:-1])
    return float(s)


def unique_block(salt, words):
    rnd = random.Random(salt)
    cons, vows = "bcdfghjklmnprstvz", "aeiou"
    out = []
    for _ in range(words):
        out.append("".join(rnd.choice(cons) + rnd.choice(vows) for _ in range(rnd.randint(2, 4))))
    return " ".join(out)


def prime_prompt(salt, words):
    return (f"Reference document {salt}, keep it for later. Do not use any tools. Reply with OK only.\n\n<doc>\n"
            + unique_block(salt, words) + "\n</doc>")


def run(cmd, cwd, timeout=600, env=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


class Codex:
    cumulative = True  # `codex exec resume --json` reports the thread's running total, not the last turn
    def __init__(s, a, work): s.a, s.work = a, work
    def _usage(s, out):
        tid, u = None, None
        for l in out.splitlines():
            try: d = json.loads(l)
            except Exception: continue
            if d.get("type") == "thread.started": tid = d.get("thread_id")
            if d.get("type") == "turn.completed": u = d.get("usage")
        if not u: raise RuntimeError("no usage: " + out[-300:])
        return tid, {"total": u.get("input_tokens", 0), "cached": u.get("cached_input_tokens", 0),
                     "write": u.get("cache_write_input_tokens", 0)}
    def _base(s): return ["--json", "--skip-git-repo-check", "-m", s.a.model, "-c", f'model_reasoning_effort="{s.a.effort}"']
    def start(s, prompt):
        rc, out, err = run(["codex", "exec", *s._base(), "-s", "read-only", prompt], s.work)
        return s._usage(out)
    def resume(s, h, prompt):
        rc, out, err = run(["codex", "exec", "resume", h, *s._base(), prompt], s.work)
        return s._usage(out)[1]


class Muse:
    def __init__(s, a, work): s.a, s.work = a, work
    def _go(s, sid, prompt):
        rc, out, err = run(["muse", "exec", "--json", "--model", s.a.model, "--reasoning-effort", s.a.effort,
                            "--session-id", sid, prompt], s.work)
        u = None
        for l in out.splitlines():
            try: d = json.loads(l)
            except Exception: continue
            if d.get("payload_type") == "run.usage": u = d["payload"]
        if not u: raise RuntimeError("no usage: " + (err or out)[-300:])
        ms = u.get("models") or []
        return {"total": sum(m.get("input_tokens", 0) for m in ms), "cached": sum(m.get("cached_tokens", 0) for m in ms),
                "write": 0, "calls": u.get("calls")}
    def start(s, prompt):
        sid = str(uuid.uuid4()); return sid, s._go(sid, prompt)
    def resume(s, h, prompt): return s._go(h, prompt)


class Devin:
    def __init__(s, a, work): s.a, s.work = a, work
    def _usage(s, f):
        d = json.load(open(f))
        st = [x for x in d.get("steps", []) if x.get("metrics")]
        if not st: raise RuntimeError("no metrics in export")
        m = st[-1]["metrics"]
        return d["session_id"], {"total": m.get("prompt_tokens", 0), "cached": m.get("cached_tokens", 0),
                                 "write": (m.get("extra") or {}).get("cache_creation_input_tokens", 0),
                                 "model": st[-1].get("model_name")}
    def _go(s, extra, prompt):
        f = os.path.join(s.work, f"export-{uuid.uuid4().hex[:10]}.json")
        pf = f + ".prompt"; open(pf, "w").write(prompt)
        rc, out, err = run(["devin", *extra, "--prompt-file", pf, "-p", "--respect-workspace-trust", "false",
                            "--export", f], s.work)
        os.remove(pf)
        if not os.path.exists(f): raise RuntimeError(f"no export rc={rc}: " + (err or out)[-300:])
        r = s._usage(f); os.remove(f); return r
    def start(s, prompt): return s._go(["--model", s.a.model], prompt)
    def resume(s, h, prompt): return s._go(["-r", h], prompt)[1]


class Pi:
    def __init__(s, a, work): s.a, s.work = a, work; s.sd = os.path.join(work, "pi-sessions"); os.makedirs(s.sd, exist_ok=True)
    def _go(s, sid, prompt):
        rc, out, err = run(["pi", "-p", "--session-dir", s.sd, "--session-id", sid, "--model", "cliproxyapi/" + s.a.model,
                            "--thinking", s.a.effort, prompt], s.work)
        fs = glob.glob(os.path.join(s.sd, f"*_{sid}.jsonl"))
        if not fs: raise RuntimeError(f"no session rc={rc}: " + (err or out)[-300:])
        last = None
        for l in open(fs[0]):
            d = json.loads(l); m = d.get("message") or {}
            if m.get("role") == "assistant": last = m
        if not last or last.get("stopReason") == "error":
            raise RuntimeError("pi error: " + str((last or {}).get("errorMessage"))[:300])
        u = last.get("usage") or {}
        return {"total": u.get("input", 0) + u.get("cacheRead", 0) + u.get("cacheWrite", 0), "cached": u.get("cacheRead", 0),
                "write": u.get("cacheWrite", 0), "api": last.get("api")}
    def start(s, prompt):
        sid = "hp-" + uuid.uuid4().hex[:12]; return sid, s._go(sid, prompt)
    def resume(s, h, prompt): return s._go(h, prompt)


HARNESSES = {"codex": Codex, "muse": Muse, "devin": Devin, "pi": Pi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--harness", required=True, choices=HARNESSES)
    ap.add_argument("--model", required=True)
    ap.add_argument("--ages", required=True)
    ap.add_argument("--replicas", type=int, default=3)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--words", type=int, default=3000, help="unique block size in words (~2 tokens each)")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--checkers", type=int, default=1)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    work = os.path.abspath(os.path.join(a.out, f"work-{a.label}")); os.makedirs(work, exist_ok=True)
    h = HARNESSES[a.harness](a, work)
    salt = uuid.uuid4().hex[:8]
    path = os.path.join(a.out, f"{a.label}.jsonl")
    lock = threading.Lock()

    def log(ev):
        ev["at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with lock:
            with open(path, "a") as f: f.write(json.dumps(ev) + "\n")
            print(json.dumps(ev), flush=True)

    def attempt(fn, *args):
        for i in range(3):
            try: return fn(*args)
            except Exception as e:
                log({"event": "retry", "error": str(e)[:300], "try": i + 1}); time.sleep(30)
        return None

    log({"event": "start", "harness": a.harness, "model": a.model, "ages": a.ages, "replicas": a.replicas,
         "words": a.words, "effort": a.effort, "salt": salt})
    b = attempt(h.start, OK_PROMPT)
    if not b: log({"event": "abort", "reason": "baseline failed"}); return
    baseline = b[1]["total"]
    log({"event": "baseline", "usage": b[1]})

    ages = [parse_age(x) for x in a.ages.split(",")]
    samples = [("control", 30.0, 0)] + [(x, ag, r) for r in range(a.replicas) for x, ag in zip(a.ages.split(","), ages)]
    # long ages first, so the short checks do not wait behind a long priming queue
    samples = [samples[0]] + sorted(samples[1:], key=lambda s: -s[1])
    heap, hlock, cv = [], threading.Lock(), threading.Condition()
    pending = [len(samples)]

    def checker():
        while True:
            with cv:
                while True:
                    if not heap and pending[0] == 0: return
                    if heap and heap[0][0] <= time.time(): item = heapq.heappop(heap); break
                    cv.wait(timeout=5)
            due, n, name, age, handle, prime, t0 = item
            r = attempt(h.resume, handle, OK_PROMPT)
            real = time.time() - t0
            if r and getattr(h, "cumulative", False):
                r = dict(r, raw={k: r[k] for k in ("total", "cached", "write")},
                         **{k: r[k] - prime.get(k, 0) for k in ("total", "cached", "write")})
            if r:
                unique = max(prime["total"] - baseline, 1)
                warm = r["cached"] >= baseline + unique / 2
                log({"event": "check", "age": name, "ageSec": age, "realAgeSec": round(real), "late": real > age * 1.1 + 90,
                     "warm": warm, "usage": r, "prime": prime, "unique": unique, "handle": handle})
            else:
                log({"event": "check-failed", "age": name, "handle": handle})
            with cv:
                pending[0] -= 1; cv.notify_all()

    threads = [threading.Thread(target=checker, daemon=True) for _ in range(a.checkers)]
    for t in threads: t.start()
    for i, (name, age, rep) in enumerate(samples):
        r = attempt(h.start, prime_prompt(f"{salt}-{i}", a.words))
        if not r:
            log({"event": "prime-failed", "age": name})
            with cv: pending[0] -= 1; cv.notify_all()
            continue
        handle, prime = r
        t0 = time.time()
        log({"event": "prime", "age": name, "rep": rep, "handle": handle, "usage": prime})
        with cv:
            heapq.heappush(heap, (t0 + age, i, name, age, handle, prime, t0)); cv.notify_all()
    for t in threads: t.join()
    log({"event": "done"})


if __name__ == "__main__":
    main()
