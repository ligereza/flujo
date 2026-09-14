# Operacion de la app (hub)

> Nota de origen (leer antes de seguir): este documento se escribio en un
> worktree basado en `origin/mejoras` (fetch del 2026-07-25). El paquete
> `flujo` esta instalado en modo editable apuntando al checkout principal del
> repo (`C:\IA\flujo`), no a este worktree -- verificado con:
> ```
> py -c "import flujo, os; print(os.path.abspath(flujo.__file__))"
> # -> C:\IA\flujo\src\flujo\__init__.py
> ```
> Esto significa que `py -m flujo ...` en esta maquina siempre corre el
> codigo que este *checkeado en `C:\IA\flujo`*, sin importar en que branch
> o worktree estes parado vos. El 2026-07-25 ese checkout estaba en una rama
> mas adelantada que `mejoras` (traia, entre otras cosas, el flag
> `--procesar-pendientes`, el sistema de perfiles en `profiles.ts`, el panel
> de Automatizaciones y el panel de Base de Datos RD -- ninguno de esos
> existe todavia en `origin/mejoras` tal como se fetcheo para este documento).
> Este manual describe el sistema real tal como corre hoy (verificable con
> los comandos de cada seccion); donde `mejoras` todavia no tiene una pieza,
> se lo marca explicitamente en vez de fingir que ya esta mergeada.

## 1. Que es y como se levanta

Comando real de entrada diaria:

```bash
py -m flujo app
```

Es un alias de `flujo serve --hub` (`src/flujo/cli.py`, comando `app`
registrado en `@app.command("app")`). Flags reales, verificados con
`py -m flujo app --help`:

```
--port, -p              INTEGER  [default: 8765]
--host                   TEXT     [default: 127.0.0.1]
--desktop
--procesar-pendientes             al arrancar, avanzar los jobs de flyer
                                   pendientes (modifica jobs: por eso no es
                                   el default)
--help
```

- Sin flags: arranca el servidor HTTP local, abre el navegador en
  `http://127.0.0.1:8765/flujo_hub.html`. Si el puerto 8765 esta ocupado,
  detecta uno libre automaticamente (`_find_free_port`, `src/flujo/web/hub.py`).
- `--desktop`: ventana nativa via `pywebview` (si esta instalado) en vez de
  pestana de navegador, con bridge Python<->JS directo (`_HubDesktopApi`).
- `--procesar-pendientes`: ver seccion 8, primera trampa -- NO es el default
  a proposito.
- Fallback sin backend: `context/flujo_hub.html` es un HTML que tambien se
  puede abrir directo con doble click (`file://`), sin servidor. Se degrada
  con gracia: los fetches a `/api/*` fallan y la UI cae a estado estatico,
  no rompe.

El frontend (`web/src/`, React + Vite) se compila con:

```bash
cd web && npm run build:context
```

Esto corre `vite build` y despues `node scripts/copy-context.mjs`, que copia
el resultado a `context/*.html`. **Los archivos `context/*.html` son
GENERADOS: no se editan a mano.** Cualquier cambio manual ahi se pierde en
el proximo build. Para cambiar la UI se edita `web/src/`, se corre el build,
y recien ahi se refleja en `context/`.

## 2. Anatomia: backend, frontend, perfiles

Tres piezas:

- **Backend** (`src/flujo/web/hub.py`): `HubRequestHandler`
  (`ThreadingHTTPServer` de la stdlib, sin dependencias extra) sirve el HTML
  estatico de `context/` y responde `/api/*` con datos reales (jobs, intake,
  cotizaciones, plano, etc). No hay framework web: el ruteo es una cadena de
  `if path == "/api/...":` dentro de `do_GET`/`do_POST`.
- **Frontend** (`web/src/`): app React/Vite. `App.tsx` decide que panel
  mostrar segun el `view` activo; `AppShell.tsx` es el layout (sidebar +
  selector de workspace); los paneles viven en `web/src/components/*.tsx`
  (uno por herramienta: `JobsPanel`, `IntakePanel`, `QuotePanel`, etc).
- **Perfiles** (`web/src/data/profiles.ts`): que ve cada perfil/workspace
  (RD, Studio, Cultura...). Cada perfil trae su propio `nav` (lista de
  paneles visibles) y colores. `AppShell.tsx` ya no tiene logica de perfil
  cableada: solo lee `profile.nav` / `profile.accent.*`.
  **Advertencia:** `profiles.ts` y `docs/HUB_PERFILES.md` (que lo documenta
  en detalle) NO existen todavia en `origin/mejoras` -- viven en una rama
  mas adelantada, pendiente de merge. Verificado 2026-07-25: en el worktree
  de `mejoras`, `web/src/data/` solo tiene `configTypes.ts` y `svgIndex.ts`,
  y el selector de workspace esta cableado a mano dentro de
  `web/src/components/AppShell.tsx` (arrays `RD_NAV`/`STUDIO_NAV`/
  `CULTURA_NAV`). La seccion 5 describe el sistema real (con `profiles.ts`),
  que es el que corre hoy via el checkout principal.

Diagrama en texto:

```
Navegador (http://127.0.0.1:8765/flujo_hub.html)
        |
        v
 HubRequestHandler (src/flujo/web/hub.py, ThreadingHTTPServer)
   |-- GET /flujo_hub.html, /svg_visualizer.html, /plano_demo.html
   |         -> sirve context/*.html (generado por `npm run build:context`)
   |-- GET/POST /api/*  -> jobs/, intake/, dashboard.py, rd/, automation.py...
   |-- (--desktop) _HubDesktopApi -> mismo backend, sin red (pywebview bridge)
        |
        v
 React app (web/src/App.tsx -> AppShell.tsx -> profiles.ts -> components/*.tsx)
```

## 3. Agregar un endpoint

Ejemplo tomado del patron real de `src/flujo/web/hub.py` (clase
`HubRequestHandler`, `class HubRequestHandler(BaseHTTPRequestHandler):` en
`src/flujo/web/hub.py:267`):

1. Elegir metodo. GET para consultas, POST si el cliente manda body JSON.
2. **GET**: agregar un bloque `if path == "/api/mi-endpoint": ...; return`
   dentro de `do_GET` (`src/flujo/web/hub.py:347`), siguiendo el patron de
   `/api/status` (`src/flujo/web/hub.py:380-382`):
   ```python
   if path == "/api/status":
       self._send_json(self._get_status())
       return
   ```
3. **POST**: mismo patron pero dentro de `do_POST`
   (`src/flujo/web/hub.py:472`), leyendo el body con
   `Content-Length`/`self.rfile.read(...)`, ejemplo real en
   `/api/parse-pedido` (`src/flujo/web/hub.py:498-508`):
   ```python
   if p == "/api/mi-endpoint":
       content_length = int(self.headers.get("Content-Length", 0))
       body = self.rfile.read(content_length).decode("utf-8")
       try:
           data = json.loads(body or "{}")
           result = self._mi_logica(data)
           self._send_json(result)
       except Exception as e:
           self._send_json({"error": str(e)}, status=400)
       return
   ```
4. El bloque nuevo va **antes** del `self.send_error(404)` final de cada
   metodo (`do_GET` termina en `src/flujo/web/hub.py:459/470`; `do_POST`
   termina en `src/flujo/web/hub.py:615` en el checkout verificado).
5. Poner la logica real en un metodo aparte (`_get_x` / `_handle_x`), no
   inline -- asi tambien queda disponible para el bridge de escritorio
   (`_HubDesktopApi`, `src/flujo/web/hub.py:1667` en el checkout verificado)
   sin duplicar codigo.
6. Responder siempre con `self._send_json(dict, status=...)`
   (`src/flujo/web/hub.py:637`). Envolver la logica en `try/except` que
   devuelva `{"error": str(e)}` con `status=200` (si el frontend debe seguir
   funcionando aunque falle) o `status=400/500` (si es un error de request).

Probarlo con el servidor corriendo (`py -m flujo app`):

```bash
curl http://127.0.0.1:8765/api/mi-endpoint
curl -X POST http://127.0.0.1:8765/api/mi-endpoint -d "{}" -H "Content-Type: application/json"
```

o abrir la URL GET directo en el navegador.

## 4. Agregar un panel

1. Crear el componente en `web/src/components/MiPanel.tsx` (mismo patron que
   `JobsPanel.tsx`, `IntakePanel.tsx`, etc: un `export default function`,
   fetch a `/api/*` con `useEffect`, sin dependencia de router).
2. Registrar la vista en el tipo `AppView`. En `origin/mejoras` ese tipo vive
   en `web/src/components/AppShell.tsx` (export `type AppView = 'hub' | ... `,
   `web/src/components/AppShell.tsx:8-19` en el worktree de `mejoras`); en el
   checkout principal (mas adelantado) el tipo se movio a
   `web/src/data/profiles.ts` y `AppShell.tsx` lo re-exporta
   (`export type { AppView, WorkspaceMode };`). Agregar el nuevo id de vista
   ahi (ej. `'mi-panel'`).
3. Importar y renderizar el componente en `web/src/App.tsx`, agregando una
   linea al `import` y otra al render condicional dentro de `<AppShell>`
   (ver `web/src/App.tsx:3-13` para los imports y `:31-41` para el bloque
   `{view === 'x' && <XPanel />}`).
4. Agregarlo al nav del perfil/workspace que corresponda: en `mejoras`, a
   uno de los arrays `RD_NAV` / `STUDIO_NAV` / `CULTURA_NAV` dentro de
   `AppShell.tsx`; en el sistema con `profiles.ts` (ver seccion 5), al
   array `nav: NavItem[]` del perfil correspondiente en
   `web/src/data/profiles.ts`. El objeto `NavItem` pide `view`, `icon`
   (de `lucide-react`), `label`, `desc` y `edit` (`true` si el panel
   produce/edita algo, `false` si es solo consulta -- controla en que
   seccion del sidebar aparece).
5. **Typecheck obligatorio antes de dar el panel por terminado**:
   ```bash
   cd web && npm run typecheck && npm run build:context
   ```
   `npm run typecheck` corre `tsc --noEmit`; si el `AppView` nuevo no esta
   registrado en todos los lugares que lo usan, tsc lo marca. `build:context`
   regenera `context/*.html` (ver seccion 1) -- sin este paso el panel nuevo
   no aparece en la app real.

## 5. Agregar un perfil

El sistema declarativo de perfiles (`web/src/data/profiles.ts`, con
`docs/HUB_PERFILES.md` documentando el detalle completo incluyendo el perfil
oculto de distribucion `rd-plano`) YA esta documentado ahi: no se duplica
aca. Referencia: `docs/HUB_PERFILES.md`.

**Advertencia (ver seccion 2):** al 2026-07-25, `docs/HUB_PERFILES.md` y
`web/src/data/profiles.ts` no existen todavia en `origin/mejoras`. Si tu
checkout esta parado en `mejoras` sin ese merge, agregar un "perfil" hoy
significa editar los arrays `RD_NAV`/`STUDIO_NAV`/`CULTURA_NAV` y los
botones del selector de workspace directamente en
`web/src/components/AppShell.tsx` (no hay archivo separado todavia).

## 6. Agregar un icono al plano

Los iconos del plano/rider viven en `src/flujo/plano/iconos.py` (glyphs SVG
portados 1:1 desde `symbolIconMarkup` en `web/src/components/PlanoTool.tsx`,
para que el PDF y el editor web muestren el mismo simbolo). Pasos:

1. Escribir la funcion `_glyph_mi_icono(cx, cy, s, c, sw)` que devuelve el
   markup SVG centrado en `(cx, cy)` (ver cualquiera de las funciones
   existentes, ej. `_glyph_tent` o `_glyph_water` en
   `src/flujo/plano/iconos.py:61-64` / `:47-51`, usan los helpers `_hx`/`_hy`
   para escalar sobre una grilla de referencia de 160x160).
2. Agregar el color en el dict `COLORES` (`src/flujo/plano/iconos.py:15-22`)
   con la misma clave que usaras como `key` del icono.
3. Agregar la etiqueta legible en el dict `ETIQUETAS`
   (`src/flujo/plano/iconos.py:24-31`).
4. Registrar la funcion en el dict `_GLYPHS`
   (`src/flujo/plano/iconos.py:167-175`), mapeando la misma `key`.
5. Si el icono debe aparecer automaticamente segun reglas del evento (no solo
   a mano), agregarlo a la logica de `simbolos_de_evento()`
   (`src/flujo/plano/iconos.py:190-204`, ej. condicionado a
   `incluye_testeo`, duracion, o `es_masivo(ev)`).
6. La paleta en `COLORES` debe espejar `ZONE_COLORS` de
   `web/src/components/PlanoTool.tsx` -- si el color no coincide, el PDF y el
   editor web se ven distintos para el mismo icono.

## 7. Verificacion antes de entregar

```bash
py -m compileall src/flujo
py -m pytest tests/ -q
cd web && npm run typecheck && npm run build:context && cd ..
py -m flujo verify
```

Salvedad del repo (doctrina fechada 2026-07-20, `docs/handoffs/archive` PR
#97): el veredicto de un PR es su matriz de CI (ubuntu + windows), **nunca**
el `pytest` local en un worktree -- el editable install importa del checkout
principal (ver nota de origen al inicio de este documento), y el worktree
puede terminar testeando codigo distinto al que cree que esta testeando.
Correr la verificacion local igual por higiene, pero no declararla veredicto
final; eso lo da CI.

## 8. Trampas ya pagadas (no volver a caer)

- **El rider RD no lleva bloque de contactos.** Decision del area de eventos
  de RD (2026-07-25): el rider se presenta a productoras externas y no debe
  pedir ni asociar nombres/telefonos de nadie del equipo; la coordinacion del
  dia se maneja por otro canal. Ver el comentario en
  `web/src/components/PlanoTool.tsx:1006-1008` ("Sin bloque de contactos a
  proposito"). No reagregarlo.

- **La app no procesa jobs pendientes al arrancar sin pedirlo explicitamente
  -- pero el estado exacto de esto depende de que codigo tengas checkeado.**
  El flag real, verificado con `py -m flujo app --help`, es
  `--procesar-pendientes` (default `False`; ver seccion 1). La causa
  original: `run_pending_flyers()` (`src/flujo/automation.py:11`, firma
  `base_dir: str | Path | None = None`) se llamaba desde
  `run_server()` con el kwarg `root=` en vez de `base_dir=`. Eso disparaba un
  `TypeError` que un `except Exception` tapaba en silencio -- la
  automatizacion nunca corria y nadie lo notaba. Al corregir el nombre del
  argumento se encendio de golpe un comportamiento que llevaba tiempo
  apagado: la primera corrida proceso 7 jobs y creo un proyecto sin que
  nadie lo pidiera. La correccion definitiva fue hacerlo opt-in con el flag
  (ver el comentario "Procesar jobs al arrancar es OPT-IN a proposito" en
  `run_server()`, `src/flujo/web/hub.py`, checkout principal). **Importante:**
  al 2026-07-25, `origin/mejoras` (la rama base de este documento) todavia
  tiene la version vieja y rota: `run_server()` llama a
  `run_pending_flyers(root=...)` sin flag ni gate (ver
  `src/flujo/web/hub.py:1401-1408` en el worktree de `mejoras`), y no existe
  `--procesar-pendientes` en su `cli.py`. En la practica esto significa que
  en `mejoras` la automatizacion sigue fallando en silencio en cada arranque
  (el bug la mantiene inerte) hasta que el fix de arriba se mergee. El
  endpoint manual `/api/auto-pending-flyers` (POST,
  `src/flujo/web/hub.py:506-513` en `mejoras`) SI usa `base_dir=` correcto y
  funciona si se lo dispara a mano.

- **Los logos de productoras no se recortan de flyers; se consiguen por
  fuente oficial.** Comentario real en
  `web/src/components/RdDbPanel.tsx:12-13`: el logo se busca en la fuente
  oficial de la productora y se guarda junto a su URL de origen; nunca se
  recorta de un flyer (derivado de baja calidad, sin fuente verificable). Y
  nunca via Instagram con la sesion personal del usuario.

- **La IP del telefono (panel de show) cambia por DHCP en cada venue: hay
  que actualizarla antes del show.** Ver el aviso en
  `web/src/components/ShowPanel.tsx:187-190` ("la IP cambia sola en un venue
  con DHCP: si el panel no responde, buscá la IP real antes que nada").

- **El servidor del telefono no arranca solo despues de un reboot.** Mismo
  aviso, `web/src/components/ShowPanel.tsx:187`: si el telefono se apago
  (bateria a 0, por ejemplo), hay que lanzarlo a mano desde Termux
  (`sh /sdcard/xio_termux/run_server.sh`).

- **Los nombres de archivo de logos no siempre coinciden con el slug de la
  productora** (ej. `grid_system.svg` en disco vs slug `gridsystem`; o
  `club_freedom.svg` vs slug `freedom`). El endpoint `_get_rd_db`
  (`src/flujo/web/hub.py:888-939`, checkout principal) tolera esa diferencia
  a proposito: resuelve primero por el yaml referenciado, despues por el
  slug exacto, y si ninguno matchea, por comparacion normalizada (sin
  guiones ni guiones bajos). No "arregles" un reporte de "sin vector" sin
  mirar primero si el archivo existe en disco con otro nombre.

## 9. No verificado

- No se corrio `py -m pytest tests/ -q` ni `py -m flujo verify` de forma
  completa como parte de este trabajo mas alla de lo pedido explicitamente
  en la seccion 7 (ver reporte de verificacion entregado junto con este
  documento); si el estado cambio entre la redaccion y la lectura, los
  numeros de linea citados pueden haberse corrido.
- No se pudo verificar en vivo si `--procesar-pendientes` mergeado a
  `mejoras` deja la automatizacion funcionando igual que en el checkout
  principal (no se disparo el flag real contra jobs de prueba); la
  descripcion de la seccion 8 se basa en lectura de codigo, no en una
  corrida observada.
- No se verificaron `RdDbPanel.tsx`, `AutomatizacionesPanel.tsx` ni
  `ShowPanel.tsx` corriendo contra un backend real (solo lectura de codigo
  fuente) porque esos paneles no existen todavia en el frontend de
  `origin/mejoras`.
