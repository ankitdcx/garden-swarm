package org.garden.aicouncil
object CouncilState {
 @Volatile var running=false; @Volatile var stopRequested=false; @Volatile var prompt=""; @Volatile var index=0
 val targets=mutableListOf<Target>(); val answers=linkedMapOf<String,String>()
 data class Target(val name:String,val pkg:String)
 fun reset(p:String){prompt=p;index=0;answers.clear();stopRequested=false;running=true}
 fun stop(){stopRequested=true;running=false}
}
