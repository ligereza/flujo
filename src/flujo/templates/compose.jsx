// compose.jsx — Flujo v0.15
#target photoshop

function readPaletteJSON(file) {
    if (!file.exists) return null;
    file.open("r");
    var content = file.read();
    file.close();
    try {
        var data = eval("(" + content + ")");
        if (data && data.colors && data.colors.length > 0) {
            var palette = [];
            for (var i = 0; i < Math.min(data.colors.length, 5); i++) {
                palette.push(data.colors[i].rgb);
            }
            return palette;
        }
    } catch(e) {}
    return null;
}

function main() {
    var baseFolder = Folder.current;
    var inputFile = new File(baseFolder + "/input/input_ig.jpg");
    var paletteFile = new File(baseFolder + "/analysis/palette.json");

    if (!inputFile.exists) {
        alert("No se encontró input/input_ig.jpg");
        return;
    }

    var doc = app.documents.add(1080, 1920, 72, baseFolder.name, NewDocumentMode.RGB);

    var idplace = charIDToTypeID("Plc ");
    var desc = new ActionDescriptor();
    desc.putPath(charIDToTypeID("null"), inputFile);
    executeAction(idplace, desc, DialogModes.NO);

    var layer = doc.activeLayer;
    layer.name = "Imagen IG (Smart Object)";

    var scale = (1920 / layer.bounds[3].value) * 100;
    layer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
    executeAction(stringIDToTypeID("newPlacedLayer"), undefined, DialogModes.NO);

    var palette = [[255,0,127],[0,255,200],[25,25,25],[255,255,255],[140,90,220]];
    var names = ["Principal","Acento","Fondo","Texto","Secundario"];

    var realPalette = readPaletteJSON(paletteFile);
    if (realPalette) {
        palette = realPalette;
    } else {
        // Fallback a aistetic
        var aisteticFile = new File(baseFolder + "/../../../projects/aistetic/aistetic.json");
        if (aisteticFile.exists) {
            var aisteticData = readPaletteJSON(aisteticFile);
            if (aisteticData) palette = aisteticData;
        }
    }

    for (var i = 0; i < palette.length; i++) {
        var colorLayer = doc.artLayers.add();
        colorLayer.name = "Color " + (names[i] || "Color " + (i+1));
        var solid = new SolidColor();
        solid.rgb.red = palette[i][0];
        solid.rgb.green = palette[i][1];
        solid.rgb.blue = palette[i][2];
        var fd = new ActionDescriptor();
        var rd = new ActionDescriptor();
        rd.putDouble(charIDToTypeID("Rd  "), palette[i][0]);
        rd.putDouble(charIDToTypeID("Grn "), palette[i][1]);
        rd.putDouble(charIDToTypeID("Bl  "), palette[i][2]);
        var cd = new ActionDescriptor();
        cd.putObject(charIDToTypeID("Clr "), charIDToTypeID("RGBC"), rd);
        fd.putObject(charIDToTypeID("Clr "), charIDToTypeID("SolidColor"), cd);
        executeAction(charIDToTypeID("Fl  "), fd, DialogModes.NO);
    }

    var txt = doc.artLayers.add();
    txt.kind = LayerKind.TEXT;
    txt.name = "Caption";
    txt.textItem.contents = "Pega el caption aquí...";
    txt.textItem.size = 28;
    txt.textItem.font = "Arial-Bold";
    txt.textItem.color = new SolidColor();
    txt.textItem.color.rgb.red = 255;
    txt.textItem.color.rgb.green = 255;
    txt.textItem.color.rgb.blue = 255;
    txt.textItem.position = [80, 1700];

    alert("Documento listo para Photoshop\\n(Paleta cargada desde analysis/palette.json)");
}
main();
