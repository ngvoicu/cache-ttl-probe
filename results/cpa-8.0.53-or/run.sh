#!/bin/bash
# 2026-11-06: OpenRouter caching through the local CPA after #7284 (cache markers, session id, levels).
# Real models through the OpenRouter openai-compatibility entry; nothing in the CPA config changes.
cd "$(dirname "$0")/../.."
export CACHE_PROBE_KEY=$(python3 -c "import json;print(json.load(open('$HOME/.pi/agent/cliproxyapi.json'))['apiKey'])")
OUT=results/cpa-8.0.53-or
B=http://127.0.0.1:8317/v1
nohup node dist/cli.js --base-url $B --model anthropic/claude-haiku-5.5 --format messages --schedule std --label P1 --concurrency 2 --out $OUT > $OUT/logs/P1.log 2>&1 &
sleep 20
nohup node dist/cli.js --base-url $B --model anthropic/claude-haiku-5.5 --format messages --ttl 1h --ages 10m,30m,65m --label P2 --concurrency 2 --out $OUT > $OUT/logs/P2.log 2>&1 &
sleep 20
nohup node dist/cli.js --base-url $B --model openai/gpt-6.1-sol --format responses --ages 30m,1h,2h,4h,8h,12h --body-extra '{"prompt_cache_options":{"ttl":"12h"}}' --label P3 --concurrency 2 --out $OUT > $OUT/logs/P3.log 2>&1 &
echo launched
