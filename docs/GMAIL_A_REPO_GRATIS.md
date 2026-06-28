# Gmail a GitHub Issues gratis

Objetivo: que un correo cree un Issue visible en GitHub sin usar monday.com.

## Decision actual

No es necesario que el asunto diga "flujo".

Usaremos palabras simples en el asunto:

```txt
eventos
suplementos
```

Ejemplos:

```txt
Eventos - flyer viernes
Suplementos - modificar etiqueta Omega 3
```

El puente queda asi:

```txt
Gmail subject eventos/suplementos
  -> Google Apps Script
  -> GitHub Issue [EVENTOS] o [SUPLEMENTOS]
  -> GitHub Project / flujo app / portal
```

---

## Script usado

```txt
tools/gmail_to_github_issues.gs
```

---

## Paso 1 - Token GitHub

Crear un fine-grained token para:

```txt
ligereza/vibecodeine
```

Permisos:

```txt
Issues: Read and write
Metadata: Read-only
```

No guardar el token en el repo.

---

## Paso 2 - Google Apps Script

1. Ir a <https://script.google.com/>.
2. Crear proyecto nuevo: `flujo Gmail Bridge`.
3. Pegar el contenido de:

```txt
tools/gmail_to_github_issues.gs
```

---

## Paso 3 - Script Properties

En Apps Script:

```txt
Project Settings -> Script properties
```

Agregar:

```txt
GITHUB_TOKEN = github_pat_...
GITHUB_REPO = ligereza/vibecodeine
GMAIL_LABEL_DONE = flujo-procesado
MAX_THREADS = 10
GMAIL_LOOKBACK = 7d
GMAIL_ROUTES = subject:eventos|EVENTOS|pedido,area/eventos,estado/por-revisar,gmail,instagram,action/descargar-ig;subject:evento|EVENTOS|pedido,area/eventos,estado/por-revisar,gmail,instagram,action/descargar-ig;subject:suplementos|SUPLEMENTOS|pedido,area/suplementos,estado/por-revisar,gmail;subject:suplemento|SUPLEMENTOS|pedido,area/suplementos,estado/por-revisar,gmail
```

La propiedad importante es `GMAIL_ROUTES`.

`GMAIL_LOOKBACK = 7d` evita que tome correos muy antiguos. Si quieres probar solo correos de hoy, puedes poner temporalmente `1d`.

Las rutas van separadas (eventos/evento y suplementos/suplemento) para que Gmail no falle con busquedas agrupadas y reconozca asuntos como `Suplementos - etiqueta Omega 3`.


Significa:

```txt
subject eventos/s -> Issue [EVENTOS]
subject suplementos/s -> Issue [SUPLEMENTOS]
```

---

## Paso 4 - Activar

En Apps Script ejecutar una vez:

```txt
setupFlujoGmailBridge
```

Google pedira permisos para Gmail y llamadas externas.

Eso crea un trigger cada 8 horas para:

```txt
processFlujoPedidos
```

---

## Paso 5 - Probar EVENTOS

Enviar o buscar un correo con asunto:

```txt
Eventos - flyer prueba
```

Texto:

```txt
https://www.instagram.com/p/XXXXX/
```

Ejecutar manualmente:

```txt
processFlujoPedidos
```

Debe crear un issue:

```txt
[EVENTOS] Eventos - flyer prueba
```

Labels:

```txt
pedido
area/eventos
estado/por-revisar
gmail
instagram
action/descargar-ig
```

---

## Paso 6 - Probar SUPLEMENTOS

Correo con asunto:

```txt
Suplementos - modificar etiqueta Omega 3
```

Debe crear:

```txt
[SUPLEMENTOS] Suplementos - modificar etiqueta Omega 3
```

Labels:

```txt
pedido
area/suplementos
estado/por-revisar
gmail
```

---

## Procesado

El script agrega la etiqueta:

```txt
flujo-procesado
```

para no procesar el mismo correo de nuevo.

Solo necesitas crear esa etiqueta en Gmail. No necesitas etiquetas `flujo-eventos` ni `flujo-suplementos` si usas asunto.

---

## Si prefieres etiquetas en vez de asunto

Tambien se puede usar labels Gmail. Cambia `GMAIL_ROUTES` a:

```txt
label:flujo-eventos|EVENTOS|pedido,area/eventos,estado/por-revisar,gmail,instagram,action/descargar-ig;label:flujo-suplementos|SUPLEMENTOS|pedido,area/suplementos,estado/por-revisar,gmail
```

Pero la recomendacion actual es por asunto:

```txt
eventos
suplementos
```

---

## Privacidad

Si el repo es publico, cuidado con mandar correos completos a Issues.

Opciones:

```txt
- usar repo privado
- evitar datos sensibles en correos procesados
- sanitizar antes en una futura version
```

---

## Siguiente mejora

Implementar:

```bash
py -m flujo issue import <numero-o-url>
```

Para convertir Issues en jobs sin copiar/pegar.
