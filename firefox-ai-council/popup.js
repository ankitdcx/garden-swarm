const $=id=>document.getElementById(id);
async function cmd(type){$("status").textContent="Running…";let r=await browser.runtime.sendMessage({type,prompt:$("q").value});$("status").textContent=r.status||"Done";$("out").textContent=r.text||""}
$("ask").onclick=()=>cmd("ASK");$("challenge").onclick=()=>cmd("CHALLENGE");$("final").onclick=()=>cmd("FINAL");$("stop").onclick=()=>cmd("STOP");
browser.runtime.sendMessage({type:"STATE"}).then(r=>{$("out").textContent=r.text||"";$("status").textContent=r.status||"Ready"});
