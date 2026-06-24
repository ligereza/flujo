# flujo · Portal de pedidos + diseño operativo

> **Paleta PURPLE:** `#12001f` fondo · `#2b0a3d` panel · `#6d28d9` purple principal · `#a855f7` acento · `#f5e8ff` papel.

**flujo** es un sistema local/gratuito para ordenar pedidos de diseño, convertirlos en jobs trazables y mostrar avance a jefatura sin monday.com.

La idea principal:

```txt
Gmail / WhatsApp / GitHub Issue
  → pedido ordenado
  → job en flujo
  → diseño / revisión / entrega
  → portal visual para jefatura
```

---

## 1. Resumen corto

flujo sirve para:

- recibir pedidos de diseño sin perder información;
- separar **texto** vs **imagen/diseño**;
- crear `jobs/` con estado, pendientes y próxima acción;
- generar briefs y cotizaciones base;
- mostrar avance a un jefe/cliente con un portal visual;
- trabajar con herramientas gratuitas: Gmail, Google Apps Script, GitHub Issues/Projects y HTML local.

No reemplaza el diseño manual. Ordena el flujo alrededor del diseño.

---

## 2. Entrada diaria

**Windows / Git Bash:** usar siempre `py`, no `python`.

La entrada principal es:

```bash
py -m flujo app
```

Tambien puedes abrir modo escritorio:

```bash
py -m flujo app --desktop
```

Desde ahí usas el hub para:

- pegar pedidos;
- revisar jobs;
- ver visualizadores SVG/plano;
- delegar tareas a agentes;
- consultar comandos.

---

## 3. Flujo gratuito reemplazo monday.com

Como monday.com no se usará, el flujo recomendado es:

```txt
Gmail
  → etiqueta flujo-pedido
  → Google Apps Script
  → GitHub Issue
  → GitHub Project tipo kanban
  → flujo portal
```

### Componentes

| Necesidad | Solución gratis |
|---|---|
| Recibir pedido por correo | Gmail + etiqueta `flujo-pedido` |
| Convertir correo en tarea visible | Google Apps Script → GitHub Issue |
| Que jefatura vea avance | GitHub Project + `flujo portal` |
| Pedir cambios | GitHub Issue Form “Cambio / corrección” |
| Trabajo real de diseño | `jobs/`, `brief.yaml`, `projects/` |
| Vista visual local | `context/portal_jefe.html` |

Guías:

- [`docs/GMAIL_A_REPO_GRATIS.md`](docs/GMAIL_A_REPO_GRATIS.md)
- [`docs/PORTAL_JEFE_GRATIS.md`](docs/PORTAL_JEFE_GRATIS.md)

---

## 4. Portal para jefatura

Generar portal visual:

```bash
py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine
```

Salida:

```txt
context/portal_jefe.html
```

Muestra:

- columnas por estado;
- pedidos abiertos;
- entregados;
- pendientes;
- próxima acción;
- botones de “Nuevo pedido” y “Pedir cambio”.

La paleta del portal está orientada a **PURPLE** para diferenciar esta etapa del sistema.

---

## 5. Gmail → repo

No se recomienda que Gmail escriba directo al repo. Mejor crea Issues.

Script incluido:

```txt
tools/gmail_to_github_issues.gs
```

Funcionamiento:

```txt
Correo con label flujo-pedido
  → Apps Script cada 10 minutos
  → GitHub Issue con labels pedido/estado/por-revisar/gmail
  → correo marcado como flujo-procesado
```

Requiere configurar en Google Apps Script:

```txt
GITHUB_TOKEN
GITHUB_REPO = ligereza/vibecodeine
GMAIL_LABEL_IN = flujo-pedido
GMAIL_LABEL_DONE = flujo-procesado
```

Ver guía completa: [`docs/GMAIL_A_REPO_GRATIS.md`](docs/GMAIL_A_REPO_GRATIS.md).

---

## 6. Pedidos de suplementos RD

Se agregó el brief operativo de suplementos RD:

```txt
docs/BRIEF_SUPLEMENTOS_RD.md
```

Ese brief define cómo trabajar piezas como:

- etiquetas;
- flyers;
- pendones;
- posts de Instagram;
- stickers;
- logo/sello de línea de suplementos;
- stand/eventos.

Regla central para esta área:

```txt
Separar siempre texto / imagen-diseño / formato / fecha / prioridad / referencias.
```

Pendientes relevantes del brief:

- etiqueta Omega 3;
- etiqueta Glicinato de Magnesio;
- ingredientes de gomitas;
- tabla nutricional Post Fiesta;
- pendón con servicios RD;
- flyers con decisión WhatsApp/QR;
- logo o sello línea suplementos;
- paquete mensual Instagram;
- 5 stickers para eventos.

---

## 7. Intake JSON

Para pedidos estructurados:

```bash
py -m flujo intake json schemas/ejemplos/flyer_evento.json
```

Genera:

```txt
jobs/<folio>/brief.yaml
jobs/<folio>/estado.md
jobs/<folio>/resultado.md
```

Documentación:

- [`docs/INTAKE_JSON.md`](docs/INTAKE_JSON.md)

---

## 8. Comandos principales

### Salud y versión

```bash
py -m flujo health
py -m flujo version
py -m flujo verify
```

### App diaria

```bash
py -m flujo app
py -m flujo app --desktop
```

### Jobs

```bash
py -m flujo job new "nombre pedido" --email inbox/correo.txt
py -m flujo job prepare jobs/<job>
py -m flujo job list
py -m flujo job status jobs/<job>
py -m flujo job activate jobs/<job>
```

### Intake JSON

```bash
py -m flujo intake json inbox/pedido.json
```

### Portal

```bash
py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine
```

### Render

```bash
py -m flujo render formats
py -m flujo render run projects/piezas_vectoriales/<proyecto>/config.json
py -m flujo render rescale projects/.../config.json --dpi 300
```

### Limpieza segura

```bash
py -m flujo clean
```

---

## 9. Estados de trabajo

Estados principales:

```txt
borrador
brief_extraido_pendiente_revision
pendiente_datos
listo_para_disenar
en_diseno
generado
entregado
pausado
cancelado
```

Para jefatura se simplifican como:

```txt
Por revisar → Pendiente datos → Listo → En diseño → Revisión → Entregado
```

---

## 10. Protocolo para agentes / airdrops

Regla Windows importante:

```txt
El usuario trabaja en Windows + Git Bash. En documentacion y handoffs usar py, no python.
context/LAST_HANDOFF.md debe mantenerse ASCII-only para evitar letras rotas.
Codigo, nombres de variables y logs pueden ir en ingles si eso evita problemas de encoding.
```

Si una IA modifica el repo debe entregar un **airdrop**:

```txt
airdrop.zip
└── _airdrop/
    ├── README.md
    ├── src/flujo/...
    ├── docs/...
    ├── tests/...
    └── HANDOFF_YYYY-MM-DD.md
```

Validación obligatoria antes de aplicar:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "vX.Y.Z - descripcion"
```

Reglas:

- no guardar tokens;
- no commitear datos sensibles;
- no usar yt-dlp;
- no borrar archivos sin listar antes qué se va a eliminar;
- mantener `context/LAST_HANDOFF.md` actualizado.

---

## 11. Estructura viva del repo

```txt
src/flujo/        paquete principal
context/          portal, handoff, reportes
jobs/             trabajos locales, normalmente no se suben completos
projects/         proyectos visuales y satélites
docs/             documentación operativa
schemas/          intake JSON y ejemplos
tools/            scripts auxiliares, Apps Script, plantillas
.github/          Issue Forms y workflows
```

Histórico y material viejo vive en `.archive/`. No usar como fuente primaria salvo que se pida explícitamente.

---

## 12. Próximas mejoras recomendadas

1. `flujo issue import <numero>` para convertir GitHub Issue en job/intake JSON.
2. Sanitización automática antes de crear Issues desde Gmail.
3. Portal jefe con filtro por área: suplementos / eventos / comercial.
4. Formulario específico de suplementos RD basado en `docs/BRIEF_SUPLEMENTOS_RD.md`.
5. Export instalable/desktop más simple para uso diario.

---

## Licencia

MIT
