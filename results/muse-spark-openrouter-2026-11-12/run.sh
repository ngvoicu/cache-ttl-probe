#!/bin/bash
# 2026-11-12: Muse Spark 1.3 on OpenRouter, through CLIProxyAPI 8.0.67 with router-for-me/CLIProxyAPI#7284
# (cache markers and session id for OpenRouter). Plain HTTP (the TypeScript probe, Responses format, a
# prompt_cache_key per sample), OpenRouter's own model id, 3 samples per age. No config change.
cd "$(dirname "$0")/../.."
OUT=results/muse-spark-openrouter-2026-11-12
export CACHE_PROBE_KEY=$(python3 -c "import json;print(json.load(open('$HOME/.pi/agent/cliproxyapi.json'))['apiKey'])")
nohup caffeinate -i node src/cli.ts --base-url http://127.0.0.1:8317/v1 --model meta/muse-spark-1.3 --format responses \
  --ages 2.5m,5m,7.5m,10m,15m,30m,40m,1h --replicas 3 --label S1 --concurrency 2 --out $OUT > $OUT/logs/S1.log 2>&1 < /dev/null &
echo launched
