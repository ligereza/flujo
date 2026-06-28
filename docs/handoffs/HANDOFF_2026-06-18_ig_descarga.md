# 🤝 Handoff 2026-06-18 — flujo v0.30.2 (ampliado) — IG: usuario + descarga + paleta

## Contexto

El dueño NO había descargado el 0.30.2 anterior (solo traía el fix de regex IG).
Pidió **ampliar la misma versión 0.30.2** con la descarga real y "más pasos".
Este zip reemplaza al 0.30.2 anterior e incluye todo.

## Qué incluye

1. **Fix IG con usuario** (lo del 0.30.2 previo): detecta
   `instagram.com/<usuario>/p/CODE/` además de `instagram.com/p/CODE/`.
2. **Descarga real en la pestaña INSTAGRAM** del editor (botón "2. Descargar
   post"): usa `flujo.ig.download` (instaloader), guarda la imagen en
   `projects/flyer_eventos/<slug>/input/`, muestra la imagen + cuenta + fecha.
3. **Extracción de paleta** de la imagen descargada (`analyze.colors`), mostrada
   como hex.
4. **Botón "3. Aplicar paleta a la pieza"**: vuelca los colores al `palette` del
   formato cargado en EDITOR y refresca el preview. → conecta IG con el editor.

## Archivos

| Archivo | Cambio |
|---|---|
| `src/flujo/intake/email_parser.py` | regex IG con `<usuario>` opcional. |
| `src/flujo/web/editor.py` | `descargar_instagram()`, `aplicar_paleta()`; pestaña INSTAGRAM con 3 botones + imagen; wiring de "aplicar paleta" a state/preview. |
| `tests/test_ig_usuario.py` | 7 tests del regex (incluye URL exacta del dueño). |
| `tests/test_ig_download_palette.py` | **NUEVO.** 7 tests (descarga mockeada + paleta + errores). |
| `docs/EDITOR_INSTAGRAM.md` | **NUEVO.** Guía de la pestaña. |
| `version.py`, `pyproject.toml` | v0.30.2 (changelog ampliado). |

## Decisiones de diseño

- **Descarga = solo instaloader** (regla del repo). Errores (privado/429/no
  encontrado) se informan con mensaje claro, no rompen la UI.
- **Funciones puras y mockeables:** `descargar_instagram` se testea parcheando
  `flujo.ig.download.download_post` (sin red). La extracción de paleta es real.
- **Reusa** `analyze.colors.extract_palette` y `ig.download` — nada nuevo de
  infraestructura.
- **Sin elemento `image`** todavía (decisión previa: SVG puro). La paleta sí se
  aplica; la foto se descarga para que la uses en Illustrator/Photoshop o para
  inferir colores.

## Verificación hecha

```
✅ regex IG: 'instagram.com/sundeckfiestas/p/CODE/' → 1 link; perfiles puros → []
✅ descarga (mock) + paleta real desde imagen generada → OK
✅ aplicar_paleta vuelca colores al config y no muta el original
✅ manejo de error (privado/login) → mensaje claro
✅ build_app + launch real → HTTP 200
✅ pytest tests/ → 168 passed, 1 skipped
```

## Cómo aplicar

```bash
flujo airdrop apply "v0.30.2 - IG usuario + descarga + paleta"
py -m pip install -e .
flujo version            # 0.30.2
flujo serve              # pestaña INSTAGRAM: pegar link → Analizar → Descargar → Aplicar paleta
py -m pytest tests/ -q   # 168 passed, 1 skipped
```

### Probar el flujo completo
1. EDITOR: elegí un formato (ej. `evt_cartelera_individual_1080x1920`).
2. INSTAGRAM: pegá `https://www.instagram.com/sundeckfiestas/p/DZdW4_vmY4l/`.
3. "2. Descargar post" → ves la imagen + la paleta.
4. "3. Aplicar paleta a la pieza" → volvé a EDITOR, el preview usa esos colores.

## Próximos pasos

- Inferir productora/fecha/venue del caption descargado (para carteleras).
- Elemento `image` en el generador (cuando el dueño quiera; hoy SVG puro).
- Edición visual de posición de elementos.
- Conectar "acuse de recibo" con el folio del intake.
