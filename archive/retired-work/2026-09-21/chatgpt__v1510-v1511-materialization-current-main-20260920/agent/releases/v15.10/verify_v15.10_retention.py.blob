#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,re,sys
root=Path(__file__).resolve().parent
receipt=json.loads((root/'RETENTION_CLOSURE_RECEIPT_v15.10.json').read_text(encoding='utf-8'))
cat=(root/'GARDEN_CATALOGUE_v15.10.txt').read_text(encoding='utf-8')
fail=[]
for name,meta in receipt['current_file_hashes'].items():
    p=root/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=meta['sha256']: fail.append('hash:'+name)
for doc,meta in receipt['source_payloads'].items():
    a=f"----- BEGIN RETENTION PAYLOAD {doc} SHA256 {meta['sha256']} -----\n"
    b=f"----- END RETENTION PAYLOAD {doc} -----"
    if a not in cat or b not in cat: fail.append('payload-marker:'+doc); continue
    payload=cat.split(a,1)[1].split(b,1)[0]
    if hashlib.sha256(payload.encode()).hexdigest()!=meta['sha256']:
        if not(payload.endswith('\n') and hashlib.sha256(payload[:-1].encode()).hexdigest()==meta['sha256']):
            fail.append('payload-hash:'+doc)
print(json.dumps({'schema':'GardenStandaloneRetentionVerification/v1','status':'PASS' if not fail else 'FAIL','failures':fail},indent=2))
sys.exit(0 if not fail else 2)
