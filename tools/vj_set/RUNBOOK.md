# RUNBOOK -- pieza MANIFIESTO #1: "el repo se performa a si mismo"

La cadena completa, hoy, es real de punta a punta: `git log` -> `osc_score.json`
-> UDP OSC -> Resolume Arena. Antes de este runbook, `git_performance.py`
generaba la partitura pero nada la enviaba; `osc_sender.py` es la pieza que
faltaba.

## 1. Generar la partitura desde la historia real del repo

```bash
py tools/vj_set/git_performance.py --out tools/vj_set/out --duration 360
```

- `--duration 360` = comprime TODO el `git log` a 6 minutos (default).
- `--limit N` = solo los ultimos N commits (util para probar rapido, ej. `--limit 30`).
- `--all` = incluye todas las ramas, no solo la actual.
- `--fps 30` = FPS para los timecodes SMPTE (default 30).

Salida en `tools/vj_set/out/`:
- `cue_sheet.json` -- cues normalizadas (smpte, layer, clip, tipo, drop).
- `osc_cues.csv` -- timecode + mensaje OSC, para auditoria manual.
- `osc_score.json` -- **lo que consume `osc_sender.py`**: `{"port": 7000,
  "fps": 30, "duration_s": ..., "messages": [{"t": seg, "address": "/composition/
  layers/N/clips/M/connect", "args": [1], "type": "feat"}, ...]}`.
- `timeline.html` -- vista de la partitura (capas como pistas, drops como barras).

## 2. Dry-run: previsualizar sin tocar red

```bash
py tools/vj_set/osc_sender.py tools/vj_set/out/osc_score.json --dry-run
```

Imprime una linea por cue: `t=<segundos> <address> <args>`. No abre ningun
socket (verificado por test: `socket.socket` monkeypateado para reventar si
se llamara). Usalo SIEMPRE antes de disparar contra Resolume real -- es la
unica forma barata de confirmar que la partitura tiene sentido antes de
gastar el show.

Ensayo a velocidad: `--speed 8` corre 8x mas rapido (ver toda la partitura de
6 minutos en 45 segundos); `--desde 120` salta directo al segundo 120.

```bash
py tools/vj_set/osc_sender.py tools/vj_set/out/osc_score.json --dry-run --speed 20
```

## 3. Preparar Resolume Arena (OSC input)

1. Resolume -> Preferences -> OSC.
2. Activar "OSC Input" en el puerto **7000** (el puerto real que usa
   `flujo.resolume.automator.ShowCue`; `osc_score.json` lo trae en el campo
   `"port"` y `osc_sender.py` lo respeta salvo que pases `--port` explicito).
3. No hace falta configurar Custom OSC Input Map: las direcciones que manda
   este set son las RUTAS NATIVAS de composicion de Resolume
   (`/composition/layers/{layer}/clips/{clip}/connect`), que Resolume ya
   entiende de fabrica para disparar un clip.
4. Mapeo de la partitura (de `ShowCue.osc_address()` en
   `src/flujo/resolume/automator.py`):
   - **layer** = tipo de Conventional Commit (`merge`->1, `feat`->2, `fix`->3,
     `refactor`->4, `perf`->5, `chore`->6, `docs`->7, `test`->8, `style`->9,
     `build`/`ci`->10, `other`->11). Ver `TYPE_LAYER` en `git_performance.py`.
   - **clip** = columna dentro de esa capa (cicla 1-8: el golpe N de esa capa
     cae en la columna `((N-1) % 8) + 1`).
   - Cada mensaje manda `connect` con arg `1` (dispara el clip).
5. LIMITACION HONESTA: el mapeo ASUME que existen clips cargados en esos
   slots de layer/columna (hasta 11 capas x 8 columnas). Si tu composicion de
   Resolume tiene menos capas o menos clips por capa, las cues que caigan
   fuera de rango simplemente no disparan nada visible (Resolume ignora un
   `/connect` a un clip vacio). Arma la composicion ANTES del show con al
   menos 11 capas x 8 clips (88 slots) si queres cubrir toda la partitura.

## 4. Disparar para real

```bash
py tools/vj_set/osc_sender.py tools/vj_set/out/osc_score.json --host 127.0.0.1 --port 7000
```

- `--host` = IP de la maquina donde corre Resolume (127.0.0.1 si es la misma
  maquina; la IP de la LAN si es otra).
- `Ctrl-C` corta limpio: imprime cuantas cues se mandaron y cuantas quedaron
  sin disparar, y sale con codigo 130 (para que un script que lo llame sepa
  que fue interrumpido, no que termino solo).
- `--desde SEG` para arrancar el set a mitad de camino (ej. reanudar despues
  de un corte).

## Resumen de flags

| flag | default | que hace |
|---|---|---|
| `--host` | `127.0.0.1` | IP destino |
| `--port` | el del score (normalmente 7000) | puerto OSC destino |
| `--dry-run` | off | solo imprime, nunca abre socket |
| `--speed` | `1.0` | multiplicador de velocidad (ensayo) |
| `--desde` | `0.0` | saltar cues con t < SEG |

## Tip de ensayo

Corre el set completo en dry-run a `--speed 30` antes de cualquier show real
para leer la partitura entera en segundos y confirmar que los drops (merges)
caen donde esperas -- son las lineas verticales claras en `timeline.html`.
