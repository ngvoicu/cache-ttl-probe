#!/bin/bash
# 2026-11-10 21:22: Meta Muse models through pi -> CLIProxyAPI -> Meta (Muse Code subscription login), with
# prompt_cache_retention "24h" added by the CLIProxyAPI config rule described in ../ember-2026-11-10 (run E2).
# M1 continues E2 (Ember, warm 3/3 to 4 h) to 24 h. M2 = Muse Wonder 1.0, M3 = Muse Spark 1.3 (never measured).
# Method as E1/E2: harness/probe.py, a new pi session per sample, resumed once after the age. Effort low.
# pi reaches Wonder and Spark through TEMPORARY pools in cliproxyapi.conf (backup
# ~/.cli-proxy-api-backups/pre-measure-pools-20261110-212000). Remove afterwards.
cd "$(dirname "$0")/../.."
OUT=results/meta-24h-2026-11-10
go() { nohup caffeinate -i python3 harness/probe.py --label "$1" --out $OUT --harness pi --replicas 3 "${@:2}" > $OUT/logs/$1.log 2>&1 < /dev/null & sleep 20; }
go M1 --model muse-ember-1.0  --ages 8h,12h,24h
go M3 --model muse-spark-1.3  --ages 5m,1h,4h,24h
go M2 --model muse-wonder-1.0 --ages 4h,12h,24h
echo launched
