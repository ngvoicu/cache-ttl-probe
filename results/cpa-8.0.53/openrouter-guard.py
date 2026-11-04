# Stops all OpenRouter probe runs when the account balance drops below $0.20. Checks every 3 minutes.
import json, subprocess, time, urllib.request, yaml
key = yaml.safe_load(open('/opt/homebrew/etc/cliproxyapi.conf'))['api-keys']['openai-compatibility'][0]['keys'][0]['api-key']
while True:
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request('https://openrouter.ai/api/v1/credits', headers={'Authorization': 'Bearer ' + key}), timeout=20))['data']
        left = d['total_credits'] - d['total_usage']
        print(time.strftime('%H:%M:%S'), f'OpenRouter balance ${left:.2f}', flush=True)
        if left < 0.20:
            subprocess.run(['pkill', '-f', '--', '--model probe-o'])
            print('balance below $0.20: stopped OpenRouter runs', flush=True)
            break
    except Exception as e:
        print('guard error', e, flush=True)
    if not subprocess.run(['pgrep', '-f', '--', '--model probe-o'], capture_output=True).stdout:
        print('no OpenRouter runs left', flush=True); break
    time.sleep(180)
