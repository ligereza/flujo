# Conectar Gmail con el repo gratis (Gmail → GitHub Issues → flujo)

Objetivo: que un correo entrante cree un pedido visible en GitHub, sin monday.com.

## Recomendación

No conectar Gmail directo a commits del repo. Mejor:

```txt
Gmail
  → etiqueta "flujo-pedido"
  → Google Apps Script
  → GitHub Issue
  → GitHub Project visible para jefatura
  → flujo app / flujo intake json / flujo portal
```

Ventajas:

- gratis;
- tu jefe puede ver estado y comentar en GitHub;
- no se commitean correos completos ni secretos automáticamente;
- funciona aunque tu computador esté apagado, porque Apps Script corre en Google.

---

## Qué archivo usar

Este repo incluye el script listo para copiar:

```txt
tools/gmail_to_github_issues.gs
```

Ese script busca correos con etiqueta `flujo-pedido`, crea un GitHub Issue y luego marca el correo como `flujo-procesado`.

---

## Paso 1 — Crear token de GitHub

En GitHub:

1. Ir a **Settings → Developer settings → Personal access tokens → Fine-grained tokens**.
2. Crear token para el repo `ligereza/vibecodeine`.
3. Permisos mínimos:
   - **Issues: Read and write**
   - opcional: **Metadata: Read-only**
4. Copiar el token.

> No pegues este token en el repo ni en chats. Va solo en Google Apps Script Properties.

---

## Paso 2 — Crear etiquetas en Gmail

En Gmail crea estas etiquetas:

```txt
flujo-pedido
flujo-procesado
```

Puedes crear un filtro, por ejemplo:

- si el asunto contiene `[Pedido]`, aplicar etiqueta `flujo-pedido`;
- o si viene de tu jefe/productora, aplicar etiqueta `flujo-pedido`.

Así tú controlas qué correos se convierten en issues.

---

## Paso 3 — Crear Google Apps Script

1. Ir a <https://script.google.com/>.
2. Crear proyecto nuevo: `flujo Gmail Bridge`.
3. Pegar el contenido de:

```txt
tools/gmail_to_github_issues.gs
```

4. Guardar.

---

## Paso 4 — Configurar Script Properties

En Apps Script:

1. Project Settings → **Script properties**.
2. Agregar:

```txt
GITHUB_TOKEN = github_pat_...
GITHUB_REPO = ligereza/vibecodeine
GMAIL_LABEL_IN = flujo-pedido
GMAIL_LABEL_DONE = flujo-procesado
GITHUB_LABELS = pedido,estado/por-revisar,gmail
MAX_THREADS = 10
```

Mínimas obligatorias:

```txt
GITHUB_TOKEN
GITHUB_REPO
```

---

## Paso 5 — Autorizar y activar trigger

En Apps Script:

1. Seleccionar función `setupFlujoGmailBridge`.
2. Ejecutar.
3. Google pedirá permisos para Gmail y llamadas externas.
4. Aceptar si estás usando tu propia cuenta.

Eso crea un trigger cada 10 minutos para ejecutar:

```txt
processFlujoPedidos
```

---

## Paso 6 — Probar

1. Enviarte un correo de prueba con asunto:

```txt
[Pedido] Flyer evento prueba
```

2. Aplicar etiqueta `flujo-pedido`.
3. Ejecutar manualmente `processFlujoPedidos` o esperar 10 min.
4. Verificar que se creó un issue en:

```txt
https://github.com/ligereza/vibecodeine/issues
```

5. Verificar que el correo quedó con etiqueta `flujo-procesado`.

---

## Cómo entra esto a flujo

Por ahora:

1. El issue queda como bandeja visible para jefatura.
2. Tú copias el contenido al hub:

```bash
py -m flujo app
```

3. O lo transformas en JSON y corres:

```bash
py -m flujo intake json inbox/pedido.json
```

4. Generas portal:

```bash
py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine
```

---

## Privacidad importante

Si el repo es público, no mandes correos reales con datos sensibles a GitHub Issues.

Opciones seguras:

- usar repo privado;
- etiquetar solo correos no sensibles;
- sanitizar manualmente antes;
- en el futuro, agregar sanitización automática antes de crear issue.

Por ahora el script limita cuerpo a 12.000 caracteres, pero no elimina PII.

---

## Alternativa si no quieres GitHub token en Google

Puedes usar un poller local por IMAP, pero requiere que tu computador esté prendido:

```txt
Gmail IMAP → script local → inbox/*.txt/json → flujo job/intake
```

Para Gmail eso implica:

- activar IMAP;
- usar contraseña de aplicación o OAuth;
- guardar credenciales localmente fuera del repo.

Recomendación actual: **Apps Script → GitHub Issue**, porque es gratis, simple y corre en la nube de Google.

---

## Próximo avance técnico sugerido

Implementar uno de estos comandos:

```bash
py -m flujo issue import <numero>
py -m flujo gmail poll
```

Orden recomendado:

1. `flujo issue import <numero>`: convierte un GitHub Issue en `intake JSON`/job.
2. Luego, si hace falta, `flujo gmail poll` local.
