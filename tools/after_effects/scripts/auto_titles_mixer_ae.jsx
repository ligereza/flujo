/*
  After Effects JSX - Auto titles + Mixer reactivo al audio
  =========================================================

  Crea UNA composicion por titulo. Cada comp lleva:
    - Fondo negro con ecualizador (efecto Audio Spectrum) apuntando a tu audio.
    - El titulo centrado que LATE con el volumen (Convert Audio to Keyframes +
      expresion sobre la escala).
    - Fundido de entrada/salida.

  Uso:
    File > Scripts > Run Script File... > auto_titles_mixer_ae.jsx
    1. Elige un .txt (un titulo por linea) o escribelos separados por ";".
    2. Elige el archivo de AUDIO.
    3. Responde tamano, fps, duracion, fuente e intensidad del pulso.

  Notas:
    - Usa match names / indices, asi que funciona con AE en espanol o ingles.
    - El ecualizador reacciona directo al audio (sin keyframes).
    - El "pulso" del titulo necesita Convert Audio to Keyframes; si tu AE no
      expone ese comando por idioma, el script avisa como hacerlo a mano.
    - El fondo es un solido negro: si quieres transparencia, apaga/borra la capa
      "Fondo Mixer" en cada comp.
*/

#target aftereffects

(function () {
  var proj = app.project;
  if (!proj) { app.newProject(); proj = app.project; }

  // ---------- Titulos ----------
  var titles = [];
  var tf = File.openDialog("Elige un .txt (un titulo por linea). Cancelar = escribir a mano.", "Texto:*.txt;Todos:*.*");
  if (tf) {
    tf.open("r"); var c = tf.read(); tf.close();
    var ls = c.split(/[\r\n]+/);
    for (var i = 0; i < ls.length; i++) { var ln = ls[i].replace(/^\s+|\s+$/g, ""); if (ln.length > 0) titles.push(ln); }
  } else {
    var raw = prompt("Titulos separados por ;  (punto y coma)", "Titulo 1; Titulo 2; Titulo 3");
    if (raw === null) return;
    var ps = String(raw).split(/;/);
    for (var j = 0; j < ps.length; j++) { var p = ps[j].replace(/^\s+|\s+$/g, ""); if (p.length > 0) titles.push(p); }
  }
  if (titles.length === 0) { alert("No hay titulos."); return; }

  // ---------- Audio ----------
  var audioFile = File.openDialog("Elige el archivo de AUDIO (wav/mp3/aac/m4a/aif)",
    "Audio:*.wav;*.mp3;*.aac;*.m4a;*.aif;*.aiff;Todos:*.*");
  if (!audioFile) { alert("Este script necesita un archivo de audio para el mixer."); return; }
  var audioItem;
  try { audioItem = app.project.importFile(new ImportOptions(audioFile)); }
  catch (e) { alert("No pude importar el audio: " + e); return; }

  // ---------- Parametros ----------
  function askInt(m, d) { var s = prompt(m, String(d)); if (s === null) return null; var v = parseInt(s, 10); return isNaN(v) ? d : v; }
  function askNum(m, d) { var s = prompt(m, String(d)); if (s === null) return null; var v = parseFloat(s); return isNaN(v) ? d : v; }
  var W = askInt("Ancho px", 1920); if (W === null) return;
  var H = askInt("Alto px", 1080); if (H === null) return;
  var FPS = askNum("FPS", 30); if (FPS === null) return;
  var DUR = askNum("Duracion por comp (segundos)", 5); if (DUR === null) return;
  var FS = askNum("Tamano de fuente px", 120); if (FS === null) return;
  var PULSE = askNum("Intensidad del pulso (0 = nada, 0.6 recomendado)", 0.6); if (PULSE === null) return;

  function findId(names) { for (var i = 0; i < names.length; i++) { var id = app.findMenuCommandId(names[i]); if (id && id !== 0) return id; } return 0; }
  var convertId = findId([
    "Convert Audio to Keyframes",
    "Convertir audio en fotogramas clave",
    "Convertir audio a fotogramas clave",
    "Convertir el audio en fotogramas clave"
  ]);

  function pad2(n) { n = String(n); while (n.length < 2) n = "0" + n; return n; }

  app.beginUndoGroup("Auto titles + mixer");
  var folder = proj.items.addFolder("Titulos + Mixer");
  var made = 0, converted = 0;

  for (var t = 0; t < titles.length; t++) {
    var name = "TituloMix_" + pad2(t + 1);
    var comp = proj.items.addComp(name, W, H, 1.0, DUR, FPS);
    comp.parentFolder = folder;

    // 1) Audio (queda al fondo del stack)
    var audioLayer = comp.layers.add(audioItem);
    try { audioLayer.startTime = 0; } catch (e) {}

    // 2) Convert Audio to Keyframes -> renombrar a AUDIO_AMP
    if (convertId > 0) {
      try {
        comp.openInViewer();
        for (var s = 1; s <= comp.numLayers; s++) comp.layer(s).selected = false;
        audioLayer.selected = true;
        var before = comp.numLayers;
        app.executeCommand(convertId);
        if (comp.numLayers > before) { comp.layer(1).name = "AUDIO_AMP"; converted++; }
      } catch (e) {}
    }

    // 3) Fondo + ecualizador (Audio Spectrum) sobre solido negro a pantalla completa
    var eq = comp.layers.addSolid([0, 0, 0], "Fondo Mixer", W, H, 1.0, comp.duration);
    var fx = null;
    try {
      fx = eq.property("ADBE Effect Parade").addProperty("ADBE AudioSpectrum");
      try { fx.property("ADBE AudioSpectrum-0002").setValue([W * 0.1, H * 0.82]); } catch (e) {} // Start Point
      try { fx.property("ADBE AudioSpectrum-0003").setValue([W * 0.9, H * 0.82]); } catch (e) {} // End Point
    } catch (e) {}

    // 4) Titulo
    var layer = comp.layers.addText(titles[t]);
    var srcProp = layer.property("ADBE Text Properties").property("ADBE Text Document");
    var td = srcProp.value;
    td.resetCharStyle();
    td.fontSize = FS;
    td.applyFill = true;
    td.fillColor = [1, 1, 1];
    td.applyStroke = false;
    try { td.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (e) {}
    srcProp.setValue(td);

    var tg = layer.property("ADBE Transform Group");
    try {
      var rect = layer.sourceRectAtTime(0, false);
      tg.property("ADBE Anchor Point").setValue([rect.left + rect.width / 2, rect.top + rect.height / 2]);
    } catch (e) {}
    tg.property("ADBE Position").setValue([W / 2, H / 2]);

    if (PULSE > 0) {
      var expr = 'try{ var a=thisComp.layer("AUDIO_AMP").effect(1)(1); var s=100 + a*' + PULSE + '; [s,s]; }catch(err){ value }';
      try { tg.property("ADBE Scale").expression = expr; } catch (e) {}
    }

    try {
      var op = tg.property("ADBE Opacity");
      var f = Math.min(0.5, DUR / 4);
      op.setValueAtTime(0, 0);
      op.setValueAtTime(f, 100);
      op.setValueAtTime(DUR - f, 100);
      op.setValueAtTime(DUR, 0);
    } catch (e) {}

    // 5) Apuntar el ecualizador a la capa de audio (indice ya estable: audio al fondo)
    if (fx) {
      try { fx.property("ADBE AudioSpectrum-0001").setValue(audioLayer.index); }
      catch (e) { try { fx.property(1).setValue(audioLayer.index); } catch (e2) {} }
    }

    made++;
  }

  app.endUndoGroup();

  var msg = "Auto titles + mixer: terminado.\n\n" +
    "Comps creadas: " + made + "\n" +
    "Audio convertido a keyframes en: " + converted + "/" + made;
  if (convertId === 0) {
    msg += "\n\nAviso: no encontre el comando 'Convert Audio to Keyframes' (posible idioma distinto).\n" +
      "El ecualizador SI reacciona; el pulso de los titulos quedo estatico.\n" +
      "Arreglo manual: abre una comp, selecciona la capa de audio, ejecuta\n" +
      "Animacion > Convertir audio en fotogramas clave y renombra la capa creada a AUDIO_AMP.";
  }
  alert(msg);
})();
