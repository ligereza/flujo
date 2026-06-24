# Alternativa gratuita a monday.com: GitHub + flujo

Objetivo: recibir pedidos, conectarlos con el repo y permitir que jefatura vea avance o pida cambios sin pagar monday.com.

## Decisión recomendada

Usar una combinación 100% gratuita/local-first:

1. **Gmail** = canal natural de recepción.
2. **Google Apps Script** = puente gratuito Gmail → GitHub Issues (ver `docs/GMAIL_A_REPO_GRATIS.md`).
3. **GitHub Issues** = entrada de pedidos y cambios.
4. **GitHub Projects** = tablero visual tipo kanban para jefatura.
5. **`flujo portal`** = portal HTML simple generado desde `jobs/` para compartir estado.
6. **`flujo intake json` / hub** = conversión del pedido a job/brief/proyecto.

No reemplaza al diseño manual: solo ordena recepción, estados, comentarios y trazabilidad.

---

## Flujo operativo

```txt
Jefe/cliente
  ├─ Nuevo pedido en GitHub Issue Form: "Pedido de diseño"
  ├─ Cambio/corrección en Issue Form: "Cambio / corrección"
  ▼
GitHub Issues + GitHub Project
  ├─ estado/por-revisar
  ├─ estado/pendiente-datos
  ├─ estado/listo
  ├─ estado/en-diseno
  ├─ estado/revision
  └─ estado/entregado
  ▼
Diseñador / flujo
  ├─ copia datos al hub o JSON
  ├─ `flujo intake json ...` o `flujo job new --email ...`
  ├─ trabaja en `jobs/` + `projects/`
  └─ `flujo portal` para exportar vista simple
```

---

## Setup en GitHub

### 1. Crear un GitHub Project gratuito

En el repo:

1. Ir a **Projects** → **New project**.
2. Elegir vista **Board**.
3. Campos sugeridos:
   - `Status`: Por revisar / Pendiente datos / Listo / En diseño / Revisión / Entregado.
   - `Prioridad`: Alta / Media / Baja.
   - `Fecha límite`.
4. Agregar automatizaciones básicas:
   - issue nuevo con label `pedido` → Por revisar.
   - issue con label `cambio` → Por revisar.

### 2. Usar Issue Forms incluidos

Este repo ahora incluye:

- `.github/ISSUE_TEMPLATE/pedido_diseno.yml`
- `.github/ISSUE_TEMPLATE/cambio_diseno.yml`
- `.github/ISSUE_TEMPLATE/config.yml`

El jefe no necesita escribir markdown: completa formulario.

### 3. Labels recomendados

Crear estos labels en GitHub si no existen:

```txt
pedido
cambio
estado/por-revisar
estado/pendiente-datos
estado/listo
estado/en-diseno
estado/revision
estado/entregado
prioridad/alta
prioridad/media
prioridad/baja
bloqueado
```

---

## Portal visual para jefatura

Generar HTML local:

```bash
py -m flujo portal
```

Con enlaces al repo:

```bash
py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine
```

Salida por defecto:

```txt
context/portal_jefe.html
```

Qué muestra:

- columnas por estado (`pendiente_datos`, `listo_para_disenar`, `en_diseno`, etc.);
- total de pedidos, abiertos, con pendientes y entregados;
- tarjetas con tipo, medida, cliente y próxima acción;
- botones para “Nuevo pedido” y “Pedir cambio” si se entrega `--repo-url`.

Privacidad: no muestra el texto original completo del pedido; solo metadata del brief.

---

## Cómo conectar issue → job por ahora

Manual/simple:

1. Jefe crea issue con formulario.
2. Diseñador copia el contenido al hub (`flujo app`) o a un JSON.
3. Ejecuta:

```bash
py -m flujo intake json inbox/pedido.json
# o
py -m flujo job new "nombre" --email inbox/correo.txt
py -m flujo job prepare jobs/<job>
```

Futuro automático:

- GitHub Action que lea el issue form y genere un JSON en `inbox/` o un job.
- Debe revisarse privacidad antes de commitear datos reales al repo.

---

## Reglas de privacidad

- Si el repo es público, no poner pedidos reales con datos sensibles en issues.
- Si se usan datos reales, preferir repo privado y colaboradores mínimos.
- Antes de enviar texto a IA externa:

```bash
py -m flujo privacy scan archivo.txt
py -m flujo privacy sanitize archivo.txt
```

---

## Siguiente mejora sugerida

Implementar `flujo issue import <url|numero>` o una GitHub Action que convierta automáticamente un issue form en `intake JSON`, con sanitización previa y confirmación humana.
