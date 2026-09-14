/*
  Illustrator JSX - Batch: revectorizar carpeta de logos JPEG
  ==========================================================

  Procesa TODAS las imagenes de una carpeta: vectoriza (trazado de imagen),
  extrusion 3D vectorial opcional, y exporta cada una como vector (SVG/EPS/PDF)
  + PNG con el nombre del archivo original.

  Uso:
    File > Scripts > Other Script... > logo_revector_batch.jsx
    Elige carpeta de ENTRADA (imagenes), carpeta de SALIDA y opciones.

  No necesita documento abierto: cada imagen se procesa en un documento temporal
  que se cierra sin guardar.
*/

#target illustrator

(function () {
  var inFolder = Folder.selectDialog("Carpeta de ENTRADA con las imagenes (JPG/PNG/TIF)");
  if (!inFolder) return;
  var outFolder = Folder.selectDialog("Carpeta de SALIDA para vector + PNG");
  if (!outFolder) return;

  var mode = prompt("Vectorizado:\nBW = blanco y negro\nC = color", "BW");
  if (mode === null) return;
  mode = (String(mode).toUpperCase() === "C") ? "C" : "BW";

  var doExtrude = confirm("Aplicar extrusion 3D vectorial a cada logo?  (Cancelar = solo vectorizar)");
  var steps = 8, off = 1.2;
  if (doExtrude) {
    var sStr = prompt("Profundidad (numero de capas)", "8");
    if (sStr === null) return;
    steps = Math.round(parseFloat(sStr)); if (isNaN(steps) || steps < 1) steps = 8;
    var oStr = prompt("Desplazamiento por capa en puntos", "1.2");
    off = parseFloat(oStr); if (isNaN(off)) off = 1.2;
  }

  var vf = prompt("Formato vectorial:\n1 = SVG\n2 = EPS\n3 = PDF", "1");
  if (vf === null) return;
  vf = String(vf).replace(/\s+/g, "");
  var vectorFormat = (vf === "2") ? "EPS" : (vf === "3") ? "PDF" : "SVG";

  var colorSpace = DocumentColorSpace.RGB;

  // ---- Helpers (auto-contenidos) ----
  function isImage(f) { return /\.(jpg|jpeg|png|gif|tif|tiff|bmp)$/i.test(f.name); }
  function baseFrom(f) { return f.name.replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9_\-]+/g, "_"); }
  function sideColor(cs, level) {
    var v = Math.round(20 + (1 - level) * 60);
    if (cs === DocumentColorSpace.CMYK) { var c = new CMYKColor(); c.cyan = 0; c.magenta = 0; c.yellow = 0; c.black = 100 - Math.round(v / 2.55); return c; }
    var r = new RGBColor(); r.red = v; r.green = v; r.blue = v; return r;
  }
  function recolor(item, color) {
    var tn = item.typename;
    if (tn === "PathItem") { try { item.filled = true; item.fillColor = color; item.stroked = false; } catch (e) {} return; }
    if (tn === "CompoundPathItem") { for (var i = 0; i < item.pathItems.length; i++) recolor(item.pathItems[i], color); return; }
    if (item.pageItems) { for (var j = 0; j < item.pageItems.length; j++) recolor(item.pageItems[j], color); }
  }
  function pseudoExtrude(doc, group, n, dx, dy) {
    var container = doc.groupItems.add(); container.name = "logo_extruido";
    for (var i = n; i >= 1; i--) {
      var copy = group.duplicate(container, ElementPlacement.PLACEATEND);
      copy.translate(dx * i, dy * i);
      recolor(copy, sideColor(doc.documentColorSpace, i / n));
    }
    group.move(container, ElementPlacement.PLACEATBEGINNING);
    return container;
  }
  function exportVector(doc, file, vfmt) {
    if (vfmt === "SVG") {
      var so = new ExportOptionsSVG();
      try { so.embedRasterImages = true; } catch (e) {}
      try { so.coordinatePrecision = 3; } catch (e) {}
      try { so.fontType = SVGFontType.OUTLINEFONT; } catch (e) {}
      doc.exportFile(file, ExportType.SVG, so);
    } else if (vfmt === "EPS") {
      var eo = new EPSSaveOptions();
      try { eo.embedAllFonts = true; } catch (e) {}
      try { eo.cmykPostScript = true; } catch (e) {}
      doc.saveAs(file, eo);
    } else {
      var po = new PDFSaveOptions();
      try { po.preserveEditability = true; } catch (e) {}
      doc.saveAs(file, po);
    }
  }

  var files = inFolder.getFiles(function (f) { return (f instanceof File) && isImage(f); });
  if (!files || files.length === 0) { alert("No encontre imagenes en la carpeta."); return; }
  if (!confirm("Se procesaran " + files.length + " imagenes.\n\nContinuar?")) return;

  var ok = 0, err = 0, log = [];
  for (var k = 0; k < files.length; k++) {
    var imgFile = files[k];
    var base = baseFrom(imgFile);
    try {
      var doc = app.documents.add(colorSpace, 2000, 2000);
      var placed = doc.placedItems.add();
      placed.file = imgFile;

      var toTrace = placed;
      try { placed.embed(); } catch (eE) {}
      if (doc.rasterItems.length > 0) toTrace = doc.rasterItems[0];
      else if (doc.pageItems.length > 0) toTrace = doc.pageItems[0];

      var traceItem = toTrace.trace();
      var opt = traceItem.tracing.tracingOptions;
      try { opt.tracingMode = (mode === "BW") ? TracingModeType.TRACINGMODEBLACKANDWHITE : TracingModeType.TRACINGMODECOLOR; } catch (e) {}
      try { opt.ignoreWhite = true; } catch (e) {}
      try { opt.pathFitting = 1.5; } catch (e) {}
      try { opt.cornerAngle = 15; } catch (e) {}
      if (mode === "BW") { try { opt.threshold = 128; } catch (e) {} }
      else { try { opt.maxColors = 16; } catch (e) {} }

      var vector = traceItem.tracing.expandTracing();
      var finalArt = vector;
      if (doExtrude) { try { finalArt = pseudoExtrude(doc, vector, steps, off, -off); } catch (eX) { finalArt = vector; } }

      var b = finalArt.visibleBounds; var apad = 10;
      doc.artboards[0].artboardRect = [b[0] - apad, b[1] + apad, b[2] + apad, b[3] - apad];

      var pngFile = new File(outFolder.fsName + "/" + base + ".png");
      var vectorFile = new File(outFolder.fsName + "/" + base + "." + vectorFormat.toLowerCase());
      var pngOpt = new ExportOptionsPNG24();
      pngOpt.artBoardClipping = true; pngOpt.transparency = true; pngOpt.horizontalScale = 300; pngOpt.verticalScale = 300;
      doc.exportFile(pngFile, ExportType.PNG24, pngOpt);
      exportVector(doc, vectorFile, vectorFormat);

      doc.close(SaveOptions.DONOTSAVECHANGES);
      ok++;
    } catch (e) {
      err++; log.push(base + ": " + e);
      try { if (app.documents.length && app.activeDocument) app.activeDocument.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
    }
  }

  var msg = "Batch terminado.\n\n" +
    "Procesadas OK: " + ok + "\nErrores: " + err + "\n" +
    "Formato: " + vectorFormat + (doExtrude ? (" + extrusion " + steps) : "") + "\n\n" +
    "Salida:\n" + outFolder.fsName;
  if (log.length) msg += "\n\nFallos:\n" + log.slice(0, 8).join("\n");
  alert(msg);
})();
