#!/bin/bash
# 2026-11-10 21:23: the Devin routes whose result was "random" or contradictory with 2 samples per age
# (../devin-harness-2026-11-08: D6p, D8p, D9p, D10p), measured again with 5 samples. pi -> CLIProxyAPI -> Devin, same
# account and method (harness/probe.py, a new pi session per sample, resumed once after the age). Effort low.
# pi reaches them through TEMPORARY pools devin/* in cliproxyapi.conf (backup
# ~/.cli-proxy-api-backups/pre-measure-pools-20261110-212000). Remove afterwards.
cd "$(dirname "$0")/../.."
OUT=results/devin-repeat-2026-11-10
AGES=5m,15m,30m,1h,2h
go() { nohup caffeinate -i python3 harness/probe.py --label "$1" --out $OUT --ages $AGES --replicas 5 --harness pi "${@:2}" > $OUT/logs/$1.log 2>&1 < /dev/null & sleep 20; }
go D6r  --model devin/gemini-4-argon
go D8r  --model devin/deepseek-v4-1-flash-1017
go D9r  --model devin/glm-5-3
go D10r --model devin/grok-4-7
echo launched
