/** Observation only: permissions supplement the trusted JS runner.
 * This does not claim containment of malicious JS or host compromise.
 */
import fs from 'node:fs';
import child from 'node:child_process';
const checks=[];
for(const [name, action] of [
  ['outside_model_read',()=>fs.readFileSync('/etc/hostname')],
  ['filesystem_write',()=>fs.writeFileSync('/tmp/garden-wasm-probe-denied','x')],
  ['child_process',()=>child.spawnSync('/usr/bin/id')],
]) {
  let blocked=false,code=null;
  try {action();} catch(error) {code=error.code;blocked=code==='ERR_ACCESS_DENIED';}
  checks.push({name,blocked,code});
}
console.log(JSON.stringify({schema:'garden.wasm_permission_probe.v1',checks,all_observed_blocked:checks.every(x=>x.blocked),limitation:'Node permissions do not guarantee malicious-host-JS containment.'}));
if(checks.some(x=>!x.blocked))process.exitCode=2;
