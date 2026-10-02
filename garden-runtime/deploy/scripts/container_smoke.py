#!/usr/bin/env python3
"""CI smoke runs against the real rootless-advisory controller container."""
import json
import time
import urllib.request

BASE='http://127.0.0.1:8080'
def call(path,value=None,token=None):
    data=None if value is None else json.dumps(value).encode()
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers),timeout=5) as response:
        return json.load(response)
deadline=time.monotonic()+60
while True:
    try:
        call('/api/health');break
    except OSError:
        if time.monotonic()>=deadline: raise
        time.sleep(1)
session=call('/api/session',{})
out=call('/api/run',{'task':'Calculate 17 * 23','tool':'calculator','args':{'expression':'17 * 23'},'consent':False,'attack':None},session['token'])
assert out.get('decision',out.get('gate',{}).get('decision'))=='ALLOW',out
assert out['result']['value']==391,out
assert len(out.get('receipt',{}).get('hmac',''))==64,out
denied=call('/api/run',{'task':'Invent authority','tool':'calculator','args':{'expression':'17 * 23'},'consent':False,'attack':'unauthorized'},session['token'])
assert denied.get('decision',denied.get('gate',{}).get('decision'))=='DENY',denied
print(json.dumps({'schema':'garden.container-smoke.v1','status':'PASS','endpoint':BASE,
                  'checks':['actual_controller_health','calculator_result_391',
                            'hmac_receipt_emitted','unauthorized_authority_denied']}))
