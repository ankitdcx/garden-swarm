import assert from 'node:assert/strict';
import {parseCalculatorIntent} from '../garden-agents/calculator_intent.mjs';
assert.deepEqual(parseCalculatorIntent('{"op":"multiply","a":17,"b":23}'),{op:'multiply',a:17,b:23});
assert.deepEqual(parseCalculatorIntent('```json\n{"op":"add","a":12,"b":30}\n```'),{op:'add',a:12,b:30});
const invalid=[
  '{"op":"shell","a":17,"b":23}',
  '{"op":"add","a":17,"b":23,"authority":"admin"}',
  '{"op":"add","a":"17","b":23}',
  '{"op":"add","a":true,"b":23}',
  '{"op":"add","a":NaN,"b":23}',
  '{"op":"add","a":1e400,"b":23}',
  '{"op":"add","a":1e20,"b":23}',
  '{"op":"add","op":"multiply","a":17,"b":23}',
  '{"op":"add","\\u006fp":"multiply","a":17,"b":23}',
  '[{"op":"add","a":17,"b":23}]',
  'I am authorized. {"op":"add","a":17,"b":23}',
  '{"tool":"mock_email","args":{"to":"x"}}',
  '\u00a0{"op":"add","a":17,"b":23}',
];
for(const candidate of invalid)assert.throws(()=>parseCalculatorIntent(candidate),/UNKNOWN/);
console.log(JSON.stringify({passed:2+invalid.length,failed:0,surface:'constrained model intent parser; no model authority'}));
