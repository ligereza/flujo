# flujo · pedidos, jobs y portal visual

**flujo** ordena pedidos de diseño y los convierte en trabajo trazable: pedido -> job -> brief -> diseño -> revisión -> entrega.

Este repositorio funciona como un sistema creativo y operativo para recibir pedidos, delegar trabajo, revisar entregables y mantener una línea de marca coherente.

Paleta visual actual: **PURPLE**.

## Estado operativo actual

- Hub pro en `flujo app` con intake, visualizadores, delegación y herramientas.
- Rol de Creative Director integrado para estrategia, revisión final y coordinación.
- Delegación especializada para visual, pipeline, brand, future y packaging.
- Workflow listo para eventos, suplementos, briefs, jobs y entregas visuales.

```txt
Gmail / WhatsApp / GitHub Issue
  -> pedido ordenado por area
  -> job o descarga Instagram
  -> diseno / revision / entrega
  -> portal visual para jefatura
```

---

## 1. Lectura obligatoria para agentes

Si eres una IA o vas a retomar el repo, lee en este orden:

1. `context/LAST_HANDOFF.md`  
   Fuente principal de continuidad. Esta en ASCII-only para evitar errores en Windows/Git Bash.
2. `docs/AGENT_OPERATING_MANUAL.md`  
   Manual operativo de agentes, delegacion y forma de trabajar.
3. `docs/FLUJO_AREAS_EVENTOS_SUPLEMENTOS.md`  
   Explica las dos rutas reales de pedidos: EVENTOS y SUPLEMENTOS.
4. `docs/GMAIL_A_REPO_GRATIS.md`  
   Explica como Gmail crea Issues sin monday.com.
5. `docs/REMOTE_WEB_IA_WORKFLOW.md`  
   Plantilla práctica para pedir ayuda a una IA web con contexto del repo y flujo de suplementos.

Reglas para agentes:

```txt
- El usuario trabaja en Windows + Git Bash.
- Usar py, no python, en instrucciones para el usuario.
- Mantener context/LAST_HANDOFF.md en ASCII-only.
- No guardar tokens, credenciales ni datos sensibles.
- Entregar cambios como airdrop si no hay acceso directo al repo.
```

---

## 2. Entrada diaria

En Windows / Git Bash:

```bash
py -m flujo app
```

Generar un prompt listo para IA web a partir de un pedido o correo:

```bash
py -m flujo ai-prompt "Necesito cotizar suplementos" --area suplementos
```

Modo escritorio:

```bash
py -m flujo app --desktop
```

Verificar estado:

```bash
py -m flujo verify
```

---

## 3. Flujo real por areas

### EVENTOS

Entrada esperada:

```txt
Correo con asunto que contiene "eventos" o "evento"
```

Uso:

```txt
EVENTOS -> link Instagram -> descarga con flujo/instaloader -> automatizacion Photoshop local
```

Tambien puede pedir:

```txt
brief / plano app / SVG / pieza visual
```

En esos casos se crea job normal.

### SUPLEMENTOS

Entrada esperada:

```txt
Correo con asunto que contiene "suplementos" o "suplemento"
```

Uso:

```txt
SUPLEMENTOS -> nuevo pedido / modificacion / correccion / cotizacion
```

Piezas posibles:

```txt
etiqueta / flyer / pendon / post Instagram / stickers / stand / logo-sello / brief comercial
```

Documento operativo:

```txt
docs/FLUJO_AREAS_EVENTOS_SUPLEMENTOS.md
```

---

## 4. Gmail sin monday.com

No se conecta Gmail directo al repo. Gmail crea **GitHub Issues**.

Configuracion recomendada en Google Apps Script:

```txt
GITHUB_TOKEN = github_pat_...
GITHUB_REPO = ligereza/vibecodeine
GMAIL_LABEL_DONE = flujo-procesado
MAX_THREADS = 10
GMAIL_LOOKBACK = 7d
GMAIL_ROUTES = subject:eventos|EVENTOS|pedido,area/eventos,estado/por-revisar,gmail,instagram,action/descargar-ig;subject:evento|EVENTOS|pedido,area/eventos,estado/por-revisar,gmail,instagram,action/descargar-ig;subject:suplementos|SUPLEMENTOS|pedido,area/suplementos,estado/por-revisar,gmail;subject:suplemento|SUPLEMENTOS|pedido,area/suplementos,estado/por-revisar,gmail
```

Con esto no necesitas escribir "flujo" en el asunto.

Ejemplos de asunto:

```txt
Eventos - flyer viernes
Suplementos - modificar etiqueta Omega 3
```

Script:

```txt
tools/gmail_to_github_issues.gs
```

Guia:

```txt
docs/GMAIL_A_REPO_GRATIS.md
```

---

## 5. GitHub Issues y Projects

Templates activos:

```txt
.github/ISSUE_TEMPLATE/pedido_eventos.yml       -> [EVENTOS]
.github/ISSUE_TEMPLATE/pedido_suplementos.yml   -> [SUPLEMENTOS]
.github/ISSUE_TEMPLATE/cambio_diseno.yml        -> [Cambio]
.github/ISSUE_TEMPLATE/revision_privacidad.yml  -> [Privacidad]
```

Labels recomendados:

```txt
area/eventos
area/suplementos
instagram
action/descargar-ig
action/crear-job
action/cotizar
estado/por-revisar
estado/pendiente-datos
estado/en-diseno
estado/revision
estado/entregado
```

---

## 6. Portal para jefatura

Generar portal visual:

```bash
py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine
```

Salida:

```txt
context/portal_jefe.html
```

Muestra estados, pendientes y proximas acciones sin usar monday.com.

---

## 7. Jobs e intake

Crear job desde correo/texto:

```bash
py -m flujo job new "nombre pedido" --email inbox/correo.txt
py -m flujo job prepare jobs/<job>
```

Intake JSON:

```bash
py -m flujo intake json inbox/pedido.json
```

Genera:

```txt
jobs/<folio>/brief.yaml
jobs/<folio>/estado.md
jobs/<folio>/resultado.md
```

Cotizacion multiformato:

```bash
py -m flujo brief paquete-cotizacion jobs/<job>
```

---

## 8. EVENTOS: descarga Instagram + Photoshop local

Para EVENTOS con link Instagram ahora hay un comando directo para tu PC:

```bash
py -m flujo eventos flyer-auto "https://www.instagram.com/p/XXXX/"
```

Hace esto:

```txt
descarga Instagram con instaloader
copia la primera imagen a C:\rd\AUTOMATIZACION\input_ig.jpg
genera C:\rd\AUTOMATIZACION\palette_ig.png
genera C:\rd\AUTOMATIZACION\palette_ig.json
NO abre Photoshop ni Blender por defecto
```

Cuando quieras autorizar el droplet:

```bash
py -m flujo eventos flyer-auto "https://www.instagram.com/p/XXXX/" --run-droplet
```

Para renderizar una vista previa de Blender:

```bash
py -m flujo eventos flyer-auto "https://www.instagram.com/p/XXXX/" --render-blender
```

Eso usa:

```txt
C:\rd\AUTOMATIZACION\cartelera.blend
```

y genera:

```txt
C:\rd\AUTOMATIZACION\preview_cartelera.png
```

Si quieres renderizar y abrir Blender:

```bash
py -m flujo eventos flyer-auto "https://www.instagram.com/p/XXXX/" --render-blender --open-blender
```

El comando pregunta antes de abrir apps externas:

```txt
Droplet_Flyer.exe + historia.psd
cartelera.blend
```

Rutas esperadas en Windows:

```txt
C:\rd\AUTOMATIZACION\Droplet_Flyer.exe
C:\rd\AUTOMATIZACION\historia.psd
C:\rd\AUTOMATIZACION\cartelera.blend
C:\rd\AUTOMATIZACION\input_ig.jpg
C:\rd\AUTOMATIZACION\palette_ig.png
C:\rd\AUTOMATIZACION\preview_cartelera.png
```

Regla:

```txt
Usar instaloader. No usar yt-dlp.
```

Tu automatizacion Photoshop queda local y bajo autorizacion humana.

---

## 9. Comandos utiles

```bash
py -m flujo health
py -m flujo version
py -m flujo verify
py -m flujo app
py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine
py -m flujo render formats
py -m flujo clean
```

---

## 10. Airdrops

Flujo normal recomendado:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "mensaje"
```

Ese es el camino principal. No uses flags extra salvo que el validador o el handoff lo pidan explicitamente.

Si un apply ya se hizo y fallo despues en checks/checkpoint:

```bash
py scripts/run_airdrop_checks.py --resume "mensaje"
```

Si un airdrop modifica el motor de airdrop, recien ahi validar con:

```bash
py scripts/validate_airdrop.py --allow-airdrop-engine
py scripts/run_airdrop_checks.py "mensaje" --allow-airdrop-engine
```

Regla practica antes de correr el runner:

```bash
git status --short
```

Si aparecen carpetas pesadas o de otro proyecto, como `logo3d/`, sacarlas del repo o agregarlas al ignore antes de ejecutar el checkpoint automatico.

Si el airdrop trae un script de limpieza, correrlo despues de aplicar.

Reglas:

```txt
- No guardar tokens.
- No commitear datos sensibles.
- No borrar sin listar antes.
- Mantener LAST_HANDOFF actualizado y ASCII-only.
- No dejar carpetas pesadas locales dentro del repo antes de un airdrop.
```

### Proyecto activo: logo_clean_lab

Proyecto experimental para limpieza de logos en Illustrator:

```txt
projects/logo_clean_lab/
tools/illustrator/scripts/logo_clean_master.jsx
```

Goal corto:

```txt
Probar y mejorar un script que alinee nodos horizontales/verticales, reduzca puntos extra y preserve curvas en letras mixtas como B/R/P/D.
```

Summary corto:

```txt
El logo ya existe y visualmente esta correcto; el script solo corrige imperfecciones pequenas. El aprendizaje se registra con reportes y resultados para ajustar reglas con evidencia.
```

---

## 11. Estructura principal

```txt
src/flujo/        codigo principal
context/          handoff, portal, reportes
jobs/             trabajos locales
projects/         proyectos visuales
schemas/          intake JSON
docs/             manuales operativos
tools/            scripts auxiliares
.github/          issue templates y workflows
```

---

## 12. Proxima mejora recomendada

Implementar:

```bash
py -m flujo issue import <numero-o-url>
```

Objetivo:

```txt
GitHub Issue [EVENTOS] + instagram -> preparar descarga
GitHub Issue [SUPLEMENTOS] -> crear job/intake/cotizacion
```

---

## Licencia

MIT
