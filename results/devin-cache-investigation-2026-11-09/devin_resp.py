import sys,json,random,string,time,uuid; import os; sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','harness')); sys.argv=['x']; import limits
def usage(d):
    u=d.get('usage') or {}; return f"{u.get('input_tokens')}/{(u.get('input_tokens_details') or {}).get('cached_tokens')}"
def run(model, variant, effort="low"):
    salt=''.join(random.choices(string.ascii_lowercase,k=8))
    text=f"Run {salt}. Reply with just OK.\n"+"\n".join(f"Fact {i}: the {salt} token number {i} is {random.Random(i).randint(1,10**9)}." for i in range(700))
    key=str(uuid.uuid4())
    base={"model":model,"instructions":"You are a helpful coding assistant. "*200,"store":False,"stream":False,
          "tools":[{"type":"function","name":f"tool_{i}","description":"Does thing %d. "%i*20,"parameters":{"type":"object","properties":{"x":{"type":"string"}}}} for i in range(5)]}
    if 'key' in variant: base["prompt_cache_key"]=key
    if 'effort' in variant: base["reasoning"]={"effort":effort,"summary":"auto"}; base["include"]=["reasoning.encrypted_content"]
    inp=[{"type":"message","role":"user","content":[{"type":"input_text","text":text}]}]
    code,d1,_=limits.post('/v1/responses',{**base,"input":inp,"max_output_tokens":256})
    if code!=200: print(model,variant,'ERR',limits.message(d1)[:200]); return
    out=d1.get('output',[])
    kinds=[o.get('type') for o in out]
    time.sleep(3)
    replay=[o for o in out if o.get('type') in ('message','reasoning','function_call')] if 'replay' in variant else [{"type":"message","role":"assistant","content":[{"type":"output_text","text":"OK"}]}]
    inp2=inp+replay+[{"type":"message","role":"user","content":[{"type":"input_text","text":"Reply with just OK again."}]}]
    code,d2,_=limits.post('/v1/responses',{**base,"input":inp2,"max_output_tokens":256})
    print(f"{model:<32} {variant:<20} out1={kinds} turn1 {usage(d1)} turn2 {usage(d2) if code==200 else limits.message(d2)[:150]}", flush=True)
def same(model, effort, n_facts=700, sleep=3):
    salt=''.join(random.choices(string.ascii_lowercase,k=8))
    text=f"Run {salt}. Reply with just OK.\n"+"\n".join(f"Fact {i}: the {salt} token number {i} is {random.Random(i).randint(1,10**9)}." for i in range(n_facts))
    body={"model":model,"instructions":"You are a helpful coding assistant. "*200,"store":False,"input":[{"type":"message","role":"user","content":[{"type":"input_text","text":text}]}],"max_output_tokens":256}
    if effort: body["reasoning"]={"effort":effort}
    res=[]
    for i in range(3):
        code,d,_=limits.post('/v1/responses',body); res.append(usage(d) if code==200 else 'ERR'); time.sleep(sleep)
    print(f"{model:<32} same-body effort={effort} facts={n_facts}: {res}", flush=True)
