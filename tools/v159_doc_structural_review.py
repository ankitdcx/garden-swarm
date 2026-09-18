#!/usr/bin/env python3
import argparse, json, os, subprocess, hashlib
from pathlib import Path

OPENROUTER='https://openrouter.ai/api/v1/chat/completions'
PACKET=Path('review-inputs/v159-doc-rebuild/STRUCTURAL_REVIEW_PACKET.txt')
OUT=Path('review-results/v159-doc-rebuild/structural')
MODELS={'deepseek':'deepseek/deepseek-v4.1-flash','glm':'z-ai/glm-5.3-flash','xiaomi':'xiaomi/mimo-v2.5','gemini':'google/gemini-3.8-flash'}

def parse_obj(txt):
    s=(txt or '').strip()
    if s.startswith('```'):
        s=s.split('\n',1)[1] if '\n' in s else s
        if s.endswith('```'): s=s[:-3]
        s=s.strip()
        if s.lower().startswith('json\n'): s=s[5:]
    if '{' in s and '}' in s:
        try: return json.loads(s[s.find('{'):s.rfind('}')+1])
        except: pass
    try: return json.loads(s)
    except: return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--family',required=True,choices=MODELS); a=ap.parse_args()
    key=os.environ['OPENROUTER_API_KEY']; model=MODELS[a.family]; packet=PACKET.read_text()
    prompt='You are an independent technical documentation architect. Review only the supplied packet. Do not invent Garden semantics. Return the requested JSON only.\n\n'+packet
    body={'model':model,'messages':[{'role':'user','content':prompt}],'temperature':0.05,'max_tokens':7000,'stream':False,'provider':{'allow_fallbacks':True,'data_collection':'deny','sort':'price','ignore':['anthropic','mistral','nvidia'],'max_price':{'prompt':1.0,'completion':4.0}}}
    if model.startswith('deepseek/') or model.startswith('xiaomi/'): body['reasoning']={'effort':'none'}
    elif model.startswith('z-ai/glm-'): body['reasoning']={'effort':'low'}
    p=subprocess.run(['curl','-sS','--connect-timeout','10','--max-time','300',OPENROUTER,'-X','POST','-H','Authorization: Bearer '+key,'-H','Content-Type: application/json','-H','HTTP-Referer: https://github.com/ankitdcx/garden-swarm','-H','X-Title: Garden v15.9 Documentation Rebuild','--data-binary','@-','-w','\\n%{http_code}'],input=json.dumps(body,separators=(',',':')),text=True,capture_output=True,timeout=320)
    raw=p.stdout
    if '\n' not in raw: raise SystemExit(2)
    payload,status=raw.rsplit('\n',1); status=int(status.strip())
    data=json.loads(payload)
    txt=((data.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    obj=parse_obj(txt); usable=(200 <= status < 300 and isinstance(obj,dict))
    OUT.mkdir(parents=True,exist_ok=True)
    result={'family':a.family,'model':model,'packet_sha256':hashlib.sha256(packet.encode()).hexdigest(),'http_status':status,'usable':usable,'review':obj,'raw':None if obj else txt,'usage':data.get('usage'),'provider':data.get('provider')}
    (OUT/(a.family+'.json')).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'family':a.family,'usable':usable,'status':status}))
    if not usable: raise SystemExit(2)

if __name__=='__main__': main()
