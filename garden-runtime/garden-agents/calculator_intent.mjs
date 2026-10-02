/** Model text can select only a bounded read-only calculator proposal. */
export function parseCalculatorIntent(text) {
  if(typeof text!=='string'||Buffer.byteLength(text)>4096)throw Error('model planning UNKNOWN: output budget exceeded');
  const raw=text.replace(/^[ \t\r\n]*/, '').replace(/[ \t\r\n]*$/, '').replace(/^```(?:json)?[ \t\r\n]*/,'').replace(/[ \t\r\n]*```$/,'');
  let proposed;
  try {proposed=JSON.parse(raw);} catch {throw Error('model planning UNKNOWN: output is not strict JSON');}
  const keyMatches=[...raw.matchAll(/("(?:[^"\\]|\\.)*")[ \t\r\n]*:/g)].map(match=>JSON.parse(match[1]));
  if(new Set(keyMatches).size!==keyMatches.length)throw Error('model planning UNKNOWN: duplicate object key');
  if(!proposed||typeof proposed!=='object'||Array.isArray(proposed)||Object.keys(proposed).sort().join(',')!=='a,b,op'||!['add','subtract','multiply','divide'].includes(proposed.op)||!Number.isFinite(proposed.a)||!Number.isFinite(proposed.b)||Math.abs(proposed.a)>1e12||Math.abs(proposed.b)>1e12)throw Error('model planning UNKNOWN: calculator proposal contract violated');
  return proposed;
}
