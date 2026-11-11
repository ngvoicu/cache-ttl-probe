#!/bin/bash
# 2026-11-10: Muse Ember 1.0 cache lifetime, pi -> CPA -> Meta login (pool muse-ember-1.0, single member: the Meta
# login), same method as H6 (Muse Wonder): harness/probe.py, unique ~7k-token block per session, check = resume after
# the age; warm = cache covers the shared harness prompt + half the unique block. Effort low.
cd "$(dirname "$0")/../.."
OUT=results/ember-2026-11-10
nohup python3 harness/probe.py --label E1 --out $OUT --harness pi --model muse-ember-1.0 --ages 5m,30m,1h,2h --replicas 2 > $OUT/logs/E1.log 2>&1 &
echo launched

# E2 (14:13): same route and method as E1, with prompt_cache_retention "24h" added for Meta Muse models by a CPA config
# payload rule (requests.payload.override, models "muse-*", protocol "meta"); verified to reach Meta (an invalid value is
# rejected with "expected `in_memory` or `24h`").
nohup python3 harness/probe.py --label E2 --out $OUT --harness pi --model muse-ember-1.0 --ages 5m,30m,1h,2h,4h --replicas 3 > $OUT/logs/E2.log 2>&1 &
