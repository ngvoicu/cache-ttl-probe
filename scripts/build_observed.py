#!/usr/bin/env python3
"""Build observed.json: every published measurement in one machine-readable file.

    python3 scripts/build_observed.py           # write observed.json
    python3 scripts/build_observed.py --check   # fail if observed.json is out of date

observed/manifest.json says which raw files count and what each one measured (route, model, request
options). Everything else in observed.json (dates, counts per age, the summary numbers) is computed here
from the raw files under results/, so the file can't drift from the data.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = "observed/manifest.json"
OUT = "observed.json"

ROUTES = {
    "anthropic-api": "Anthropic API key",
    "claude-subscription": "Claude Pro/Max login (the Claude Code subscription)",
    "codex-subscription": "ChatGPT plan through the Codex login",
    "devin": "Devin subscription",
    "meta-subscription": "Muse Code subscription key on Meta's Model API",
    "openai-api": "OpenAI API key",
    "openrouter": "OpenRouter API key",
    "antigravity": "Google Antigravity login",
}
CLIENTS = {
    "pi+cliproxyapi": "the pi coding agent through CLIProxyAPI: real sessions, resumed once (harness/probe.py)",
    "cliproxyapi": "plain HTTP requests through CLIProxyAPI (the TypeScript probe)",
    "direct": "plain HTTP requests straight to the vendor (the TypeScript probe)",
    "codex-cli": "OpenAI's Codex CLI (harness/probe.py)",
    "devin-cli": "the Devin CLI (harness/probe.py)",
    "muse-code": "Meta's Muse Code CLI (harness/probe.py)",
}
HARNESS_CLIENT = {"pi": "pi+cliproxyapi", "codex": "codex-cli", "devin": "devin-cli", "muse": "muse-code"}
UNIT = {"s": 1, "m": 60, "h": 3600}


def age_seconds(label):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([smh])", label)
    if not m:
        raise ValueError(f"bad age {label!r}")
    return round(float(m.group(1)) * UNIT[m.group(2)])


def age_label(seconds):
    for unit, size in (("h", 3600), ("m", 60)):
        if seconds % size == 0:
            return f"{seconds // size}{unit}"
        if unit == "m" and seconds % 30 == 0 and seconds >= 60:
            return f"{seconds / 60:g}m"
    return f"{seconds}s"


def read_harness(path):
    """harness/probe.py event log: one JSON object per line."""
    rows = [json.loads(line) for line in open(os.path.join(ROOT, path)) if line.strip()]
    start = next(r for r in rows if r["event"] == "start")
    control, checks, late = [], {}, 0
    for r in rows:
        if r["event"] != "check":
            continue
        if r["age"] == "control":
            control.append(bool(r["warm"]))
        elif r.get("late"):
            late += 1
        else:
            checks.setdefault(age_seconds(r["age"]), []).append(bool(r["warm"]))
    return {
        "client": HARNESS_CLIENT[start["harness"]],
        "date": start["at"][:10],
        "started": start["at"],
        "control": control,
        "checks": checks,
        "late": late,
        "effort": start.get("effort"),
    }


def read_plain(path):
    """Result file of the TypeScript probe."""
    j = json.load(open(os.path.join(ROOT, path)))
    checks, late = {}, 0
    for c in j.get("checks", []):
        if c.get("error"):
            continue
        target = c["targetAgeMs"]
        # The probe's own rule (src/run.ts lateAfterMs); 0.1.0 files carry no flag, so apply it here.
        if c.get("late") or c["actualAgeMs"] - target > max(30_000, round(target * 0.1)):
            late += 1
            continue
        checks.setdefault(round(target / 1000), []).append(bool(c["warm"]))
    control = [bool(j["control"]["warm"])] if j.get("control") else []
    return {
        "date": j["startedAt"][:10],
        "started": j["startedAt"],
        "control": control,
        "checks": checks,
        "late": late,
        "probe_version": j.get("probeVersion"),
    }


def summarize(checks):
    """all_warm_through_s: the largest age up to which every age tested was fully warm (the safe value).
    last_warm_s: the largest age with any warm check. first_all_cold_s: the smallest age with none."""
    ages = sorted(checks)
    through = None
    for age in ages:
        if all(checks[age]):
            through = age
        else:
            break
    warm_ages = [a for a in ages if any(checks[a])]
    cold_ages = [a for a in ages if not any(checks[a])]
    return {
        "all_warm_through_s": through,
        "last_warm_s": max(warm_ages) if warm_ages else None,
        "first_all_cold_s": min(cold_ages) if cold_ages else None,
    }


def build_cache(manifest):
    entries = []
    for run in manifest["runs"]:
        path = run["file"]
        data = read_harness(path) if path.endswith(".jsonl") else read_plain(path)
        client = run.get("client") or data["client"]
        if client not in CLIENTS or run["route"] not in ROUTES:
            raise SystemExit(f"{run['id']}: unknown client or route")
        options = dict(run.get("options") or {})
        if data.get("effort") and "reasoning" not in options:
            options["reasoning"] = data["effort"]
        entry = {
            "id": run["id"],
            "route": run["route"],
            "client": client,
            "model": run["model"],
            "models_dev": run.get("models_dev"),
            "base_model": run.get("base_model"),
            "options": options,
            "date": data["date"],
            "source": path,
            "control": {"warm": sum(data["control"]), "total": len(data["control"])},
            "checks": [
                {"age": age_label(age), "age_s": age, "warm": sum(v), "total": len(v)}
                for age, v in sorted(data["checks"].items())
            ],
            "late_excluded": data["late"],
            **summarize(data["checks"]),
        }
        for key in ("requires", "lacks", "note", "continues"):
            if run.get(key):
                entry[key] = run[key]
        entry["_started"] = data["started"]
        entry["_checks"] = data["checks"]
        entries.append(entry)

    # "continues": a run that adds checks to an earlier one (older ages, or more samples of an age; same route,
    # client, model and options). Its `checks` and its three summary numbers then cover the earlier run too, and the
    # runs that one continues, so the entry stays consistent in itself for a reader that doesn't know the field (a
    # run with only cold, old ages would otherwise read as "never cached").
    by_id = {e["id"]: e for e in entries}
    for e in sorted(entries, key=lambda e: e["_started"]):
        e["_merged"] = e["_checks"]
        if "continues" not in e:
            continue
        base = by_id.get(e["continues"])
        same = base and all(base[k] == e[k] for k in ("route", "client", "model", "options"))
        if not same or "_merged" not in base:
            raise SystemExit(f"{e['id']}: continues {e['continues']}, which is missing, differs, or started later")
        merged = {age: list(v) for age, v in base["_merged"].items()}
        for age, v in e["_checks"].items():
            merged.setdefault(age, []).extend(v)
        e["_merged"] = merged
        e["checks"] = [{"age": age_label(age), "age_s": age, "warm": sum(v), "total": len(v)} for age, v in sorted(merged.items())]
        e.update(summarize(merged))

    # "latest": the newest run of the same route, client, model and options.
    newest = {}
    for e in entries:
        key = (e["route"], e["client"], e["model"], json.dumps(e["options"], sort_keys=True))
        if key not in newest or e["_started"] > newest[key]["_started"]:
            newest[key] = e
    for e in entries:
        key = (e["route"], e["client"], e["model"], json.dumps(e["options"], sort_keys=True))
        e["latest"] = newest[key] is e
        del e["_started"], e["_checks"], e["_merged"]
    entries.sort(key=lambda e: (e["route"], e["model"], e["client"], e["date"], e["id"]))
    return entries


def check_evidence(rows, item):
    """Every number in a limits entry must be backed by a row of the raw limits file."""
    for ev in item["evidence"]:
        model = ev["row_model"]
        mine = [r for r in rows if r.get("model") == model]
        if "accepted" in ev:
            ok = any(r.get("status") == 200 and r.get("promptTokens") == ev["accepted"] for r in mine)
        elif "refused_n" in ev:
            ok = any(r.get("status") != 200 and r.get("n") == ev["refused_n"] for r in mine)
        elif "refused_kind" in ev:
            ok = any(r.get("status") != 200 and r.get("kind") == ev["refused_kind"] for r in mine)
        elif "output_step" in ev:
            ok = any(r.get("status") == 200 and r.get("maxTokens") == ev["output_step"] for r in mine)
        elif "message_has" in ev:
            ok = any(ev["message_has"] in (r.get("message") or "") for r in mine)
        elif "ctx_message_has" in ev:
            ok = any(ev["ctx_message_has"] in str((r.get("ctx") or ["", ""])[1]) for r in mine)
        else:
            ok = False
        if not ok:
            raise SystemExit(f"limits {item['route']} {item['model']}: no raw row backs {ev}")


def build_limits(manifest):
    files = {}
    out = []
    for item in manifest["limits"]:
        path = item.get("file") or manifest["limits_file"]
        if path not in files:
            files[path] = [json.loads(line) for line in open(os.path.join(ROOT, path)) if line.strip()]
        check_evidence(files[path], item)
        entry = {k: v for k, v in item.items() if k not in ("evidence", "file")}
        entry.setdefault("models_dev", None)
        entry["source"] = path
        out.append(entry)
    out.sort(key=lambda e: (e["route"], e["model"]))
    return out


def build_known(manifest):
    """Lifetimes that follow from how requests are built (not measured): passed through after a shape check."""
    out = []
    for item in manifest.get("known", []):
        if item.get("route") not in ROUTES or item.get("client") not in CLIENTS:
            raise SystemExit(f"known: unknown route or client in {item}")
        if not isinstance(item.get("ttl_s"), int) or not item.get("basis") or not item.get("source") or not item.get("model"):
            raise SystemExit(f"known: ttl_s, model, basis and source are required in {item}")
        out.append(item)
    return out


def build():
    manifest = json.load(open(os.path.join(ROOT, MANIFEST)))
    return {
        "schema": 1,
        "repository": "https://github.com/ngvoicu/groundtruth",
        "about": "Prompt-cache lifetimes and limits as measured, not as documented. Built from results/ by "
                 "scripts/build_observed.py; see README.md, section 'observed.json'.",
        "routes": ROUTES,
        "clients": CLIENTS,
        "cache": build_cache(manifest),
        "limits": build_limits(manifest),
        "known": build_known(manifest),
        "excluded": manifest["excluded"],
    }


def main():
    text = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    target = os.path.join(ROOT, OUT)
    if "--check" in sys.argv:
        current = open(target).read() if os.path.exists(target) else ""
        if current != text:
            raise SystemExit(f"{OUT} is out of date: run python3 scripts/build_observed.py")
        print(f"{OUT} is up to date")
        return
    open(target, "w").write(text)
    data = json.loads(text)
    print(f"wrote {OUT}: {len(data['cache'])} cache runs, {len(data['limits'])} limits")


if __name__ == "__main__":
    main()
