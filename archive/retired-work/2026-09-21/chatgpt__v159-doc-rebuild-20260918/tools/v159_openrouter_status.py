#!/usr/bin/env python3
import json, os
from urllib import request, error
key=os.environ.get('OPENROUTER_API_KEY')
if not key: raise SystemExit('OPENROUTER_API_KEY missing')
req=request.Request('https://openrouter.ai/api/v1/key',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
try:
    with request.urlopen(req,timeout=30) as r:
        data=json.loads(r.read().decode())
except error.HTTPError as exc:
    data={'http_status':exc.code,'detail':exc.read().decode(errors='replace')[:1000]}
p=data.get('data') if isinstance(data,dict) and isinstance(data.get('data'),dict) else data
safe={k:p.get(k) for k in ['label','usage','usage_daily','usage_weekly','usage_monthly','limit','limit_remaining','limit_reset','is_free_tier'] if isinstance(p,dict) and k in p}
print(json.dumps(safe,indent=2,sort_keys=True))
open('/tmp/openrouter-key-status.json','w').write(json.dumps(safe,indent=2,sort_keys=True)+'\n')
