function site(){let h=location.hostname;if(h.includes("chatgpt"))return"ChatGPT";if(h.includes("gemini"))return"Gemini";if(h.includes("claude"))return"Claude";if(h.includes("grok"))return"Grok";if(h.includes("deepseek"))return"DeepSeek";return h}
const cfg={
 ChatGPT:{inputs:['#prompt-textarea','textarea'],send:['button[data-testid="send-button"]','button[aria-label*="Send"]']},
 Gemini:{inputs:['div[contenteditable="true"]','textarea'],send:['button[aria-label*="Send"]','button.send-button']},
 Claude:{inputs:['div[contenteditable="true"]','textarea'],send:['button[aria-label*="Send"]','button[type="submit"]']},
 Grok:{inputs:['textarea','div[contenteditable="true"]'],send:['button[type="submit"]','button[aria-label*="Send"]']},
 DeepSeek:{inputs:['textarea','div[contenteditable="true"]'],send:['button[aria-label*="Send"]','button[type="submit"]']}
};
const sleep=m=>new Promise(r=>setTimeout(r,m));
function first(ss){for(const s of ss){let e=document.querySelector(s);if(e)return e}return null}
function setText(el,text){el.focus();if(el.tagName==="TEXTAREA"||el.tagName==="INPUT"){let d=Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el),"value");d&&d.set?d.set.call(el,text):el.value=text;el.dispatchEvent(new Event("input",{bubbles:true}))}else{el.textContent=text;el.dispatchEvent(new InputEvent("input",{bubbles:true,inputType:"insertText",data:text}))}}
function snapshot(){let sels=['[data-message-author-role="assistant"]','.markdown','.prose','article','main'];let arr=[];for(const s of sels)document.querySelectorAll(s).forEach(e=>{let t=(e.innerText||"").trim();if(t.length>30)arr.push(t)});return arr}
async function waitAnswer(before){let last="",stable=0;for(let i=0;i<120;i++){await sleep(1000);let a=snapshot(),cur=a[a.length-1]||"";if(cur&&cur!==before&&cur===last)stable++;else stable=0;last=cur;if(stable>=3&&cur.length>30)return cur}throw new Error("Timed out waiting for stable response")}
browser.runtime.onMessage.addListener(async m=>{if(m.type!=="RUN")return;let s=site(),c=cfg[s];if(!c)return{site:s,error:"Unsupported site"};let inp=first(c.inputs);if(!inp)return{site:s,error:"Input box not found"};let old=(snapshot().slice(-1)[0]||"");setText(inp,m.prompt);await sleep(400);let b=first(c.send);if(b)b.click();else{inp.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",code:"Enter",bubbles:true}));inp.dispatchEvent(new KeyboardEvent("keyup",{key:"Enter",code:"Enter",bubbles:true}))}try{return{site:s,answer:await waitAnswer(old)}}catch(e){return{site:s,error:e.message}}});
