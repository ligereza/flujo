/*
  Photoshop JSX - Capas a fotos individuales
  ==========================================

  Exporta cada capa de nivel superior del documento abierto como un PNG
  individual, recortado a su contenido y con transparencia. Opcion para exportar
  solo capas de texto.

  Uso:
    1. Abre tu documento en Photoshop.
    2. File > Scripts > Browse... > layers_to_photos.jsx
    3. Responde: solo texto?  carpeta de salida?  escala?

  No modifica tu documento: cada capa se exporta desde un duplicado temporal que
  se cierra sin guardar.
*/

#target photoshop

(function () {
  if (app.documents.length === 0) { alert("Abre un documento de Photoshop."); return; }
  var src = app.activeDocument;

  var onlyText = confirm("Exportar SOLO capas de texto?  (Cancelar = todas las capas de nivel superior)");
  var outFolder = Folder.selectDialog("Carpeta de salida para las capas");
  if (!outFolder) return;
  var scaleStr = prompt("Escala de exportacion en % (100 = tamano actual)", "100");
  var scale = parseFloat(scaleStr); if (isNaN(scale) || scale <= 0) scale = 100;

  function safe(s) {
    s = String(s).replace(/[\\\/:*?"<>|\r\n\t]+/g, "_").replace(/\s+/g, "_");
    if (s.length > 40) s = s.substr(0, 40);
    if (s.length === 0) s = "capa";
    return s;
  }
  function pad2(n) { n = String(n); while (n.length < 2) n = "0" + n; return n; }

  // ---- Capas objetivo (nivel superior) ----
  var targets = [];
  for (var i = 0; i < src.layers.length; i++) {
    var ly = src.layers[i];
    if (onlyText) {
      if (ly.typename === "ArtLayer" && ly.kind === LayerKind.TEXT) targets.push(i);
    } else {
      targets.push(i);
    }
  }
  if (targets.length === 0) { alert("No encontre capas para exportar."); return; }

  var prevUnits = app.preferences.rulerUnits;
  app.preferences.rulerUnits = Units.PIXELS;

  var ok = 0, err = 0;
  for (var k = 0; k < targets.length; k++) {
    var idx = targets[k];
    var name = src.layers[idx].name;
    try {
      var dup = src.duplicate();
      app.activeDocument = dup;
      for (var j = 0; j < dup.layers.length; j++) dup.layers[j].visible = (j === idx);
      try { dup.trim(TrimType.TRANSPARENT, true, true, true, true); } catch (eT) {}
      if (scale !== 100) {
        try {
          dup.resizeImage(UnitValue(dup.width.as("px") * scale / 100, "px"),
                          UnitValue(dup.height.as("px") * scale / 100, "px"),
                          null, ResampleMethod.BICUBIC);
        } catch (eR) {}
      }
      var file = new File(outFolder.fsName + "/" + pad2(k + 1) + "_" + safe(name) + ".png");
      var opts = new ExportOptionsSaveForWeb();
      opts.format = SaveDocumentType.PNG; opts.PNG8 = false; opts.transparency = true; opts.interlaced = false;
      dup.exportDocument(file, ExportType.SAVEFORWEB, opts);
      dup.close(SaveOptions.DONOTSAVECHANGES);
      app.activeDocument = src;
      ok++;
    } catch (e) {
      err++;
      try { if (app.activeDocument !== src) app.activeDocument.close(SaveOptions.DONOTSAVECHANGES); } catch (e2) {}
      try { app.activeDocument = src; } catch (e3) {}
    }
  }

  app.preferences.rulerUnits = prevUnits;
  alert("Capas a fotos: terminado.\n\nExportadas: " + ok + "\nErrores: " + err + "\n\nCarpeta:\n" + outFolder.fsName);
})();
