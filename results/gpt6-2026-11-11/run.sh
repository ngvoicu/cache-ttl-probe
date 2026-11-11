#!/bin/bash
# 2026-11-11 12:2x: GPT-6 Astra and Luna on every route of the owner's pools, and the OpenAI API key (new that day).
# G1-G4: pi -> CLIProxyAPI (harness/probe.py, a new pi session per sample, resumed once after the age), pinned with
#   temporary pools probe/gpt-6-* (Codex login, made with harness/pool.py) and devin/gpt-6-* (Devin serves them as is).
# G5-G9: plain HTTP through CLIProxyAPI (the TypeScript probe, Responses format, prompt_cache_key per sample):
#   the OpenAI API key through temporary aliases probe-key/*, OpenRouter by its own model ids.
# Context limits first (limits_walk.py -> limits.jsonl). Backup before: ~/.cli-proxy-api-backups/pre-gpt6-measure-20261111-121633.
cd ~/Projects/ngvoicu/cpa/cache-ttl-probe
OUT=results/gpt6-2026-11-11
AGES=5m,15m,30m,1h,2h
PAGES=5m,15m,30m,40m,1h,2h
export CACHE_PROBE_KEY=$(python3 -c "import json;print(json.load(open('~/.pi/agent/cliproxyapi.json'))['apiKey'])")
B=http://127.0.0.1:8317/v1
go() { nohup caffeinate -i python3 harness/probe.py --label "$1" --out $OUT --ages $AGES --replicas 3 --harness pi "${@:2}" > $OUT/logs/$1.log 2>&1 < /dev/null & sleep 20; }
plain() { nohup caffeinate -i node src/cli.ts --base-url $B --model "$2" --format responses --ages $PAGES --replicas 3 --label "$1" --concurrency 2 --out $OUT > $OUT/logs/$1.log 2>&1 < /dev/null & sleep 15; }
go G1 --model probe/gpt-6-astra
go G2 --model probe/gpt-6-luna
go G3 --model devin/gpt-6-astra
go G4 --model devin/gpt-6-luna
plain G5 probe-key/gpt-6.1-sol
plain G6 probe-key/gpt-6-astra
plain G7 probe-key/gpt-6-luna
plain G8 openai/gpt-6-astra
plain G9 openai/gpt-6-luna
echo launched
