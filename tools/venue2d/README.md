# Venue 2D — referencia teatral

`referencia_plano_teatro.py` es el primer prototipo del circuito SCD: una GUI
paramétrica que dibuja en 2D la planta radial de una sala y sus butacas a partir
de constantes geométricas. Es una referencia matemática y visual, no una
medición certificada ni el motor headless de planos operativos.

La cadena que consume esta referencia es:

```text
venue2d/referencia_plano_teatro.py
  → venue_geometria_scd.py
  → data/venues/*.json
  → venue3d/index.html
  → venue_secuencia.mjs
```

`tools/venue.py` valida y administra los registros. `projects/plano/` conserva
el motor separado de planos y riders de eventos (`plano_stands.py`). El visor
3D usa polilíneas con unidad y confianza explícitas; todavía no existe una
integración XIO ni Gaussian splat. Si se incorpora captura visual en el futuro,
deberá entrar como evidencia calibrada y no podrá inventar escala métrica.
