let state={question:"",answers:{},critiques:{},stopped:false};
const sites=["chatgpt.com","gemini.google.com","claude.ai","grok.com","chat.deepseek.com"];
async function tabs(){let all=await browser.tabs.query({});return all.filter(t=>sites.some(s=>(t.url||"").includes(s)))}
async function run(prompt,mode){state.stopped=false;let ts=await tabs(),out={};for(const t of ts){if(state.stopped)break;try{let r=await browser.tabs.sendMessage(t.id,{type:"RUN",prompt,mode});out[r.site||t.url]=r.answer||("ERROR: "+(r.error||"no answer"))}catch(e){out[t.url]="ERROR: "+e.message}}return out}
function anon(obj){return Object.values(obj).map((x,i)=>"Answer "+String.fromCharCode(65+i)+":\n"+x).join("\n\n")}
browser.runtime.onMessage.addListener(async m=>{
 if(m.type==="STOP"){state.stopped=true;return{status:"Stopped",text:JSON.stringify(state,null,2)}}
 if(m.type==="STATE")return{status:"Ready",text:JSON.stringify(state,null,2)}
 if(m.type==="ASK"){state.question=m.prompt;state.answers=await run(m.prompt,"answer");return{status:"Round 1 collected",text:JSON.stringify(state.answers,null,2)}}
 if(m.type==="CHALLENGE"){let p="Original question:\n"+state.question+"\n\nIndependent answers:\n"+anon(state.answers)+"\n\nFind concrete errors, missing dimensions and disagreements. Do not guess authors. Give a revised answer under 200 words.";state.critiques=await run(p,"critique");return{status:"Cross-check collected",text:JSON.stringify(state.critiques,null,2)}}
 if(m.type==="FINAL"){let ts=await tabs();if(!ts.length)return{status:"No AI tabs",text:""};let p="Original question:\n"+state.question+"\n\nAnswers:\n"+anon(state.answers)+"\n\nCritiques:\n"+anon(state.critiques)+"\n\nProduce one concise best-supported answer, then unresolved disagreements and unknowns. Do not force consensus.";let r=await browser.tabs.sendMessage(ts[0].id,{type:"RUN",prompt:p,mode:"final"});return{status:"Final collected",text:r.answer||r.error||""}}
 return{status:"Unknown command",text:""}
});
