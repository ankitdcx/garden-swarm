// ==UserScript==
// @name         Garden Review Bridge
// @namespace    https://github.com/ankitdcx/garden-swarm
// @version      0.2.1
// @description  Local-only Garden bridge for AI web reviewers
// @match        https://chat.deepseek.com/*
// @match        https://gemini.google.com/*
// @match        https://claude.ai/*
// @match        https://grok.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==
(function(){
 'use strict';
 const host=location.hostname;
 const provider=host.includes('deepseek')?'deepseek':host.includes('gemini')?'gemini':host.includes('claude')?'claude':host.includes('grok')?'grok':'unknown';
 const visible=e=>{const r=e.getBoundingClientRect();return r.width>20&&r.height>15&&r.bottom>0&&r.top<innerHeight};
 const score=e=>{const r=e.getBoundingClientRect();return(e.matches('textarea,[contenteditable=true]')?100:0)+(e.getAttribute('role')==='textbox'?40:0)+(r.top>innerHeight*.4?30:0)+(r.width>innerWidth*.3?20:0)};
 function probe(){
  const es=[...document.querySelectorAll('textarea,[contenteditable=true],[role=textbox],input[type=text]')].filter(visible).sort((a,b)=>score(b)-score(a));
  const e=es[0]; const r=e&&e.getBoundingClientRect();
  return {provider,href:location.origin,composerFound:!!e,composer:e?{tag:e.tagName,role:e.getAttribute('role')||'',id:e.id||'',classes:String(e.className||'').slice(0,120),bounds:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}:null};
 }
 function setComposer(e,text){
  e.focus();
  if(e.tagName==='TEXTAREA'||e.tagName==='INPUT'){
   const proto=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
   const setter=Object.getOwnPropertyDescriptor(proto,'value').set; setter.call(e,text);
   e.dispatchEvent(new Event('input',{bubbles:true})); e.dispatchEvent(new Event('change',{bubbles:true}));
  } else {
   e.textContent=text; e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:text}));
  }
 }
 function composer(){return [...document.querySelectorAll('textarea,[contenteditable=true],[role=textbox],input[type=text]')].filter(visible).sort((a,b)=>score(b)-score(a))[0]}
 function post(){
  const body=JSON.stringify(probe());
  GM_xmlhttpRequest({method:'POST',url:'http://127.0.0.1:17351/calibration',headers:{'Content-Type':'application/json'},data:body});
 }
 async function pollJob(){
  GM_xmlhttpRequest({method:'GET',url:'http://127.0.0.1:17351/job/'+provider,onload:r=>{
   try{const j=JSON.parse(r.responseText); if(!j||!j.job_id||!j.prompt||GM_getValue('last_job_'+provider,'')===j.job_id)return;
    const e=composer(); if(!e)return; setComposer(e,j.prompt); GM_setValue('last_job_'+provider,j.job_id);
    GM_xmlhttpRequest({method:'POST',url:'http://127.0.0.1:17351/job/'+provider+'/prepared',headers:{'Content-Type':'application/json'},data:JSON.stringify({job_id:j.job_id,prepared:true})});
   }catch(err){GM_xmlhttpRequest({method:'POST',url:'http://127.0.0.1:17351/debug',headers:{'Content-Type':'application/json'},data:JSON.stringify({provider,stage:'poll-parse',error:String(err),status:r.status,body:String(r.responseText).slice(0,500)})});}
  },onerror:e=>GM_xmlhttpRequest({method:'POST',url:'http://127.0.0.1:17351/debug',headers:{'Content-Type':'application/json'},data:JSON.stringify({provider,stage:'poll-http-error',error:String(e.error||e)})})});
 }
 setTimeout(post,2500); setInterval(post,10000); setInterval(pollJob,3000);
})();