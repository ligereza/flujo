/*
  Illustrator JSX - Revectorizar JPEG + extrusion 3D + exportar 2 formatos
  =======================================================================

  Convierte un logo JPEG de baja calidad a vector (trazado de imagen), aplica una
  extrusion 3D vectorial (fiable, sin efectos vivos fragiles) y exporta el
  resultado en DOS formatos: vector (SVG/EPS/PDF) + PNG.

  Uso:
    1. Selecciona la imagen del logo (JPEG colocado o incrustado).
    2. File > Scripts > Other Script... > logo_revector_extrude.jsx
    3. Responde: BW/color, extrusion si/no, profundidad, carpeta y nombre.

  Notas:
    - La extrusion es vectorial (copias apiladas y oscurecidas). Se exporta limpio.
    - Para una extrusion foto-realista usa Efecto > 3D y materiales de forma manual
      sobre el vector que este script deja en tu documento.
    - El logo vectorizado queda en tu documento; la exportacion se hace desde un
      documento temporal para no tocar tus mesas de trabajo.
*/

#target illustrator

(function () {
  if (app.documents.length === 0) { alert("Abre un documento con el logo JPEG."); return; }
  var doc = app.activeDocument;
  if (!doc.selection || doc.selection.length === 0) { alert("Selecciona la imagen del logo (JPEG)."); return; }

  var art = doc.selection[0];
  if (art.typename === "PlacedItem") { try { art.embed(); art = doc.selection[0]; } catch (e) {} }
  if (art.typename !== "RasterItem" && art.typename !== "PlacedItem") {
    alert("El objeto seleccionado no es una imagen. Selecciona el JPEG del logo.");
    return;
  }

  var mode = prompt("Vectorizado:\nBW = blanco y negro (logos de un color)\nC = color", "BW");
  if (mode === null) return;
  mode = (String(mode).toUpperCase() === "C") ? "C" : "BW";

  var doExtrude = confirm("Aplicar extrusion 3D vectorial?  (Cancelar = solo vectorizar)");
  var steps = 8, off = 1.2;
  if (doExtrude) {
    var sStr = prompt("Profundidad (numero de capas de extrusion)", "8");
    if (sStr === null) return;
    steps = Math.round(parseFloat(sStr)); if (isNaN(steps) || steps < 1) steps = 8;
    var oStr = prompt("Desplazamiento por capa en puntos", "1.2");
    off = parseFloat(oStr); if (isNaN(off)) off = 1.2;
  }

  var outFolder = Folder.selectDialog("Carpeta de salida para SVG + PNG");
  if (!outFolder) return;
  var baseName = prompt("Nombre base de archivo", "logo_vector");
  if (baseName === null) return;
  baseName = String(baseName).replace(/[^A-Za-z0-9_\-]+/g, "_"); if (!baseName) baseName = "logo_vector";

  var vf = prompt("Formato vectorial a exportar junto al PNG:\n1 = SVG\n2 = EPS\n3 = PDF", "1");
  if (vf === null) return;
  vf = String(vf).replace(/\s+/g, "");
  var vectorFormat = (vf === "2") ? "EPS" : (vf === "3") ? "PDF" : "SVG";

  // ---------- Trazado de imagen ----------
  var traceItem;
  try { traceItem = art.trace(); }
  catch (e) {
    alert("No pude iniciar el trazado automatico: " + e + "\n\nAlternativa manual:\nObjeto > Trazado de imagen > Crear, luego Expandir.");
    return;
  }
  var t = traceItem.tracing;
  var opt = t.tracingOptions;
  try { opt.tracingMode = (mode === "BW") ? TracingModeType.TRACINGMODEBLACKANDWHITE : TracingModeType.TRACINGMODECOLOR; } catch (e) {}
  try { opt.ignoreWhite = true; } catch (e) {}
  try { opt.pathFitting = 1.5; } catch (e) {}
  try { opt.cornerAngle = 15; } catch (e) {}
  if (mode === "BW") { try { opt.threshold = 128; } catch (e) {} }
  else { try { opt.maxColors = 16; } catch (e) {} }

  var vector;
  try { vector = t.expandTracing(); } // GroupItem
  catch (e) { alert("No pude expandir el trazado: " + e); return; }

  // ---------- Extrusion vectorial ----------
  function sideColor(level) { // level 1 = capa mas lejana (mas oscura)
    var v = Math.round(20 + (1 - level) * 60); // 20 (oscuro) .. 80 (mas claro)
    if (doc.documentColorSpace === DocumentColorSpace.CMYK) {
      var c = new CMYKColor(); c.cyan = 0; c.magenta = 0; c.yellow = 0;
      c.black = 100 - Math.round(v / 2.55); return c;
    }
    var r = new RGBColor(); r.red = v; r.green = v; r.blue = v; return r;
  }
  function recolor(item, color) {
    var tn = item.typename;
    if (tn === "PathItem") { try { item.filled = true; item.fillColor = color; item.stroked = false; } catch (e) {} return; }
    if (tn === "CompoundPathItem") { for (var i = 0; i < item.pathItems.length; i++) recolor(item.pathItems[i], color); return; }
    if (item.pageItems) { for (var j = 0; j < item.pageItems.length; j++) recolor(item.pageItems[j], color); }
  }
  function pseudoExtrude(group, n, dx, dy) {
    var container = doc.groupItems.add();
    container.name = "logo_extruido";
    for (var i = n; i >= 1; i--) {
      var copy = group.duplicate(container, ElementPlacement.PLACEATEND);
      copy.translate(dx * i, dy * i);
      recolor(copy, sideColor(i / n));
    }
    group.move(container, ElementPlacement.PLACEATBEGINNING); // cara frontal arriba
    return container;
  }

  var finalArt = vector;
  if (doExtrude) {
    try { finalArt = pseudoExtrude(vector, steps, off, -off); }
    catch (e) { alert("No pude crear la extrusion (" + e + "). Continuo solo con el vector."); finalArt = vector; }
  }

  // ---------- Exportar vector + PNG desde documento temporal ----------
  var apad = 10;
  var pngFile = new File(outFolder.fsName + "/" + baseName + ".png");
  var vectorFile = new File(outFolder.fsName + "/" + baseName + "." + vectorFormat.toLowerCase());

  function exportVector(tmpDoc, file, vfmt) {
    if (vfmt === "SVG") {
      var so = new ExportOptionsSVG();
      try { so.embedRasterImages = true; } catch (e) {}
      try { so.coordinatePrecision = 3; } catch (e) {}
      try { so.fontType = SVGFontType.OUTLINEFONT; } catch (e) {}
      tmpDoc.exportFile(file, ExportType.SVG, so);
    } else if (vfmt === "EPS") {
      var eo = new EPSSaveOptions();
      try { eo.embedAllFonts = true; } catch (e) {}
      try { eo.cmykPostScript = true; } catch (e) {}
      tmpDoc.saveAs(file, eo);
    } else {
      var po = new PDFSaveOptions();
      try { po.preserveEditability = true; } catch (e) {}
      tmpDoc.saveAs(file, po);
    }
  }

  try {
    var b = finalArt.visibleBounds; // [L,T,R,B]
    var w = (b[2] - b[0]) + apad * 2, h = (b[1] - b[3]) + apad * 2;
    var tmp = app.documents.add(doc.documentColorSpace, Math.max(1, w), Math.max(1, h));
    var copy = finalArt.duplicate(tmp.activeLayer, ElementPlacement.PLACEATEND);
    var cb = copy.visibleBounds;
    tmp.artboards[0].artboardRect = [cb[0] - apad, cb[1] + apad, cb[2] + apad, cb[3] - apad];

    var pngOpt = new ExportOptionsPNG24();
    pngOpt.artBoardClipping = true; pngOpt.transparency = true; pngOpt.horizontalScale = 300; pngOpt.verticalScale = 300;
    tmp.exportFile(pngFile, ExportType.PNG24, pngOpt);

    exportVector(tmp, vectorFile, vectorFormat);

    tmp.close(SaveOptions.DONOTSAVECHANGES);
    app.activeDocument = doc;
  } catch (e) {
    alert("Vectorizado listo, pero fallo la exportacion automatica: " + e + "\n\nExporta manualmente con Archivo > Exportar.");
    return;
  }

  alert(
    "Listo.\n\n" +
    "Vectorizado: " + (mode === "BW" ? "blanco y negro" : "color") + "\n" +
    "Extrusion: " + (doExtrude ? ("si (" + steps + " capas)") : "no") + "\n" +
    "Formato vectorial: " + vectorFormat + "\n\n" +
    "Exportado:\n" + vectorFile.fsName + "\n" + pngFile.fsName
  );
})();
