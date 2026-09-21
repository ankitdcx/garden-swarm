#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,sys
root=Path(__file__).resolve().parent
receipt=json.loads((root/'CLOSURE_RECEIPT_v15.11.json').read_text(encoding='utf-8'))
fail=[]
for name,meta in receipt['primary_source_hashes'].items():
    p=root/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=meta['sha256']: fail.append('hash:'+name)
for doc,status in receipt['inherited_retention_payload_checks'].items():
    if status!='PASS': fail.append('retention:'+doc)
for key in ('missing_v1511_ids','missing_constructs','missing_tests'):
    if receipt['checks'][key]: fail.append(key)
print(json.dumps({'schema':'GardenV1511Verification/v1','status':'PASS' if not fail else 'FAIL','failures':fail},indent=2))
sys.exit(0 if not fail else 2)
