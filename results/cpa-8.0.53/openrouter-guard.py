# Stops all OpenRouter probe runs when they have spent more than BUDGET dollars since the guard started,
# or when the balance drops below $0.20. Checks every 3 minutes.
import json, subprocess, sys, time, urllib.request, yaml
BUDGET = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
key = yaml.safe_load(open('/opt/homebrew/etc/cliproxyapi.conf'))['api-keys']['openai-compatibility'][0]['keys'][0]['api-key']
def credits():
    d = json.load(urllib.request.urlopen(urllib.request.Request('https://openrouter.ai/api/v1/credits', headers={'Authorization': 'Bearer ' + key}), timeout=20))['data']
    return d['total_credits'], d['total_usage']
start = credits()[1]
while True:
    try:
        total, used = credits()
        spent, left = used - start, total - used
        print(time.strftime('%H:%M:%S'), f'spent ${spent:.2f} of ${BUDGET:.0f} budget, balance ${left:.2f}', flush=True)
        if spent > BUDGET or left < 0.20:
            subprocess.run(['pkill', '-f', '--', '--model probe-o']); subprocess.run(['pkill', '-f', 'openrouter.ai/api/v1'])
            print('budget reached: stopped OpenRouter runs', flush=True)
            break
    except Exception as e:
        print('guard error', e, flush=True)
    if not (subprocess.run(['pgrep', '-f', '--', '--model probe-o'], capture_output=True).stdout or subprocess.run(['pgrep', '-f', 'openrouter.ai/api/v1'], capture_output=True).stdout):
        print('no OpenRouter runs left', flush=True); break
    time.sleep(180)
