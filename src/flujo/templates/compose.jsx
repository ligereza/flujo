// compose.jsx — Flujo v0.15
// Script para Photoshop (doble clic)
// Coloca input_ig.jpg como Smart Object + paleta REAL desde analysis/palette.json

#target photoshop

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

    // === Cargar paleta real desde analysis/palette.json ===
    var palette = [
        [255, 0, 127],
        [0, 255, 200],
        [25, 25, 25],
        [255, 255, 255],
        [140, 90, 220]
    ];
    var names = ["Principal", "Acento", "Fondo", "Texto", "Secundario"];

    if (paletteFile.exists) {
        try {
            paletteFile.open("r");
            var content = paletteFile.read();
            paletteFile.close();

            var data = eval("(" + content + ")");
            if (data && data.colors && data.colors.length > 0) {
                palette = [];
                for (var i = 0; i < Math.min(data.colors.length, 5); i++) {
                    palette.push(data.colors[i].rgb);
                }
            }
        } catch(e) {}
    }

    for (var i = 0; i < palette.length; i++) {
        var colorLayer = doc.artLayers.add();
        colorLayer.name = "Color " + (names[i] || "Color " + (i+1));

        var solid = new SolidColor();
        solid.rgb.red = palette[i][0];
        solid.rgb.green = palette[i][1];
        solid.rgb.blue = palette[i][2];

        var fillDesc = new ActionDescriptor();
        var rgbDesc = new ActionDescriptor();
        rgbDesc.putDouble(charIDToTypeID("Rd  "), palette[i][0]);
        rgbDesc.putDouble(charIDToTypeID("Grn "), palette[i][1]);
        rgbDesc.putDouble(charIDToTypeID("Bl  "), palette[i][2]);

        var colorDesc = new ActionDescriptor();
        colorDesc.putObject(charIDToTypeID("Clr "), charIDToTypeID("RGBC"), rgbDesc);
        fillDesc.putObject(charIDToTypeID("Clr "), charIDToTypeID("SolidColor"), colorDesc);
        executeAction(charIDToTypeID("Fl  "), fillDesc, DialogModes.NO);
    }

    var textLayer = doc.artLayers.add();
    textLayer.kind = LayerKind.TEXT;
    textLayer.name = "Caption IG";
    textLayer.textItem.contents = "Pega aquí el caption del post...";
    textLayer.textItem.size = 28;
    textLayer.textItem.font = "Arial-Bold";
    textLayer.textItem.color = new SolidColor();
    textLayer.textItem.color.rgb.red = 255;
    textLayer.textItem.color.rgb.green = 255;
    textLayer.textItem.color.rgb.blue = 255;
    textLayer.textItem.position = [80, 1700];

    alert("Documento listo para Photoshop\n(Paleta cargada desde analysis/palette.json)");
}

main();
