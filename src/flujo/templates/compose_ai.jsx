// compose_ai.jsx — Flujo v0.15
#target illustrator

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

    var doc = app.documents.add(DocumentColorSpace.RGB, 1080, 1920);
    doc.artboards[0].name = baseFolder.name;

    var placed = doc.placedItems.add();
    placed.file = inputFile;
    placed.name = "Imagen IG (Linked)";

    var scale = (1920 / placed.height) * 100;
    placed.resize(scale, scale);
    placed.position = [(1080 - placed.width) / 2, 1920 - placed.height];

    var palette = [[255,0,127],[0,255,200],[25,25,25],[255,255,255],[140,90,220]];
    var names = ["Principal","Acento","Fondo","Texto","Secundario"];

    var realPalette = readPaletteJSON(paletteFile);
    if (realPalette) {
        palette = realPalette;
    } else {
        // Fallback a aistetic (línea editorial central)
        var aisteticFile = new File(baseFolder + "/../../../projects/aistetic/aistetic.json");
        if (aisteticFile.exists) {
            var aisteticData = readPaletteJSON(aisteticFile);  // reuse, aunque no es perfecto
            if (aisteticData) palette = aisteticData;
        }
    }

    for (var i = 0; i < palette.length; i++) {
        var c = new RGBColor();
        c.red = palette[i][0]; c.green = palette[i][1]; c.blue = palette[i][2];
        var sw = doc.swatches.add();
        sw.name = names[i] || ("Color " + (i+1));
        sw.color = c;
    }

    alert("Documento listo para Illustrator\\n(Swatches cargados desde analysis/palette.json)");
}
main();
