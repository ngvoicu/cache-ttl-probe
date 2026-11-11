#!/bin/bash
# 2026-11-06 23:3x: Codex subscription cache lifetimes up to 12 h (probe 0.2.0), all GPT models the account serves.
# 6.1 Sol / Terra are pools in the real CPA, so they are pinned to Codex through temporary aliases
# probe/gpt-6.1-* on the Codex login (backup pre-codex-probe-aliases-*; remove the aliases afterwards).
# (GPT-6 Sol / Astra / Luna were started and stopped: the owner needs only 6.1.) Devin was out of daily quota, so not measured here.
cd "$(dirname "$0")/../.."
export CACHE_PROBE_KEY=$(python3 -c "import json;print(json.load(open('$HOME/.pi/agent/cliproxyapi.json'))['apiKey'])")
OUT=results/cpa-codex-long-2026-11-06
B=http://127.0.0.1:8317/v1
AGES=5m,15m,30m,1h,2h,3h,4h,6h,8h,10h,12h
run() { nohup node src/cli.ts --base-url $B --model "$2" --format responses --ages $AGES --label "$1" --concurrency 2 --out $OUT > $OUT/logs/$1.log 2>&1 & sleep 30; }
run X1 probe/gpt-6.1-sol
run X2 probe/gpt-6.1-terra
echo launched
# X2 (Terra) was cold at 5 min: finer ages
# nohup node src/cli.ts --base-url $B --model probe/gpt-6.1-terra --format responses --ages 1m,2m,3m,4m,5m,7.5m --label X2b --concurrency 2 --out $OUT
