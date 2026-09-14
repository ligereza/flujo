#target photoshop
/*
  ai_photoshop_bridge.jsx -- Puente JSON agente <-> Photoshop (mismo contrato que el de Illustrator).
  MODE="export" -> ~/Desktop/ai_illustrator/state.json ; MODE="apply" -> lee ops.json
  Targetea capas de texto por NOMBRE. Ops: setText, setSize, setFill.
*/
var MODE = "export";   // "export" | "apply"
var IO = new Folder(Folder.desktop + "/ai_illustrator"); if (!IO.exists) IO.create();

function readFile(f){ f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
function writeFile(f,s){ f.encoding="UTF-8"; f.open("w"); f.write(s); f.close(); }
function esc(s){ return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/[\r\n]+/g,"\\n"); }
function pad2(x){ x=Math.round(x).toString(16); return x.length<2?"0"+x:x; }
function hexColor(hex){ hex=String(hex).replace("#",""); var c=new SolidColor();
  c.rgb.red=parseInt(hex.substr(0,2),16); c.rgb.green=parseInt(hex.substr(2,2),16); c.rgb.blue=parseInt(hex.substr(4,2),16); return c; }

function collect(container, arr){
  for (var i=0;i<container.artLayers.length;i++){
    var L=container.artLayers[i];
    if (L.kind==LayerKind.TEXT){
      var ti=L.textItem, c=ti.color.rgb;
      arr.push('{"name":"'+esc(L.name)+'","content":"'+esc(ti.contents)+'","size":'+Math.round(ti.size)+
        ',"fill":"#'+pad2(c.red)+pad2(c.green)+pad2(c.blue)+'"}');
    }
  }
  for (var g=0;g<container.layerSets.length;g++) collect(container.layerSets[g], arr);
}
function findLayer(container, name){
  for (var i=0;i<container.artLayers.length;i++) if (container.artLayers[i].name==name) return container.artLayers[i];
  for (var g=0;g<container.layerSets.length;g++){ var r=findLayer(container.layerSets[g],name); if(r) return r; }
  return null;
}
function doExport(){
  var d=app.activeDocument, arr=[]; collect(d, arr);
  writeFile(new File(IO.fsName+"/state.json"), '{"doc":"'+esc(d.name)+'","app":"photoshop","texts":['+arr.join(",")+']}');
  alert("PS EXPORT ok: "+arr.length+" capas de texto");
}
function doApply(){
  var f=new File(IO.fsName+"/ops.json"); if(!f.exists){ alert("No existe:\n"+f.fsName); return; }
  var data; try{ data=eval("("+readFile(f)+")"); }catch(e){ alert("ops.json invalido: "+e); return; }
  var ops=data.ops||[], done=0, miss=0, d=app.activeDocument;
  for (var i=0;i<ops.length;i++){
    var o=ops[i], L=findLayer(d,o.target); if(!L){ miss++; continue; }
    var ti=L.textItem;
    try {
      if(o.op=="setText") ti.contents=o.content;
      else if(o.op=="setSize") ti.size=o.size;
      else if(o.op=="setFill") ti.color=hexColor(o.fill);
      done++;
    } catch(e){}
  }
  alert("PS APPLY ok: "+done+" ops, "+miss+" no encontrados");
}
if (MODE=="export") doExport(); else doApply();
