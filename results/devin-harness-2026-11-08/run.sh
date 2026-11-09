#!/bin/bash
# 2026-11-08: Devin's latest models, Devin CLI (c) vs pi through CPA (p), same Devin account. Effort low (lowest level
# the model has). Smoke test in ../devin-smoke-2026-11-08. Skipped: Fable 5.1 (Anthropic's content filter refuses the
# probe text on both routes); Devin CLI for GPT-6.1 Sol, GPT-6 Astra, Muse Wonder (reports 0 cached even at 30 s, as
# for Terra in H9). Kimi K3.1 Pro: Devin CLI only (CPA's Devin catalog has K3, not K3.1).
# pi routes are pinned with TEMPORARY pools devin/* in cliproxyapi.conf; backup
# ~/.cli-proxy-api-backups/pre-devin-harness-20261108-202642. Remove afterwards.
cd ~/Projects/ngvoicu/cpa/cache-ttl-probe
OUT=results/devin-harness-2026-11-08
AGES=5m,15m,30m,1h,2h
go() { nohup python3 harness/probe.py --label "$1" --out $OUT --ages $AGES --replicas 2 "${@:2}" > $OUT/logs/$1.log 2>&1 < /dev/null & sleep 20; }
go D1c  --harness devin --model claude-haiku-5-5-low
go D1p  --harness pi    --model devin/claude-haiku-5-5
go D2c  --harness devin --model claude-sonnet-5-5-low
go D2p  --harness pi    --model devin/claude-sonnet-5-5
go D4p  --harness pi    --model devin/gpt-6-1-sol
go D5p  --harness pi    --model devin/gpt-6-astra
go D6c  --harness devin --model gemini-4-argon-low
go D6p  --harness pi    --model devin/gemini-4-argon
go D7p  --harness pi    --model devin/muse-wonder-1-0
go D8c  --harness devin --model deepseek-v4-1-flash-1017-low
go D8p  --harness pi    --model devin/deepseek-v4-1-flash-1017
go D9c  --harness devin --model glm-5-3-low
go D9p  --harness pi    --model devin/glm-5-3
go D10c --harness devin --model grok-4-7-low
go D10p --harness pi    --model devin/grok-4-7
go D11c --harness devin --model nemotron-3-5-super-none
go D11p --harness pi    --model devin/nemotron-3-5-super
go D12c --harness devin --model swe-2-medium
go D12p --harness pi    --model devin/swe-2
go D13c --harness devin --model kimi-k3-1-pro-low
echo launched
