// ==UserScript==
// @name         AI Council - Multi AI Roundtable
// @namespace    garden.local
// @version      1.3.0
// @description  Ask logged-in AI web chats together, cross-check, and synthesize without APIs.
// @match        https://chatgpt.com/*
// @match        https://gemini.google.com/*
// @match        https://claude.ai/*
// @match        https://grok.com/*
// @match        https://chat.deepseek.com/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_addValueChangeListener
// @grant        GM_registerMenuCommand
// @run-at       document-idle
// ==/UserScript==
(function(){
'use strict';
const sleep=m=>new Promise(r=>setTimeout(r,m));
const S={question:'aic_q',phase:'aic_phase',job:'aic_job',answers:'aic_answers',critiques:'aic_critiques',final:'aic_final',stop:'aic_stop'};
function who(){let h=location.hostname;if(h==='chatgpt.com')return'ChatGPT';if(h==='gemini.google.com')return'Gemini';if(h==='claude.ai')return'Claude';if(h==='grok.com')return'Grok';if(h==='chat.deepseek.com')return'DeepSeek';return h}
const cfg={
ChatGPT:{i:['#prompt-textarea','textarea','div[contenteditable="true"]'],s:['button[data-testid="send-button"]','button[aria-label*="Send"]']},
Gemini:{i:['rich-textarea div[contenteditable="true"]','div.ql-editor[contenteditable="true"]','div[contenteditable="true"]'],s:['button[aria-label="Send message"]','button[aria-label*="Send"]']},
Claude:{i:['div[contenteditable="true"]','textarea'],s:['button[aria-label*="Send"]','button[type="submit"]']},
Grok:{i:['textarea','div[contenteditable="true"]'],s:['button[type="submit"]','button[aria-label*="Send"]']},
DeepSeek:{i:['textarea','div[contenteditable="true"]'],s:['button[aria-label*="Send"]','button[type="submit"]']}
};
function first(a){for(const q of a){let e=document.querySelector(q);if(e)return e}return null}
function setText(e,t){e.focus();if('value'in e){let p=Object.getPrototypeOf(e),d=Object.getOwnPropertyDescriptor(p,'value');if(d&&d.set)d.set.call(e,t);else e.value=t;e.dispatchEvent(new Event('input',{bubbles:true}))}else{e.textContent=t;e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:t}))}}
function snaps(){let out=[];['[data-message-author-role="assistant"]','.markdown','.prose','article','main'].forEach(q=>document.querySelectorAll(q).forEach(e=>{let t=(e.innerText||'').trim();if(t.length>40)out.push(t)}));return out}
async function stable(old){let last='',n=0;for(let k=0;k<180;k++){if(GM_getValue(S.stop,false))throw Error('Stopped');await sleep(1000);let a=snaps(),x=a[a.length-1]||'';if(x&&x!==old&&x===last)n++;else n=0;last=x;if(n>=3&&x.length>40)return x}throw Error('Response timeout')}
async function send(p){let c=cfg[who()],e=first(c.i);if(!e)throw Error('Input not found');let old=snaps().slice(-1)[0]||'';setText(e,p);await sleep(500);let b=first(c.s);if(b)b.click();else{e.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',bubbles:true}));e.dispatchEvent(new KeyboardEvent('keyup',{key:'Enter',code:'Enter',bubbles:true}))}return stable(old)}
function getObj(k){let x=GM_getValue(k,{});return x&&typeof x==='object'?x:{}}
function anon(o,label='Answer'){return Object.values(o).map((x,i)=>label+' '+String.fromCharCode(65+i)+':\n'+x).join('\n\n')}
async function execute(job){
 if(!job||job.id===GM_getValue('aic_last_job',''))return;GM_setValue('aic_last_job',job.id);
 let me=who();try{let answer=await send(job.prompt);let key=job.phase==='round1'?S.answers:job.phase==='critique'?S.critiques:S.final;if(key===S.final)GM_setValue(key,{model:me,text:answer});else{let o=getObj(key);o[me]=answer;GM_setValue(key,o)}}catch(e){let key=job.phase==='round1'?S.answers:S.critiques,o=getObj(key);o[me]='ERROR: '+e.message;GM_setValue(key,o)}
 render();
}
GM_addValueChangeListener(S.job,(k,o,n,remote)=>{if(remote)execute(n)});
function broadcast(phase,prompt){GM_setValue(S.stop,false);GM_setValue(S.job,{id:Date.now()+'-'+Math.random(),phase,prompt})}
function expectedTabs(){return Number(GM_getValue('aic_expected',3))||3}
async function waitCount(key,n,ms=180000){let t=Date.now();while(Date.now()-t<ms){if(GM_getValue(S.stop,false))throw Error('Stopped');if(Object.keys(getObj(key)).length>=n)return true;await sleep(1000)}return false}
function setStage(x){GM_setValue('aic_stage',x);render()}
async function start(){
 let q=document.querySelector('#aic-question').value.trim();if(!q)return;
 GM_setValue(S.stop,true);GM_setValue(S.question,q);GM_setValue(S.answers,{});GM_setValue(S.critiques,{});GM_setValue(S.final,{});GM_setValue('aic_stage','Starting new council…');let box=document.querySelector('#aic-out');if(box)box.textContent='';await sleep(150);GM_setValue(S.stop,false);
 const n=expectedTabs();
 try{
  setStage('Asking '+n+' AIs…');broadcast('round1',q);
  await waitCount(S.answers,n);
  setStage('Comparing answers…');
  let a=getObj(S.answers);broadcast('critique','Original question:\n'+q+'\n\nIndependent answers:\n'+labelled(a)+'\n\nReview EVERY answer above independently. For each answer, state any concrete error, missing dimension, or useful unique insight. Then give your own revised answer under 200 words. Do not merely follow majority agreement.');
  await waitCount(S.critiques,n);
  setStage('Making final answer…');
  let c=getObj(S.critiques);broadcast('final','Original question:\n'+q+'\n\nAnswers:\n'+labelled(a)+'\n\nCross-critiques:\n'+labelled(c,'Review')+'\n\nYou are the final synthesizer. Use EVERY original answer and EVERY cross-review/revised answer above. Resolve disagreements only when reasons or evidence justify it. Produce sections: FINAL ANSWER, AGREEMENT, IMPORTANT DISAGREEMENTS, MISSED DIMENSIONS, UNKNOWNS. Keep the final answer concise but preserve important minority insights.');
  let t=Date.now();while(Date.now()-t<180000){let f=getObj(S.final);if(f.text){setStage('Done');return}await sleep(1000)}
  setStage('Final answer timed out');
 }catch(e){setStage(e.message)}
}
function stop(){GM_setValue(S.stop,true);setStage('Stopped')}
function render(){
 let p=document.querySelector('#ai-council-box');if(!p)return;
 let a=getObj(S.answers),c=getObj(S.critiques),f=getObj(S.final),stage=GM_getValue('aic_stage','Ready');
 p.querySelector('#aic-status').textContent=stage+'  •  '+Object.keys(a).length+' answers  •  '+Object.keys(c).length+' reviews';
 p.querySelector('#aic-out').textContent=f.text|| (Object.keys(a).length? 'Waiting for the council to finish.\n\nAnswers received from: '+Object.keys(a).join(', '):'Your final answer will appear here.');
}
function ui(){
 if(document.querySelector('#ai-council-box'))return;
 let d=document.createElement('div');d.id='ai-council-box';
 d.style='position:fixed;z-index:2147483647;left:5vw;top:5vh;width:90vw;height:90vh;background:#111;color:#fff;padding:18px;border-radius:18px;font:18px sans-serif;box-shadow:0 4px 28px #000b;box-sizing:border-box;display:flex;flex-direction:column;overflow:hidden';
 d.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:28px">AI Council</b><button id="aic-close" style="font-size:24px;padding:5px 14px">×</button></div><textarea id="aic-question" placeholder="Ask something…" style="width:100%;height:18%;min-height:90px;margin-top:10px;box-sizing:border-box;font-size:21px;padding:12px;border-radius:10px"></textarea><button id="aic-ask" style="font-size:24px;font-weight:bold;padding:18px;min-height:70px;margin-top:10px">ASK COUNCIL</button><div id="aic-status" style="margin-top:12px;font-size:17px">Ready</div><pre id="aic-out" style="white-space:pre-wrap;flex:1;min-height:0;overflow:auto;background:#1d1d1d;padding:16px;border-radius:10px;font-size:19px;line-height:1.5;margin:10px 0 0 0"></pre><div style="display:flex;gap:8px;margin-top:8px"><button id="aic-stop" style="flex:1;font-size:18px;padding:12px">STOP</button><button id="aic-settings" style="flex:1;font-size:18px;padding:12px">AI COUNT: '+expectedTabs()+'</button></div>';
 document.body.appendChild(d);
 d.querySelector('#aic-ask').onclick=start;d.querySelector('#aic-stop').onclick=stop;d.querySelector('#aic-close').onclick=()=>d.remove();
 d.querySelector('#aic-settings').onclick=()=>{let n=prompt('How many AI tabs should Council wait for?',expectedTabs());if(n&&Number(n)>0){GM_setValue('aic_expected',Number(n));d.querySelector('#aic-settings').textContent='AI COUNT: '+Number(n)}};
 render();
}
GM_registerMenuCommand('AI Council: show panel',ui);setTimeout(ui,1500);setInterval(render,3000);
})();