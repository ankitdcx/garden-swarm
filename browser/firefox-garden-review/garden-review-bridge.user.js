// ==UserScript==
// @name         Garden Review Bridge
// @namespace    https://github.com/ankitdcx/garden-swarm
// @version      0.1.0
// @description  Local-only Garden bridge for AI web reviewers
// @match        https://chat.deepseek.com/*
// @match        https://gemini.google.com/*
// @match        https://claude.ai/*
// @match        https://grok.com/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
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
 function post(){
  const body=JSON.stringify(probe());
  GM_xmlhttpRequest({method:'POST',url:'http://127.0.0.1:17351/calibration',headers:{'Content-Type':'application/json'},data:body});
 }
 setTimeout(post,2500); setInterval(post,10000);
})();