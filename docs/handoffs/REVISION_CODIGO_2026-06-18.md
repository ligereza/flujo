# 🔍 Revisión de Código — `flujo` (v0.23.0)

**Fecha:** 2026-06-18
**Revisor:** Arena.ai Agent Mode
**Alcance:** Revisión de arquitectura, bugs y refactor sobre `src/flujo/`

---

## 📊 Resumen ejecutivo

| Métrica | Antes | Después |
|---------|-------|---------|
| Tests pasando | 58/61 (2 fallidos + CLI roto) | **60/61** (1 skip por falta de imagen) |
| `flujo --help` | 💥 SyntaxError — no arranca | ✅ Funciona |
| `flujo airdrop list` | ❌ Ejecutaba el comando equivocado | ✅ Lista versiones correctamente |
| `flujo health` | ❌ No registrado (cabecera perdida) | ✅ Funciona |
| Bugs críticos | 3 | **0** |

**Conclusión:** el CLI estaba **completamente roto** desde el último commit (un SyntaxError impedía importar el módulo). Ya está restaurado y funcionando.

---

## 🚨 Bugs CRÍTICOS encontrados y corregidos

### 1. `SyntaxError` en `cli.py` — f-string multilínea ilegal (línea 109)

El comando `airdrop status` contenía un f-string que cruzaba varias líneas físicas con comillas dobles simples (`f"…\n…"`), lo cual es **inválido en Python**. Como resultado, `import flujo.cli` lanzaba `SyntaxError: unterminated f-string literal` y **todo el CLI dejaba de funcionar**.

```python
# ❌ ANTES (roto)
console.print(f"
[bold cyan]flujo version actual:[/] [bold]{v}[/]
")

# ✅ DESPUÉS (arreglado)
console.print(f"\n[bold cyan]flujo version actual:[/] [bold]{v}[/]\n")
```

### 2. Decoradores mal apilados en la sección `airdrop` (líneas 102–113)

Dos problemas a la vez:
- `@airdrop_app.command("list")` estaba apilado encima de `@airdrop_app.command("status")`, **ambos decorando `airdrop_status`**.
- La función `airdrop_list()` (la que realmente lista versiones) **no tenía ningún decorador** → era código muerto inaccesible.

**Consecuencia:** `flujo airdrop list` ejecutaba `airdrop_status` (mostraba la versión en vez de listar). Corregido asignando cada decorador a su función correcta.

### 3. Función `health` sin cabecera — código huérfano (líneas 202–204)

Durante la adición del feature airdrop se **perdieron** el decorador `@app.command()` y la línea `def health():`. Quedaba el docstring + cuerpo sueltos con indentación a nivel módulo → segundo `SyntaxError` (enmascarado por el #1). Restaurada la cabecera.

---

## ⚙️ Mejoras de calidad aplicadas

| Archivo | Cambio | Motivo |
|---------|--------|--------|
| `cli.py` | Help del app ahora usa versión **dinámica** (`v{get_version()}`) | Decía `v0.16` aunque la versión real era `0.23.0` |
| `cli.py` | Eliminada función `_get_version()` redundante | Duplicaba el import ya existente |
| `lifecycle.py` | `if/else` redundante en `activate_job` colapsado | Ambas ramas hacían exactamente lo mismo (`EN_DISENO`) |
| `lifecycle.py` | Removidos imports no usados: `re`, `subprocess`, `sys`, `repo_root`, `JobInfo`, `job_status` | Código muerto |
| `brief.py` | `_detect_bleed` ya no tiene un no-op (`return None if … else None`) | Línea que siempre devolvía `None` sin sentido |
| `test_smoke.py` | `test_version` ahora valida la versión actual dinámica | Estaba hardcodeado a `"0.16.0"` y fallaba en cada release |

---

## 📝 Observaciones y recomendaciones (NO corregidas aún)

Estos son puntos de calidad / arquitectura que vale la pena abordar a futuro. No rompen nada hoy, pero son deuda técnica:

### Prioridad media

1. **Drift de versión en la documentación.** La versión real es `0.23.0` pero los docs están desincronizados:
   - `README.md` → v0.20
   - `PARA_IA.md` → v0.16
   - `PARA_IA_CONTEXT.md` → v0.20.0
   - `cli.py` docstring del módulo → v0.16

   *Sugerencia:* centralizar la versión en `version.py` (ya hecho) y hacer que los docs la referencien, o al menos actualizar los números.

2. **`privacy/scan.py` — patrón de tarjeta demasiado amplio.**
   ```python
   "tarjeta": re.compile(r"\b(?:\d[ -]?){13,19}\b")
   ```
   Caza cualquier secuencia de 13–19 dígitos, incluyendo números que también matchean `telefono_cl` o `rut_chile` → **doble conteo** de PII y riesgo inflado. Recomendable añadir lookahead de Luhn o delimitarlo más.

3. **`airdrop.py` — `rollback_last()` no limpia el backup** después de restaurar, y `run_auto_checkpoint()` traga errores (`return False` sin detalle). Para un sistema de "deploy", conviene loggear el `stderr`.

4. **`serve()` delega a `scripts/app.py` vía `subprocess`** en lugar de importar la app de Gradio. Es frágil (depende de que el archivo legacy exista) y rompe la promesa de "CLI unificada". Valdría la pena migrar la app a `src/flujo/web/`.

### Prioridad baja

5. **`paths.py` `repo_root()` recorre el filesystem en cada llamada.** Se llama cientos de veces por comando. Se beneficiaría de un `@functools.lru_cache` o un módulo de paths con cache.

6. **`~60 scripts en `scripts/`** parecen duplicar funcionalidad ya cubierta por la CLI (`flyer_from_email.py`, `job_new.sh`, `privacy_scan_text.py`…). El README los llama "utilidades" pero gran parte son *legacy* pre-CLI. Candidatos a archivar.

7. **`brief.py` incluye un parser YAML propio** (`parse_yaml_simple`) a pesar de que `pyyaml` está en `requirements.txt`. Funciona, pero mantener dos parsers es riesgo. Si pyyaml es dependencia garantizada, el custom parser puede quedar solo como fallback explícito.

8. **Higiene de git:** muchos commits con mensajes placeholder (`"nose"`, `"tu mensaje aquí"`, `"ultimavez?"`, `"fixin"`). El checkpoint automático del airdrop es cómodo pero no debería generar mensajes vacíos — conviene exigir un mensaje real.

---

## ✅ Verificación final

```bash
$ python -m flujo --help          # ✅ arranca, muestra v0.23.0
$ python -m flujo health          # ✅ chequeo completo
$ python -m flujo airdrop list    # ✅ lista versiones (no muestra versión)
$ python -m flujo airdrop status  # ✅ muestra versión
$ python -m pytest tests/ -q      # ✅ 60 passed, 1 skipped
$ python -m compileall src/       # ✅ sin errores
```

---

## 🗂️ Archivos modificados

- `src/flujo/cli.py` — arreglos críticos + versión dinámica
- `src/flujo/jobs/lifecycle.py` — dead code + imports
- `src/flujo/jobs/brief.py` — no-op en `_detect_bleed`
- `tests/test_smoke.py` — test de versión dinámico

> **Nota:** estos cambios están en el clon local (`/home/user/flujo`). No se han commiteado ni pusheado al repo remoto. Cuando quieras integrarlos, revisa con `git diff` y haz checkpoint con tu flujo habitual.
