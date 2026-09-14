# Piezas curadas del tapiz

Serie curada de piezas SVG generadas con el instrumento real
(`projects/tapiz/vibecode_spaces.py`), nunca dibujadas a mano. Cada pieza
teje los espacios de un archivo vivo del repo: el codigo elige la trama,
el instrumento solo la revela. Paleta flujo oficial en todas.

Nota: esta carpeta se llama `piezas_curadas/` porque `projects/tapiz/piezas/`
esta gitignorada (salida efimera del instrumento); lo curado se versiona aqui.

## Piezas

| Pieza | Modo | Fuente tejida | Lectura |
|---|---|---|---|
| `field_compete_engine.svg` | field (gul) | `tools/compete_engine.py` | El motor de diagnostico del ecosistema como campo repetido de guls: la telemetria vuelta alfombra. |
| `border_validate_airdrop.svg` | border (boteh) | `scripts/validate_airdrop.py` | El validador que custodia la frontera del repo tejido como cenefa boteh: el borde que decide que entra. |
| `medallion_loom.svg` | medallion | `projects/tapiz/vibecode/loom.py` | El telar tejiendose a si mismo: su codigo ocupa el centro como medallon. |
| `mihrab_spaces.svg` | mihrab | `projects/tapiz/vibecode/spaces.py` | El render principal orientado hacia un nicho: el codigo que dibuja apunta a donde mira. |
| `cauce_cauce.svg` | cauce (animada, SMIL) | `projects/tapiz/vibecode/cauce.py` | El cauce leyendo su propia recurrencia: mismo token, mismo color, patron reconocido y no impuesto. |
| `field_telemetry.svg` | field (gul) | `tools/tapiz_telemetry.py` | La telemetria del tapiz tejida como campo: el sensor vuelto motivo repetido. |
| `border_dossier_tapiz.svg` | border (boteh) | `projects/cultura/dossiers/tapiz.md` | El dossier que enmarca al proyecto tejido como cenefa: la investigacion es el borde de la obra. |
| `mihrab_tilde_meter.svg` | mihrab | `desktop/tilde_meter.py` | El medidor de sobrevivencia de la tilde orientado hacia su nicho: el instrumento reza por las marcas. |
| `medallion_entrada.svg` | medallion | `projects/tapiz/vibecode_spaces.py` | La puerta de entrada del instrumento como medallon minimo: casi vacio, porque la entrada solo delega. |
| `cauce_sala3d.svg` | cauce (animada, SMIL) | `tools/sala3d/build.js` | La galeria tejiendose a si misma: el build de la sala 3D leido por el cauce. |
| `void_animado.svg` | espaciado + zigzag_vertical + raices (animadas, SMIL, compuesta en 3 paneles) | `SAMPLE_CODE` (muestra canonica de `projects/tapiz/vibecode/spaces.py`) | Las tres morfologias del vacio animado (direccion 2026-07-12): el hueco que respira, el hilo en zigzag que teje hacia abajo, la raiz rectangular que crece y ramifica. |

## Regeneracion exacta

Desde la raiz del repo:

```bash
py projects/tapiz/vibecode_spaces.py tools/compete_engine.py -m field --svg projects/tapiz/piezas_curadas/field_compete_engine.svg
py projects/tapiz/vibecode_spaces.py scripts/validate_airdrop.py -m border --svg projects/tapiz/piezas_curadas/border_validate_airdrop.svg
py projects/tapiz/vibecode_spaces.py projects/tapiz/vibecode/loom.py -m medallion --svg projects/tapiz/piezas_curadas/medallion_loom.svg
py projects/tapiz/vibecode_spaces.py projects/tapiz/vibecode/spaces.py -m mihrab --svg projects/tapiz/piezas_curadas/mihrab_spaces.svg
py projects/tapiz/vibecode_spaces.py projects/tapiz/vibecode/cauce.py -m cauce -a --svg projects/tapiz/piezas_curadas/cauce_cauce.svg
py projects/tapiz/vibecode_spaces.py tools/tapiz_telemetry.py -m field --svg projects/tapiz/piezas_curadas/field_telemetry.svg
py projects/tapiz/vibecode_spaces.py projects/cultura/dossiers/tapiz.md -m border --svg projects/tapiz/piezas_curadas/border_dossier_tapiz.svg
py projects/tapiz/vibecode_spaces.py desktop/tilde_meter.py -m mihrab --svg projects/tapiz/piezas_curadas/mihrab_tilde_meter.svg
py projects/tapiz/vibecode_spaces.py projects/tapiz/vibecode_spaces.py -m medallion --svg projects/tapiz/piezas_curadas/medallion_entrada.svg
py projects/tapiz/vibecode_spaces.py tools/sala3d/build.js -m cauce -a --svg projects/tapiz/piezas_curadas/cauce_sala3d.svg
```

`void_animado.svg` es la unica pieza compuesta de la serie: en vez de un
solo `--svg`, apila en 3 paneles el export animado de los tres modos
nuevos (`espaciado`, `zigzag_vertical`, `raices` -- ver
`projects/tapiz/vibecode/void_shapes.py`) sobre la misma fuente chica
(`SAMPLE_CODE`). Cada panel por separado se regenera con el CLI normal:

```bash
py projects/tapiz/vibecode_spaces.py projects/tapiz/vibecode/spaces.py -m espaciado -a --svg /tmp/espaciado.svg
py projects/tapiz/vibecode_spaces.py projects/tapiz/vibecode/spaces.py -m zigzag_vertical -a --svg /tmp/zigzag_vertical.svg
py projects/tapiz/vibecode_spaces.py projects/tapiz/vibecode/spaces.py -m raices -a --svg /tmp/raices.svg
```

(sin archivo de entrada, el CLI cae a su `SAMPLE_CODE` embebido). El
compuesto en si se arma apilando los tres `<svg>` internos en un solo
documento (SMIL puro, sin JS, GitHub-safe); no forma parte del instrumento
reusable porque es un stitch de una sola vez para esta pieza curada.

Regla de peso: cada SVG curado bajo ~300KB (una pieza de 918KB fue
rechazada por pesada). `src/flujo/cli.py` en modo medallion dio 800KB+:
descartado; fuentes chicas tejen mejor.

Las piezas son deterministas respecto de su fuente: si el archivo tejido
cambia, la pieza cambia. La serie fija el estado 2026-07-11.
