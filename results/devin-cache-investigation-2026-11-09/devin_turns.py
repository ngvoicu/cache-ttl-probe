import sys,json,random,string,time; sys.argv=['x']; sys.path.insert(0,'~/Projects/ngvoicu/cpa/cache-ttl-probe/harness'); import limits
model=sys.stdin.readline().strip() if False else None
def run(model, variant):
    salt=''.join(random.choices(string.ascii_lowercase,k=8))
    text=f"Run {salt}. Reply with just OK.\n"+"\n".join(f"Fact {i}: the {salt} token number {i} is {random.Random(i).randint(1,10**9)}." for i in range(700))
    msgs=[]
    if 'sys' in variant: msgs.append({"role":"system","content":"You are a helpful coding assistant. "*200})
    msgs.append({"role":"user","content":text})
    body={"model":model,"max_tokens":16,"messages":msgs}
    if 'tools' in variant:
        body["tools"]=[{"type":"function","function":{"name":f"tool_{i}","description":"Does thing %d. "%i*20,"parameters":{"type":"object","properties":{"x":{"type":"string"}}}}} for i in range(5)]
    code,d1,_=limits.post('/v1/chat/completions',body)
    reply=d1['choices'][0]['message'].get('content') or 'OK'
    u1=d1.get('usage',{})
    time.sleep(3)
    body2=dict(body); body2["messages"]=msgs+[{"role":"assistant","content":reply},{"role":"user","content":"Reply with just OK again."}]
    code,d2,_=limits.post('/v1/chat/completions',body2)
    u2=d2.get('usage',{})
    print(f"{model:<34} {variant:<10} turn1 {u1.get('prompt_tokens')}/{(u1.get('prompt_tokens_details') or {}).get('cached_tokens')}  turn2 {u2.get('prompt_tokens')}/{(u2.get('prompt_tokens_details') or {}).get('cached_tokens')}", flush=True)
for model in sys.argv[1:] if len(sys.argv)>1 else []: pass
