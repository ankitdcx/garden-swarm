package org.garden.aicouncil
import android.app.*;import android.os.*;import android.content.*;import android.provider.Settings;import android.widget.*
class MainActivity:Activity(){
 override fun onCreate(b:Bundle?){super.onCreate(b)
  val root=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(28,28,28,28)}
  val p=EditText(this).apply{hint="Ask all AIs…";minLines=4}
  val status=TextView(this).apply{text="Idle"}
  val enable=Button(this).apply{text="ENABLE AUTOMATION";setOnClickListener{startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))}}
  val ask=Button(this).apply{text="ASK ALL";setOnClickListener{
   CouncilState.targets.clear()
   val all=listOf(CouncilState.Target("ChatGPT","com.openai.chatgpt"),CouncilState.Target("Gemini","com.google.android.apps.bard"),CouncilState.Target("Claude","com.anthropic.claude"),CouncilState.Target("Grok","ai.x.grok"),CouncilState.Target("DeepSeek","com.deepseek.chat"))
   all.filter{packageManager.getLaunchIntentForPackage(it.pkg)!=null}.forEach{CouncilState.targets.add(it)}
   if(CouncilState.targets.isEmpty()){status.text="No configured AI apps detected";return@setOnClickListener}
   CouncilState.reset(p.text.toString());status.text="Running "+CouncilState.targets.size+" apps…"
   startActivity(packageManager.getLaunchIntentForPackage(CouncilState.targets.first().pkg))
  }}
  val stop=Button(this).apply{text="STOP / TAKE OVER";setOnClickListener{CouncilState.stop();status.text="Stopped"}}
  val results=Button(this).apply{text="SHOW COLLECTED";setOnClickListener{
   val msg=CouncilState.answers.entries.joinToString("\n\n"){it.key+":\n"+it.value}
   AlertDialog.Builder(this@MainActivity).setTitle("Collected").setMessage(msg).setPositiveButton("OK",null).show()
  }}
  listOf(p,enable,ask,stop,status,results).forEach(root::addView);setContentView(root)
 }
}
