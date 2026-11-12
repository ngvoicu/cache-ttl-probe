#!/bin/bash
# 2026-11-12: GLM 5.3 Flash and DeepSeek V4.1 Flash on OpenRouter, through CLIProxyAPI 8.0.67 with
# router-for-me/CLIProxyAPI#7284 (cache markers and session id for OpenRouter). Plain HTTP (the TypeScript probe,
# Responses format, a prompt_cache_key per sample), OpenRouter's own model ids, 3 samples per age. No config change.
# F1: GLM, the default ~2,500-token prompt: stopped at the control (1,280 of 2,661 tokens cached, under half).
# F2: GLM, ~6,000-token prompt.  F3: DeepSeek, ~6,000-token prompt.
cd "$(dirname "$0")/../.."
OUT=results/openrouter-flash-2026-11-12
AGES=2.5m,5m,7.5m,10m,15m,30m,40m,1h
export CACHE_PROBE_KEY=$(python3 -c "import json;print(json.load(open('$HOME/.pi/agent/cliproxyapi.json'))['apiKey'])")
plain() { nohup caffeinate -i node src/cli.ts --base-url http://127.0.0.1:8317/v1 --model "$2" --format responses --ages $AGES --replicas 3 --label "$1" --concurrency 2 --out $OUT "${@:3}" > $OUT/logs/$1.log 2>&1 < /dev/null & }
case "$1" in
  F1) plain F1 z-ai/glm-5.3-flash ;;
  F2) plain F2 z-ai/glm-5.3-flash --prefix-tokens 6000 ;;
  F3) plain F3 deepseek/deepseek-v4.1-flash --prefix-tokens 6000 ;;
  *) echo "usage: run.sh F1|F2|F3"; exit 1 ;;
esac
echo launched
