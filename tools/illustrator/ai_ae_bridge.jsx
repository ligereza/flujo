/*
  ai_ae_bridge.jsx -- Puente JSON agente <-> After Effects (comp activa, capas de texto).
  MODE="export" -> ~/Desktop/ai_illustrator/state.json ; MODE="apply" -> lee ops.json
  Targetea capas por NOMBRE. Ops: setText, setSize.
  Correr desde AE: Archivo > Scripts > Run Script File...
*/
var MODE = "export";   // "export" | "apply"
var IO = new Folder(Folder.desktop + "/ai_illustrator"); if (!IO.exists) IO.create();

function readFile(f){ f.open("r"); var s=f.read(); f.close(); return s; }
function writeFile(f,s){ f.open("w"); f.write(s); f.close(); }
function esc(s){ return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/[\r\n]+/g,"\\n"); }
function comp(){
  var c=app.project.activeItem;
  if (!(c && c instanceof CompItem)){ alert("Abre/selecciona una composicion"); return null; }
  return c;
}
function doExport(){
  var c=comp(); if(!c) return; var arr=[];
  for (var i=1;i<=c.numLayers;i++){
    var L=c.layer(i), sp=L.property("Source Text");
    if (sp){ var td=sp.value; arr.push('{"name":"'+esc(L.name)+'","content":"'+esc(td.text)+'","size":'+Math.round(td.fontSize)+'}'); }
  }
  writeFile(new File(IO.fsName+"/state.json"), '{"comp":"'+esc(c.name)+'","app":"aftereffects","texts":['+arr.join(",")+']}');
  alert("AE EXPORT ok: "+arr.length+" capas de texto");
}
function doApply(){
  var c=comp(); if(!c) return;
  var f=new File(IO.fsName+"/ops.json"); if(!f.exists){ alert("No existe:\n"+f.fsName); return; }
  var data; try{ data=eval("("+readFile(f)+")"); }catch(e){ alert("ops.json invalido: "+e); return; }
  var ops=data.ops||[], done=0, miss=0;
  app.beginUndoGroup("AI ops");
  for (var i=0;i<ops.length;i++){
    var o=ops[i], L=null;
    for (var k=1;k<=c.numLayers;k++) if (c.layer(k).name==o.target){ L=c.layer(k); break; }
    if(!L){ miss++; continue; }
    var sp=L.property("Source Text"); if(!sp){ miss++; continue; }
    try {
      var td=sp.value;
      if(o.op=="setText") td.text=o.content;
      else if(o.op=="setSize") td.fontSize=o.size;
      sp.setValue(td); done++;
    } catch(e){}
  }
  app.endUndoGroup();
  alert("AE APPLY ok: "+done+" ops, "+miss+" no encontrados");
}
if (MODE=="export") doExport(); else doApply();
