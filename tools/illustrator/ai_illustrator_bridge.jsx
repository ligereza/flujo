#target illustrator
/*
  ai_illustrator_bridge.jsx  --  Puente JSON agente <-> Illustrator (Cauce / taller-svg-rd)

  Cierra la comunicacion sin pasar el .ai ni el SVG completo:
    MODE="export"  -> vuelca el doc activo a  ~/Desktop/ai_illustrator/state.json
                      (el agente lo lee: nombre, texto, x/y, size, font, fill por capa)
    MODE="apply"   -> lee  ~/Desktop/ai_illustrator/ops.json  y aplica los cambios

  Requisito: NOMBRA tus capas/frames de texto (se targetea por nombre).
  Uso: Illustrator > Archivo > Secuencias de comandos > Otra secuencia... y elige este .jsx
       1) MODE="export", corre -> pasa state.json al agente
       2) el agente devuelve ops.json (mismo formato que ai_illustrator_ops.example.json)
       3) MODE="apply", corre -> Illustrator aplica
*/

var MODE = "export";   // "export" | "apply"

// ==========================================================================
// LECTURA DE MODO DESDE ARCHIVO DE CONFIGURACION O DIALOGO
// ==========================================================================
function getModeFromConfig() {
  var ioFolder = new Folder(Folder.desktop + "/ai_illustrator");
  if (!ioFolder.exists) ioFolder.create();

  // Intentar leer config.json primero
  var configFile = new File(ioFolder.fsName + "/config.json");
  if (configFile.exists) {
    try {
      configFile.encoding = "UTF-8";
      configFile.open("r");
      var content = configFile.read();
      configFile.close();
      var cfg = (typeof JSON !== 'undefined' && JSON.parse) ? JSON.parse(content) : eval('(' + content + ')');
      if (cfg.mode && (cfg.mode === "export" || cfg.mode === "apply")) {
        return cfg.mode;
      }
    } catch(e) {}
  }

  // Si no hay config o mode invalido, preguntar al usuario
  var modePrompt = prompt(
    "Selecciona modo de operacion:\\n\\n" +
    "  export = Exportar estado del documento a state.json\\n\\n" +
    "  apply  = Aplicar cambios desde ops.json\\n\\n" +
    "Deja vacio para usar 'export' por defecto.",
    "export"
  );

  if (modePrompt === null) return "export"; // Cancel = default
  modePrompt = String(modePrompt).toLowerCase().trim();
  if (modePrompt === "export" || modePrompt === "apply") return modePrompt;
  if (modePrompt === "") return "export";

  // Entrada invalida, fallback a export
  alert("Modo no reconocido, usando 'export' por defecto.");
  return "export";
}

var MODE = getModeFromConfig();

var IO = new Folder(Folder.desktop + "/ai_illustrator");
if (!IO.exists) IO.create();

function readFile(f){ f.encoding="UTF-8"; f.open("r"); var s=f.read(); f.close(); return s; }
function writeFile(f, s){ f.encoding="UTF-8"; f.open("w"); f.write(s); f.close(); }
function esc(s){ return String(s).replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/[\r\n]+/g,"\\n"); }
function pad2(x){ x=Math.round(x).toString(16); return x.length<2?"0"+x:x; }
function toHex(c){ try { return "#"+pad2(c.red)+pad2(c.green)+pad2(c.blue); } catch(e){ return "#000000"; } }
function hexColor(hex){ hex=String(hex).replace("#",""); var c=new RGBColor();
  c.red=parseInt(hex.substr(0,2),16); c.green=parseInt(hex.substr(2,2),16); c.blue=parseInt(hex.substr(4,2),16); return c; }
function frameName(tf){
  if (tf.name && tf.name.length) return tf.name;
  try { if (tf.layer && tf.layer.name) return tf.layer.name; } catch(e){}
  return "";
}

function doExport(){
  var d = app.activeDocument, rows = [];
  for (var i=0;i<d.textFrames.length;i++){
    var t=d.textFrames[i], ca;
    try { ca=t.textRange.characterAttributes; } catch(e){ continue; }
    var fill="#000000", font="", size=0;
    try{ fill=toHex(ca.fillColor); }catch(e){}
    try{ font=ca.textFont.name; }catch(e){}
    try{ size=Math.round(ca.size*100)/100; }catch(e){}
    rows.push('{"name":"'+esc(frameName(t))+'","content":"'+esc(t.contents)+'",'+
      '"x":'+Math.round(t.position[0])+',"y":'+Math.round(t.position[1])+
      ',"size":'+size+',"font":"'+esc(font)+'","fill":"'+fill+'"}');
  }
  var json = '{"doc":"'+esc(d.name)+'","unit":"pt","texts":['+rows.join(",")+']}';
  var f=new File(IO.fsName+"/state.json"); writeFile(f, json);
  alert("EXPORT ok: "+rows.length+" textos ->\n"+f.fsName);
}

function findByName(name){
  var d=app.activeDocument, hits=[];
  for (var i=0;i<d.textFrames.length;i++){ if (frameName(d.textFrames[i])==name) hits.push(d.textFrames[i]); }
  return hits;
}

// target por NOMBRE (o.target) o por CONTENIDO actual (o.find = subcadena).
// 'find' sirve cuando muchos frames comparten capa/nombre (ej. plantilla "CAMBIOS").
function findTargets(o){
  if (o.find != null){
    var d=app.activeDocument, hits=[], q=String(o.find).replace(/[\r\n]+/g,"\n");
    for (var i=0;i<d.textFrames.length;i++){
      if (String(d.textFrames[i].contents).replace(/[\r\n]+/g,"\n").indexOf(q) >= 0) hits.push(d.textFrames[i]);
    }
    return hits;
  }
  return findByName(o.target);
}

function doApply(){
  var f=new File(IO.fsName+"/ops.json");
  if(!f.exists){ alert("No existe:\n"+f.fsName); return; }
  var data; try { data = (typeof JSON !== 'undefined' && JSON.parse) ? JSON.parse(readFile(f)) : eval('(' + readFile(f) + ')'); } catch(e){ alert("ops.json invalido: "+e); return; }
  var ops = data.ops || [], done=0, miss=0;
  for (var i=0;i<ops.length;i++){
    var o=ops[i];
    if(o.op=="addText"){
      try {
        var nt=app.activeDocument.textFrames.add();
        nt.contents=o.content||"texto"; nt.position=[o.x||0, o.y||0];
        if(o.name) nt.name=o.name;
        var nca=nt.textRange.characterAttributes;
        if(o.size) nca.size=o.size;
        if(o.font){ try{ nca.textFont=textFonts.getByName(o.font); }catch(e){} }
        if(o.fill) nca.fillColor=hexColor(o.fill);
        done++;
      } catch(e){}
      continue;
    }
    var tfs=findTargets(o);
    if(!tfs.length){ miss++; continue; }
    for (var j=0;j<tfs.length;j++){
      var t=tfs[j], ca=t.textRange.characterAttributes;
      try {
        if(o.op=="setText") t.contents=o.content;
        else if(o.op=="setSize") ca.size=o.size;
        else if(o.op=="setFill") ca.fillColor=hexColor(o.fill);
        else if(o.op=="setFont") ca.textFont=textFonts.getByName(o.font);
        else if(o.op=="move") t.position=[o.x, o.y];
        done++;
      } catch(e){}
    }
  }
  app.redraw();
  alert("APPLY ok: "+done+" ops aplicadas, "+miss+" targets no encontrados.");
}

if (MODE=="export") doExport(); else doApply();