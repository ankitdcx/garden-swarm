package org.garden.aicouncil
object CouncilState {
 enum class Phase { ROUND1, CRITIQUE, FINAL, DONE }
 @Volatile var running=false; @Volatile var stopRequested=false; @Volatile var prompt=""; @Volatile var activePrompt=""; @Volatile var index=0; @Volatile var phase=Phase.ROUND1
 val targets=mutableListOf<Target>(); val answers=linkedMapOf<String,String>(); val critiques=linkedMapOf<String,String>(); @Volatile var finalAnswer=""
 data class Target(val name:String,val pkg:String)
 fun reset(p:String){prompt=p;activePrompt=p;index=0;answers.clear();critiques.clear();finalAnswer="";phase=Phase.ROUND1;stopRequested=false;running=true}
 fun stop(){stopRequested=true;running=false}
 fun critiquePrompt():String { val block=answers.entries.mapIndexed{i,e->"Answer "+('A'.code+i).toChar()+":\n"+e.value}.joinToString("\n\n"); return "Original question:\n"+prompt+"\n\nIndependent answers:\n"+block+"\n\nFind concrete errors, missing dimensions and disagreements. Do not guess authors. Give a revised answer under 200 words." }
 fun finalPrompt():String { val a=answers.entries.joinToString("\n\n"){it.key+":\n"+it.value}; val c=critiques.entries.joinToString("\n\n"){it.key+" critique:\n"+it.value}; return "Original question:\n"+prompt+"\n\nIndependent answers:\n"+a+"\n\nCross-critiques:\n"+c+"\n\nProduce one concise best-supported answer, then list important unresolved disagreements and unknowns. Do not force consensus." }
}
