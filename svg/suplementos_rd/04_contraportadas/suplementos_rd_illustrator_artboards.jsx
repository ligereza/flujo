// flujo_illustrator_artboards.jsx
#target illustrator

function addText(frame, text, size, fontName, fill) {
    frame.contents = text;
    frame.textRange.characterAttributes.size = size;
    frame.textRange.characterAttributes.textFont = textFonts.getByName(fontName);
    frame.textRange.characterAttributes.fillColor = new RGBColor();
    frame.textRange.characterAttributes.fillColor.red = fill[0];
    frame.textRange.characterAttributes.fillColor.green = fill[1];
    frame.textRange.characterAttributes.fillColor.blue = fill[2];
}

function main() {
    var payload = {
  "document": {
    "name": "Suplementos RD - Contraportadas",
    "width": 2362,
    "height": 1654,
    "colorMode": "RGB"
  },
  "artboards": [
    {
      "name": "Pre Fiesta",
      "title": "PRE FIESTA",
      "body": [
        "Apoya el metabolismo energético y la respuesta al estrés antes de situaciones de alta demanda.",
        "Vitaminas, taurina, L-teanina y rhodiola."
      ],
      "cta": "Beneficio: energía + regulación",
      "contact": "WhatsApp RD / QR"
    },
    {
      "name": "Post Fiesta",
      "title": "POST FIESTA",
      "body": [
        "Complementa la recuperación nutricional tras contextos de alta exigencia fisiológica.",
        "Electrolitos, vitaminas, NAC, cardo mariano y CoQ10."
      ],
      "cta": "Beneficio: recuperación + hidratación",
      "contact": "WhatsApp RD / QR"
    },
    {
      "name": "Impulso",
      "title": "IMPULSO",
      "body": [
        "Contribuye al estado de alerta y la concentración en actividades que requieren foco sostenido.",
        "Cafeína, L-teanina y vitamina B12."
      ],
      "cta": "Beneficio: foco + alerta",
      "contact": "WhatsApp RD / QR"
    },
    {
      "name": "Hongos Adaptógenos",
      "title": "HONGOS ADAPTÓGENOS",
      "body": [
        "Acompaña procesos de regulación y bienestar en rutinas exigentes.",
        "Cordyceps, melena de león, reishi, L-teanina y vitamina B12."
      ],
      "cta": "Beneficio: regulación + bienestar",
      "contact": "WhatsApp RD / QR"
    },
    {
      "name": "Magnesio",
      "title": "MAGNESIO",
      "body": [
        "Complementa la ingesta diaria de magnesio, mineral esencial para el sistema nervioso, la función muscular y el metabolismo energético.",
        "Disponible en citrato y bisglicinato."
      ],
      "cta": "Beneficio: relajación + función muscular",
      "contact": "WhatsApp RD / QR"
    },
    {
      "name": "Creatina",
      "title": "CREATINA",
      "body": [
        "Molécula ampliamente estudiada en suplementación nutricional, vinculada a la producción de energía celular.",
        "Disponible en polvo y en gomitas."
      ],
      "cta": "Beneficio: energía + rendimiento",
      "contact": "WhatsApp RD / QR"
    },
    {
      "name": "Proteína",
      "title": "PROTEÍNA",
      "body": [
        "Suplemento en polvo de proteína de suero de leche para apoyar la recuperación muscular y el aporte proteico diario.",
        "Disponible en whey y iso protein."
      ],
      "cta": "Beneficio: recuperación + proteína",
      "contact": "WhatsApp RD / QR"
    }
  ],
  "base_dir": "C:\\IA\\flujo"
};
    var doc = app.documents.add(DocumentColorSpace.RGB, payload.document.width, payload.document.height);
    doc.artboards[0].name = payload.document.name;
    doc.artboards[0].artboardRect = [0, 0, payload.document.width, payload.document.height];

    var baseWidth = payload.document.width;
    var baseHeight = payload.document.height;
    var columns = 2;
    var rows = Math.ceil(payload.artboards.length / columns);
    var spacingX = 80;
    var spacingY = 80;
    var boardWidth = (baseWidth - spacingX * (columns + 1)) / columns;
    var boardHeight = (baseHeight - spacingY * (rows + 1)) / rows;

    for (var i = 0; i < payload.artboards.length; i++) {
        var item = payload.artboards[i];
        if (i > 0) {
            doc.artboards.add();
        }
        var board = doc.artboards[i];
        var col = i % columns;
        var row = Math.floor(i / columns);
        var x0 = spacingX + col * (boardWidth + spacingX);
        var y0 = baseHeight - spacingY - (row + 1) * boardHeight - row * spacingY;
        board.artboardRect = [x0, y0, x0 + boardWidth, y0 + boardHeight];
        board.name = item.name;

        var rect = doc.pathItems.rectangle(y0 - boardHeight, x0, boardWidth, boardHeight);
        rect.filled = true;
        rect.stroked = true;
        rect.fillColor = new RGBColor();
        rect.fillColor.red = 246; rect.fillColor.green = 239; rect.fillColor.blue = 227;
        rect.strokeColor = new RGBColor();
        rect.strokeColor.red = 207; rect.strokeColor.green = 194; rect.strokeColor.blue = 178;

        var titleFrame = doc.textFrames.add();
        titleFrame.position = [x0 + 40, y0 - 80];
        titleFrame.contents = item.title;
        titleFrame.textRange.characterAttributes.size = 32;
        titleFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');

        var bodyFrame = doc.textFrames.add();
        bodyFrame.position = [x0 + 40, y0 - 140];
        bodyFrame.contents = item.body.join('
');
        bodyFrame.textRange.characterAttributes.size = 18;
        bodyFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');

        if (item.cta) {
            var ctaFrame = doc.textFrames.add();
            ctaFrame.position = [x0 + 40, y0 - 220];
            ctaFrame.contents = item.cta;
            ctaFrame.textRange.characterAttributes.size = 16;
            ctaFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');
        }

        if (item.contact) {
            var contactFrame = doc.textFrames.add();
            contactFrame.position = [x0 + 40, y0 - 280];
            contactFrame.contents = item.contact;
            contactFrame.textRange.characterAttributes.size = 16;
            contactFrame.textRange.characterAttributes.textFont = textFonts.getByName('Arial');
        }
    }

    alert('Mesas de trabajo creadas desde flujo');
}

main();
