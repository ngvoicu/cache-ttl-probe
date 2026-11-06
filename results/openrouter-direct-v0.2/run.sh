#!/bin/bash
# 2026-11-06: R1 again with probe 0.2.0 (overdue samples are primed again, late checks left out).
# Same request as R1 (direct to OpenRouter, Responses format, top-level cache_control, session_id),
# Haiku instead of Opus: same cache rules, a fraction of the price.
cd ~/Projects/ngvoicu/cpa/cache-ttl-probe
export CACHE_PROBE_KEY=$(python3 -c "
import yaml
c=yaml.safe_load(open('/opt/homebrew/etc/cliproxyapi.conf'))
print(next(k['api-key'] for e in c['api-keys']['openai-compatibility'] if 'openrouter.ai' in e.get('base-url','') for k in e['keys']))")
OUT=results/openrouter-direct-v0.2
nohup node src/cli.ts --base-url https://openrouter.ai/api/v1 --model anthropic/claude-haiku-5.5 --format responses \
  --body-extra '{"cache_control":{"type":"ephemeral"}}' --session-id --ages 2.5m,5m,7.5m,10m \
  --label R1b --concurrency 2 --out $OUT > $OUT/logs/R1b.log 2>&1 &
echo launched
