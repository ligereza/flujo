/*
  Illustrator JSX - Titulos a fotos individuales
  ==============================================

  Toma un bloque de texto (uno o varios marcos de texto seleccionados) y exporta
  CADA linea como una imagen individual (PNG o JPG), conservando fuente, tamano y
  color del marco de origen.

  Uso:
    1. Selecciona el/los marco(s) de texto con tus titulos (una linea = un titulo).
    2. File > Scripts > Other Script... > titles_to_photos.jsx
    3. Responde formato, escala, transparencia y margen.
    4. Elige carpeta de salida.

  No modifica tu documento original: cada titulo se renderiza en un documento
  temporal que se cierra sin guardar.
*/

#target illustrator

(function () {
  if (app.documents.length === 0) { alert("Abre un documento con tu bloque de texto."); return; }
  var doc = app.activeDocument;

  // ---- Origen: marcos de texto seleccionados ----
  var frames = [];
  if (doc.selection && doc.selection.length) {
    for (var i = 0; i < doc.selection.length; i++) {
      if (doc.selection[i].typename === "TextFrame") frames.push(doc.selection[i]);
    }
  }
  if (frames.length === 0) {
    alert("Selecciona el bloque de texto (uno o varios marcos de texto) y vuelve a ejecutar.");
    return;
  }

  // ---- Opciones ----
  var fmt = prompt("Formato de salida: PNG o JPG", "PNG");
  if (fmt === null) return;
  fmt = (String(fmt).toUpperCase() === "JPG") ? "JPG" : "PNG";

  var scaleStr = prompt("Escala de exportacion en % (100 = 1x, 300 = 3x)", "300");
  if (scaleStr === null) return;
  var scale = parseFloat(scaleStr); if (isNaN(scale) || scale <= 0) scale = 300;

  var transparent = (fmt === "PNG") ? confirm("Fondo transparente?  (Cancelar = fondo blanco)") : false;

  var padStr = prompt("Margen alrededor de cada titulo en puntos", "24");
  var pad = parseFloat(padStr); if (isNaN(pad)) pad = 24;

  var outFolder = Folder.selectDialog("Elige la carpeta de salida para los titulos");
  if (!outFolder) return;

  var cs = doc.documentColorSpace;

  // ---- Helpers ----
  function safe(s) {
    s = String(s).replace(/[\\\/:*?"<>|\r\n\t]+/g, "_").replace(/\s+/g, "_");
    if (s.length > 40) s = s.substr(0, 40);
    if (s.length === 0) s = "titulo";
    return s;
  }
  function pad2(n) { n = String(n); while (n.length < 2) n = "0" + n; return n; }
  function cloneColor(src) {
    if (!src) return null;
    var tn = src.typename;
    if (tn === "RGBColor") { var r = new RGBColor(); r.red = src.red; r.green = src.green; r.blue = src.blue; return r; }
    if (tn === "CMYKColor") { var c = new CMYKColor(); c.cyan = src.cyan; c.magenta = src.magenta; c.yellow = src.yellow; c.black = src.black; return c; }
    if (tn === "GrayColor") { var g = new GrayColor(); g.gray = src.gray; return g; }
    return src; // Spot u otros: se reutiliza tal cual
  }

  // ---- Reunir titulos (linea a linea) con atributos del marco ----
  var jobs = [];
  for (var f = 0; f < frames.length; f++) {
    var fr = frames[f];
    var attrs = { size: 100, font: null, fill: null };
    try {
      var ca = fr.textRange.characterAttributes;
      try { attrs.size = ca.size; } catch (e1) {}
      try { attrs.font = ca.textFont; } catch (e2) {}
      try { attrs.fill = cloneColor(ca.fillColor); } catch (e3) {}
    } catch (e0) {}
    var parts = String(fr.contents).split(/[\r\n]+/);
    for (var p = 0; p < parts.length; p++) {
      var ln = parts[p].replace(/^\s+|\s+$/g, "");
      if (ln.length > 0) jobs.push({ line: ln, attrs: attrs });
    }
  }
  if (jobs.length === 0) { alert("No encontre lineas de texto en la seleccion."); return; }

  if (!confirm("Se exportaran " + jobs.length + " titulos como " + fmt + ".\n\nContinuar?")) return;

  // ---- Exportar cada titulo en un documento temporal ----
  function exportOne(job, idx) {
    var tmp = app.documents.add(cs, 4000, 2000);
    var tf = tmp.textFrames.pointText([200, 1000]);
    tf.contents = job.line;
    var rng = tf.textRange;
    try { if (job.attrs.font) rng.characterAttributes.textFont = job.attrs.font; } catch (e1) {}
    try { rng.characterAttributes.size = job.attrs.size; } catch (e2) {}
    try { if (job.attrs.fill) rng.characterAttributes.fillColor = cloneColor(job.attrs.fill); } catch (e3) {}

    try { tmp.selection = null; } catch (e4) {}
    var b = tf.visibleBounds; // [left, top, right, bottom]
    tmp.artboards[0].artboardRect = [b[0] - pad, b[1] + pad, b[2] + pad, b[3] - pad];

    var base = pad2(idx) + "_" + safe(job.line);
    if (fmt === "PNG") {
      var o = new ExportOptionsPNG24();
      o.artBoardClipping = true; o.horizontalScale = scale; o.verticalScale = scale;
      o.transparency = transparent;
      if (!transparent) { o.matte = true; var w = new RGBColor(); w.red = 255; w.green = 255; w.blue = 255; o.matteColor = w; }
      tmp.exportFile(new File(outFolder.fsName + "/" + base + ".png"), ExportType.PNG24, o);
    } else {
      var j = new ExportOptionsJPEG();
      j.artBoardClipping = true; j.horizontalScale = scale; j.verticalScale = scale; j.qualitySetting = 100;
      tmp.exportFile(new File(outFolder.fsName + "/" + base + ".jpg"), ExportType.JPEG, j);
    }
    tmp.close(SaveOptions.DONOTSAVECHANGES);
  }

  var ok = 0, err = 0;
  for (var k = 0; k < jobs.length; k++) {
    try { exportOne(jobs[k], k + 1); ok++; }
    catch (e) { err++; }
  }
  try { app.activeDocument = doc; } catch (e) {}

  alert("Titulos a fotos: terminado.\n\nExportados: " + ok + "\nErrores: " + err + "\n\nCarpeta:\n" + outFolder.fsName);
})();
