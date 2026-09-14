# TAPIZ - ecosistema Tapiz / Psicosis / Fungi

Pieza artistica: telemetria de ingenieria renderizada como ecosistema vivo.
Tres entidades: **Tapiz** (el espacio geometrico donde todo se proyecta),
**Psicosis** (entropia, el sistema bajo presion pierde coherencia) y
**Fungi** (descomposicion: los assets decaen y sus cuerpos quedan enterrados
en el documento, codificados, hasta que alguien los exhuma con un click).

## Piezas

| Archivo | Rol |
|---|---|
| `tools/compete_engine.py` | Pipeline: analiza assets (presion de tokens, riesgo guardrail, conflictos de estado) y compila `tools/dist/system_status.json` |
| `tools/system_map.py` | Contrato (`API_CONTRACT_SCHEMA`) + validador estructural del JSON + directivas de render |
| `tools/tapiz_renderer.html` | Frontend: consume el JSON y lo vuelve visual (mesh, mascara, tears, esporas, sigil) |
| `tools/tapiz_telemetry.py` | (modo live) construye el ecosistema desde el estado REAL del repo |
| `tools/tapiz_three.html` | Frontend 3D (Three.js r160 via CDN): mismo contrato, grilla instanciada, fog por mascara, esporas raycasteables |
| `tools/TAPIZ_RESOLUME_SPEC.md` | Spec de mapping OSC para Resolume Arena 7 (campo -> direccion -> rango -> curva), para operador VJ |
| `tests/test_compete_engine.py` | Tests del engine y sus modos |

## Uso

```bash
py tools/compete_engine.py --demo      # ecosistema mock, estado calmo
py tools/compete_engine.py --stress    # ecosistema hostil: todos los umbrales feos
py tools/compete_engine.py --live      # autorretrato: telemetria real del repo
py tools/compete_engine.py --demo --out DIR   # salida a otro directorio

py tools/system_map.py validate tools/dist/system_status.json   # PASS/FAIL por seccion
py tools/system_map.py show                                     # directivas de render

py -m pytest tests/test_compete_engine.py -q

# ver el arte:
py -m http.server 8137        # desde la raiz del repo
# http://localhost:8137/tools/tapiz_renderer.html
# (file:// tambien sirve: aparece un file-picker, apuntarlo al JSON)
```

`tools/dist/` es salida generada: esta en gitignore, no se commitea.

## Mapa concepto -> visual

| Diagnostico (ingenieria) | Metafora | Render |
|---|---|---|
| Presion de tokens (densidad ASCII penalizada) | Grilla bioluminiscente que se apaga bajo carga | CSS vars -> opacidad/densidad del mesh canvas |
| Riesgo guardrail (lexicon, mitigacion artistica 70%) | Velo cromatico que censura el contenido | `filter` CSS sobre el wrapper (blur/saturate/hue-rotate) |
| Race conditions / violaciones de estado | Desgarros temporales en el espacio | keyframes `temporal_tear` inyectados, mas violentos con mas colisiones |
| Assets en descomposicion | Esporas: cuerpos enterrados en el documento | Circulos clickeables; decode Base64+Shift42 en overlay |
| Huella de la compilacion | Sigil (sello ritual) | SHA-256 en el footer; el poll re-renderiza solo si cambia |

## Contrato

El JSON tiene 5 secciones (`meta`, `luminous_mesh_densities`,
`chromatic_frequency_masks`, `chronological_collision_buffers`,
`encoded_asset_payloads`). Esquema completo y tipos en
`tools/system_map.py::API_CONTRACT_SCHEMA`. Cualquier renderer alternativo
(Resolume/VJ, Three.js) debe validar contra eso, no adivinar.

Protocolo de payloads: contenido UTF-8 -> base64 -> shift +42 por byte ->
base64 -> chunks de 256 chars. El JS de referencia para decodificar esta en
`system_map.py::CHUNK_DECODING_PROTOCOL_JS` (corregido 2026-07-10: la version
original tenia un btoa/atob espurio que devolvia base64 en vez de contenido).

## Privacidad (modo live)

El JSON live puede terminar publicado (artifact web). Regla dura: el contenido
de assets solo lleva nombres de archivo, tamanos, conteos, fechas y hashes
cortos de git. Nunca: `.env*`, keys/secrets/tokens, `*.local.md`, contenido de
`datadrops/` (nombres y tamanos OK). La lista de exclusion vive en
`tools/tapiz_telemetry.py` y tiene test propio.

## Puentes construidos (2026-07-11)

- Renderer Resolume/VJ: spec OSC completa en `tools/TAPIZ_RESOLUME_SPEC.md`
  (implementacion en Resolume = trabajo de operador, la spec basta).
- Escena Three.js: `tools/tapiz_three.html` (mismo contrato, file-picker +
  fetch de `tools/dist/system_status.json`; falta solo embeberla en el hub web).
- Autorretrato continuo: retirado 2026-08-29 (`tapiz_live_loop.py` no tenia
  consumidor medido; ver `/home/mak/_archive/orden-limpieza-20260828/por-razon/
  herramienta-abandonada/POR-QUE.txt`). `py tools/compete_engine.py --live`
  sigue disponible para correr un tick a mano.

## Puentes construidos (2026-07-11, segunda tanda)

- Embed de tapiz_three.html en el hub web (workspace Cultura, seccion
  "Ecosistema 3D": iframe lazy + comandos + fallback http.server).
- Piezas curadas del telar y cauce en `projects/tapiz/piezas_curadas/`
  (5 SVG generados con el instrumento real; entrada propia en
  `tools/portfolio/proyectos.json`).
- Primera pieza tilde: `py projects/tilde/sobrevivencia.py corpus.jsonl`
  (render target sobrevivencia-01 segun `projects/tilde/SPEC.md`).
