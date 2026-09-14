/*
  After Effects JSX - Titulos a composiciones
  ===========================================

  Toma un bloque de texto (un titulo por linea) y crea UNA composicion por titulo,
  con una capa de texto centrada y un fundido de entrada/salida. Opcion para
  anadir todas las comps a la cola de render.

  Uso:
    1. En After Effects: File > Scripts > Run Script File... > titles_to_comps.jsx
    2. Elige un .txt (un titulo por linea) o escribe los titulos separados por ";".
    3. Responde tamano, fps, duracion y tamano de fuente.
*/

#target aftereffects

(function () {
  var proj = app.project;
  if (!proj) { app.newProject(); proj = app.project; }

  // ---- Titulos ----
  var titles = [];
  var f = File.openDialog("Elige un .txt (un titulo por linea). Cancelar = escribir a mano.",
                          "Texto:*.txt;Todos:*.*");
  if (f) {
    f.open("r"); var content = f.read(); f.close();
    var lines = content.split(/[\r\n]+/);
    for (var i = 0; i < lines.length; i++) {
      var ln = lines[i].replace(/^\s+|\s+$/g, "");
      if (ln.length > 0) titles.push(ln);
    }
  } else {
    var raw = prompt("Escribe los titulos separados por ;  (punto y coma)", "Titulo 1; Titulo 2; Titulo 3");
    if (raw === null) return;
    var parts = String(raw).split(/;/);
    for (var j = 0; j < parts.length; j++) {
      var p = parts[j].replace(/^\s+|\s+$/g, "");
      if (p.length > 0) titles.push(p);
    }
  }
  if (titles.length === 0) { alert("No hay titulos."); return; }

  // ---- Parametros ----
  function askInt(msg, def) { var s = prompt(msg, String(def)); if (s === null) return null; var v = parseInt(s, 10); return isNaN(v) ? def : v; }
  function askNum(msg, def) { var s = prompt(msg, String(def)); if (s === null) return null; var v = parseFloat(s); return isNaN(v) ? def : v; }

  var W = askInt("Ancho px", 1920); if (W === null) return;
  var H = askInt("Alto px", 1080); if (H === null) return;
  var FPS = askNum("FPS", 30); if (FPS === null) return;
  var DUR = askNum("Duracion por comp (segundos)", 3); if (DUR === null) return;
  var FS = askNum("Tamano de fuente px", 120); if (FS === null) return;
  var addRQ = confirm("Anadir cada comp a la cola de render?  (Cancelar = no)");

  function pad2(n) { n = String(n); while (n.length < 2) n = "0" + n; return n; }

  app.beginUndoGroup("Titulos a comps");
  var folder = proj.items.addFolder("Titulos");
  var made = 0;

  for (var t = 0; t < titles.length; t++) {
    var name = "Titulo_" + pad2(t + 1);
    var comp = proj.items.addComp(name, W, H, 1.0, DUR, FPS);
    comp.parentFolder = folder;

    var layer = comp.layers.addText(titles[t]);
    var srcProp = layer.property("Source Text");
    var td = srcProp.value;
    td.resetCharStyle();
    td.fontSize = FS;
    td.applyFill = true;
    td.fillColor = [1, 1, 1];
    td.applyStroke = false;
    try { td.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (e) {}
    srcProp.setValue(td);

    // Centrar
    try {
      var rect = layer.sourceRectAtTime(0, false);
      layer.property("Anchor Point").setValue([rect.left + rect.width / 2, rect.top + rect.height / 2]);
      layer.property("Position").setValue([W / 2, H / 2]);
    } catch (e) {}

    // Fundido de entrada/salida
    try {
      var op = layer.property("Opacity");
      var fin = Math.min(0.5, DUR / 4), fout = Math.min(0.5, DUR / 4);
      op.setValueAtTime(0, 0);
      op.setValueAtTime(fin, 100);
      op.setValueAtTime(DUR - fout, 100);
      op.setValueAtTime(DUR, 0);
    } catch (e) {}

    if (addRQ) { try { proj.renderQueue.items.add(comp); } catch (e) {} }
    made++;
  }

  app.endUndoGroup();
  alert("Titulos a comps: terminado.\n\nComps creadas: " + made + (addRQ ? "\nAnadidas a la cola de render." : ""));
})();
