#!/bin/bash
# 2026-11-06 ~23:50: latest models of other vendors through the real CPA, probe 0.2.0.
# OpenRouter entry (CPA with #7284: cache markers, session id): Gemini 4 Argon, Kimi K3.1 Pro, DeepSeek V4.1 Flash,
# 2 samples per age to keep the cost near $0.35. Muse Wonder on the Meta login (subscription), 3 samples.
# Devin (Gemini 4 Argon, Muse Wonder, Claude 5.5, GPT-6.1 Terra) waits for its daily quota.
cd ~/Projects/ngvoicu/cpa/cache-ttl-probe
export CACHE_PROBE_KEY=$(python3 -c "import json;print(json.load(open('~/.pi/agent/cliproxyapi.json'))['apiKey'])")
OUT=results/cpa-latest-2026-11-06
B=http://127.0.0.1:8317/v1
AGES=2.5m,5m,10m,15m,30m,1h,2h
run() { nohup node src/cli.ts --base-url $B --model "$2" --format responses --ages $AGES --replicas $3 --label "$1" --concurrency 2 --out $OUT > $OUT/logs/$1.log 2>&1 & sleep 20; }
run L1 google/gemini-4-argon 2
run L2 moonshotai/kimi-k3.1-pro 2
run L3 deepseek/deepseek-v4.1-flash 2
run L4 muse-wonder-1.0 3
echo launched
# L1 (Gemini 4 Argon) had no cached re-send with the ~2.3k prompt: again with 8k (Gemini's minimum cacheable size)
# nohup node src/cli.ts --base-url $B --model google/gemini-4-argon --format responses --prefix-tokens 8000 --ages $AGES --replicas 2 --label L1b --concurrency 2 --out $OUT
