#!/bin/bash
# Launch the Measurement Matrix through the local CPA. One detached probe process per row.
cd ~/Projects/ngvoicu/cpa/cache-ttl-probe
export CACHE_PROBE_KEY=$(python3 -c "import json;print(json.load(open('~/.pi/agent/cliproxyapi.json'))['apiKey'])")
OUT=results/cpa-8.0.53
run() { # row schedule extra...
  local row=$1 sched=$2; shift 2
  nohup node dist/cli.js --base-url http://127.0.0.1:8317/v1 --model "probe-$(echo $row | tr A-Z a-z)" --label "$row" --concurrency 2 --out $OUT $sched "$@" > $OUT/logs/$row.log 2>&1 &
  sleep 15
}
run C1 "--schedule long"
run C2 "--schedule long"
for r in D1 D2 D3 D4 D6 D7 D8; do run $r "--schedule std"; done
run D5 "--schedule std" --prefix-tokens 5000
run D9 "--schedule long"
run M1 "--schedule std"
run M3 "--schedule std"
run A3 "--schedule std" --prefix-tokens 5000
run O1 "--schedule quick"
run O2 "--schedule long"
run O3 "--schedule long"
run O4 "--schedule std" --prefix-tokens 5000
run O5 "--schedule std" --prefix-tokens 5000
for r in O6 O7 O9 O10; do run $r "--schedule std"; done
run O8 "--schedule long"
run O11 "--schedule quick"
# K1: explicit 1h through CPA on the claude-2 key, with and without the beta header
nohup node dist/cli.js --base-url http://127.0.0.1:8317/v1 --model probe-k1 --format messages --ttl 1h --ages 10m,30m,65m --label K1-nobeta --concurrency 2 --out $OUT > $OUT/logs/K1-nobeta.log 2>&1 &
sleep 15
nohup node dist/cli.js --base-url http://127.0.0.1:8317/v1 --model probe-k1 --format messages --ttl 1h --beta extended-cache-ttl-2025-04-11 --ages 10m,30m,65m --label K1-beta --concurrency 2 --out $OUT > $OUT/logs/K1-beta.log 2>&1 &
echo launched
