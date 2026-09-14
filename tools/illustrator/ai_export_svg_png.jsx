#target illustrator
/*
  ai_export_svg_png.jsx -- Exporta el doc activo a SVG + PNG en ~/Desktop/ai_illustrator
  para pasarlo a un LLM (SVG editable + PNG de referencia). Un click.
  Usa Arial en el doc para que abra igual en cualquier maquina.
*/
var IO = new Folder(Folder.desktop + "/ai_illustrator"); if (!IO.exists) IO.create();
var d = app.activeDocument;
var base = d.name.replace(/\.[^.]+$/, "");

// SVG (texto editable, imagenes embebidas, atributos de presentacion)
var svgOpt = new ExportOptionsSVG();
try { svgOpt.fontType = SVGFontType.SVGFONT; } catch (e) {}
svgOpt.embedRasterImages = true;
try { svgOpt.cssProperties = SVGCSSPropertyLocation.PRESENTATIONATTRIBUTES; } catch (e) {}
try { svgOpt.coordinatePrecision = 2; } catch (e) {}
d.exportFile(new File(IO.fsName + "/" + base + ".svg"), ExportType.SVG, svgOpt);

// PNG de referencia
var pngOpt = new ExportOptionsPNG24();
pngOpt.artBoardClipping = true;
d.exportFile(new File(IO.fsName + "/" + base + ".png"), ExportType.PNG24, pngOpt);

alert("Exportado SVG + PNG ->\n" + IO.fsName);
