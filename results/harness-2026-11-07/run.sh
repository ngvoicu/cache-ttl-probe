#!/bin/bash
# 2026-11-07: cache lifetimes through the vendors' own harnesses vs pi through CPA, same account and model.
# harness/probe.py: unique ~7k-token block per session, check = resume after the age; warm = cache covers the shared
# harness prompt + half the unique block. Effort low everywhere.
# pi -> CPA routes are pinned with TEMPORARY single-member pools (cliproxyapi.conf, pools list) and the temporary
# Codex aliases probe/gpt-6.1-*; backup ~/.cli-proxy-api-backups/pre-harness-probe-20261107-141138. Remove afterwards.
cd ~/Projects/ngvoicu/cpa/cache-ttl-probe
OUT=results/harness-2026-11-07
LONG=5m,15m,30m,1h,2h,4h,6h,8h,10h,12h
SHORT=2.5m,5m,10m,15m,30m,1h,2h
DEV=5m,30m,1h,2h,4h,6h,8h,12h
GPT=5m,15m,30m,45m,1h,2h
go() { nohup python3 harness/probe.py --label "$1" --out $OUT "${@:2}" > $OUT/logs/$1.log 2>&1 & sleep 15; }
go H1  --harness codex --model gpt-6.1-sol              --ages $LONG  --replicas 3
go H2  --harness pi    --model probe/gpt-6.1-sol        --ages $LONG  --replicas 3
go H3  --harness codex --model gpt-6.1-terra            --ages $LONG  --replicas 3
go H4  --harness pi    --model probe/gpt-6.1-terra      --ages $LONG  --replicas 3
go H5  --harness muse  --model muse-wonder-1.0          --ages $SHORT --replicas 3
go H6  --harness pi    --model muse-wonder-1.0          --ages $SHORT --replicas 3
go H7  --harness devin --model claude-opus-5-5-low      --ages $DEV   --replicas 2
go H8  --harness pi    --model devin/claude-opus-5-5    --ages $DEV   --replicas 2
go H9  --harness devin --model gpt-6-1-terra-low        --ages $GPT   --replicas 2
go H10 --harness pi    --model devin/gpt-6-1-terra      --ages $GPT   --replicas 2
echo launched
