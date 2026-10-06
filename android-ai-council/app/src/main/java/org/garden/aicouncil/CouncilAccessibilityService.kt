package org.garden.aicouncil
import android.accessibilityservice.AccessibilityService
import android.content.*;import android.os.*;import android.view.accessibility.AccessibilityEvent;import android.view.accessibility.AccessibilityNodeInfo
class CouncilAccessibilityService:AccessibilityService(){
 private val h=Handler(Looper.getMainLooper());private var lastText="";private var stable=0
 override fun onAccessibilityEvent(e:AccessibilityEvent?){
  if(!CouncilState.running||CouncilState.stopRequested||CouncilState.index>=CouncilState.targets.size)return
  val t=CouncilState.targets[CouncilState.index];if(e?.packageName?.toString()!=t.pkg)return
  h.removeCallbacksAndMessages(null);h.postDelayed({step(t)},700)
 }
 private fun nodes(root:AccessibilityNodeInfo?):List<AccessibilityNodeInfo>{if(root==null)return emptyList();val out=mutableListOf<AccessibilityNodeInfo>();fun walk(n:AccessibilityNodeInfo){out.add(n);for(i in 0 until n.childCount)n.getChild(i)?.let{walk(it)}};walk(root);return out}
 private fun step(t:CouncilState.Target){
  if(CouncilState.stopRequested)return
  val ns=nodes(rootInActiveWindow);val editable=ns.lastOrNull{it.isEditable}
  if(editable!=null&&editable.text.toString().isBlank()){val b=Bundle();b.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,CouncilState.prompt);editable.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,b);h.postDelayed({clickSend(ns)},500);return}
  val text=ns.filter{!it.isEditable&&it.text!=null}.joinToString("\n"){it.text.toString()}.trim()
  if(text.length>lastText.length+20){lastText=text;stable=0;h.postDelayed({step(t)},1800);return}
  if(text==lastText&&text.length>80)stable++ else stable=0;lastText=text
  if(stable>=2){CouncilState.answers[t.name]=extract(text,CouncilState.prompt);advance()}else h.postDelayed({step(t)},1800)
 }
 private fun clickSend(ns:List<AccessibilityNodeInfo>){val n=ns.firstOrNull{(it.contentDescription?.toString()?:"").contains("send",true)||(it.text?.toString()?:"").equals("Send",true)};n?.performAction(AccessibilityNodeInfo.ACTION_CLICK);h.postDelayed({if(CouncilState.index<CouncilState.targets.size)step(CouncilState.targets[CouncilState.index])},2000)}
 private fun extract(all:String,p:String):String{return all.substringAfterLast(p,all).takeLast(12000).trim()}
 private fun advance(){stable=0;lastText="";CouncilState.index++;if(CouncilState.index>=CouncilState.targets.size){CouncilState.running=false;startActivity(Intent(this,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));return};packageManager.getLaunchIntentForPackage(CouncilState.targets[CouncilState.index].pkg)?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)?.let{startActivity(it)}}
 override fun onInterrupt(){CouncilState.stop()}
}
