# 🤝 Handoff — Airdrop combinado v0.31.0 → v0.33.2

**Fecha:** 2026-06-21
**Versión origen:** 0.31.0 (estado actual del repo remoto)
**Versión destino:** 0.33.2
**Aplicar con:** `flujo airdrop apply "v0.33.2 - airdrop combinado: limpieza, plano módulo, costos, editor, fixes y hotfixes Windows"`

---

## 🎯 Resumen ejecutivo

Este airdrop es **una entrega única** que contiene **todos los cambios** desde v0.31.0 hasta v0.33.2, incluyendo el hotfix definitivo para el error de encoding en `plano_stands.py` en Windows.

Incluye:

1. **Limpieza del repo** — elimina carpetas temporales de Instagram commitadas por error.
2. **Integración de `plano`** como módulo real de flujo (`src/flujo/plano/`).
3. **Nuevos comandos** `flujo plano`, `flujo plano --rider`, `flujo plano --costs`.
4. **Editor visual** autocontenido para planos de stands.
5. **Fixes de calidad** — Pillow 14, script roto, privacidad (Luhn), cache de rutas.
6. **Hotfix Windows #1** — `plano_stands.py` robusto con `PYTHONPATH` + `sys.path`.
7. **Hotfix Windows #2** — `plano_stands.py` reconfigura stdout a UTF-8; flecha `→` cambiada por `->`.
8. **Tests** para plano y módulos afectados.
9. **Documentación sincronizada** a v0.33.2.

---

## 🚀 Cómo aplicar

### 1. Descomprimir el ZIP en la raíz del repo

```bash
cd flujo
unzip airdrop_2026-06-21_combinado_v0.31.0_a_v0.33.2.zip
```

### 2. Revisar el dry-run

```bash
flujo airdrop dry-run
```

Debería listar **21 archivos**:

```
REPLACE  .gitignore
REPLACE  HANDOFF_2026-06-21_combinado_v0.31.0_a_v0.33.2.md
REPLACE  PARA_IA.md
REPLACE  README.md
REPLACE  docs/AGENT_GUIDE.md
REPLACE  projects/plano/plano_editor.html
REPLACE  projects/plano/plano_stands.py
REPLACE  pyproject.toml
REPLACE  scripts/cleanup_ig_temp_folders.sh
REPLACE  scripts/sanitize_sensitive.py
REPLACE  src/flujo/airdrop.py
REPLACE  src/flujo/analyze/colors.py
REPLACE  src/flujo/cli.py
REPLACE  src/flujo/paths.py
REPLACE  src/flujo/plano/__init__.py
REPLACE  src/flujo/plano/costs.py
REPLACE  src/flujo/plano/engine.py
REPLACE  src/flujo/privacy/scan.py
REPLACE  src/flujo/version.py
REPLACE  tests/test_plano_module.py
REPLACE  tests/test_plano_stands.py
```

### 3. Eliminar carpetas temporales de Instagram (paso manual)

El airdrop **solo copia archivos**, no puede eliminar carpetas. Las 4 carpetas `C：/Users/issvk/AppData/Local/Temp/ig_*` están commitadas en v0.31.0 y deben eliminarse manualmente antes del commit. El script incluido lo hace:

```bash
bash scripts/cleanup_ig_temp_folders.sh

# Verificar que desaparecieron:
ls -d C：*/ 2>/dev/null || echo "OK"
```

### 4. Aplicar el airdrop

```bash
flujo airdrop apply "v0.33.2 - airdrop combinado: limpieza, plano módulo, costos, editor, fixes y hotfixes Windows"
```

Esto hace: backup → copiar archivos → checkpoint → push.

### 5. Reinstalar

```bash
py -m pip install -e .
```

### 6. Verificar

```bash
flujo version
flujo health
flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider
flujo plano projects/plano/ejemplos/evento_ejemplo.json --costs
py -m pytest tests/ -q
```

---

## ✅ Verificación realizada

Se probó el airdrop desde un clon limpio en v0.31.0:

```text
flujo version              → 0.33.2
flujo health               → OK
flujo plano ... --rider    → rider correcto
flujo plano ... --costs    → cotización referencial $565.000
flujo plano ... -o plano.svg → SVG generado
py -m pytest tests/ -q     → 132 passed, 1 skipped
python -m compileall ...   → sin errores de sintaxis
flujo privacy scan ...     → tarjeta válida detectada, inválida ignorada
```

---

## 📝 Detalle completo de cambios

### A. Limpieza y fixes (v0.32.0)

| Cambio | Archivo | Motivo |
|---|---|---|
| Eliminar carpetas temp IG | `.gitignore`, `scripts/cleanup_ig_temp_folders.sh` | 4 carpetas `C：/Users/.../Temp/ig_*` con descargas de Instagram |
| Fix Pillow 14 | `src/flujo/analyze/colors.py` | `Image.getdata()` obsoleto; usa `get_flattened_data()` con fallback |
| Fix script roto | `scripts/sanitize_sensitive.py` | `SyntaxError` por string sin cerrar; faltaba cuerpo del script |
| Fix motor airdrop | `src/flujo/airdrop.py` | Permitir actualizar `.gitignore` desde un airdrop |
| Tests plano script | `tests/test_plano_stands.py` | Cubre SVG, rider, evento pequeño y masivo |
| Sincronía docs | `README.md`, `PARA_IA.md`, `docs/AGENT_GUIDE.md` | Actualizar a v0.33.2 |

### B. Plano como módulo (v0.33.0)

| Cambio | Archivo | Motivo |
|---|---|---|
| Motor de planos | `src/flujo/plano/__init__.py`, `engine.py`, `costs.py` | Lógica importable y testeable |
| CLI usa módulo | `src/flujo/cli.py` | `flujo plano` sin `subprocess` |
| Costos | `src/flujo/plano/costs.py` + flag `--costs` | Cotización referencial automática |
| Editor HTML | `projects/plano/plano_editor.html` | Editor visual autocontenido |
| Wrapper script | `projects/plano/plano_stands.py` | Compatibilidad con el script original |
| Cache rutas | `src/flujo/paths.py` | `repo_root()` con `@lru_cache` |
| Plano base | `src/flujo/paths.py` | Nueva función `plano_base()` |
| Validación Luhn | `src/flujo/privacy/scan.py` | Reduce falsos positivos en tarjetas |
| Tests módulo | `tests/test_plano_module.py` | Cubre engine, layout, costos, carga |

### C. Hotfixes Windows (v0.33.1 + v0.33.2)

| Cambio | Archivo | Motivo |
|---|---|---|
| Robustecer import | `projects/plano/plano_stands.py` | Ahora intenta `sys.path` + `PYTHONPATH` e imprime traceback |
| Subprocess con PYTHONPATH | `tests/test_plano_stands.py` | Inyecta `src/` en `PYTHONPATH` para el subproceso |
| Encoding UTF-8 | `projects/plano/plano_stands.py` | Reconfigura stdout/stderr a UTF-8 para evitar `cp1252` |
| Flecha ASCII | `src/flujo/plano/engine.py` | `→` cambiada por `->` en el rider |
| Diagnóstico | `projects/plano/plano_stands.py` + `tests/test_plano_stands.py` | Si falla, se ve el error real en stderr |

---

## 🔮 Próximos pasos sugeridos

1. **Ajustar precios reales** en `src/flujo/plano/costs.py` con el dueño.
2. **Integrar plano en el pipeline de jobs** para briefs de intervención en terreno.
3. **Conectar el editor HTML con backend** para no duplicar lógica en JS.
4. **Layouts más realistas** — escenario, accesos, baños, zona médica.
5. **Exportar PDF** del plano + rider + costos.

---

## 📦 Estructura del ZIP

```
airdrop_2026-06-21_combinado_v0.31.0_a_v0.33.2.zip
└── _airdrop/
    ├── HANDOFF_2026-06-21_combinado_v0.31.0_a_v0.33.2.md
    ├── .gitignore
    ├── README.md
    ├── PARA_IA.md
    ├── pyproject.toml
    ├── docs/
    │   └── AGENT_GUIDE.md
    ├── projects/
    │   └── plano/
    │       ├── plano_stands.py
    │       └── plano_editor.html
    ├── scripts/
    │   ├── cleanup_ig_temp_folders.sh
    │   └── sanitize_sensitive.py
    ├── src/
    │   └── flujo/
    │       ├── airdrop.py
    │       ├── analyze/
    │       │   └── colors.py
    │       ├── cli.py
    │       ├── paths.py
    │       ├── plano/
    │       │   ├── __init__.py
    │       │   ├── engine.py
    │       │   └── costs.py
    │       ├── privacy/
    │       │   └── scan.py
    │       └── version.py
    └── tests/
        ├── test_plano_module.py
        └── test_plano_stands.py
```

---

## 🙏 Nota para la siguiente IA

- Este airdrop es **monolítico**: contiene todo desde v0.31.0 hasta v0.33.2.
- El módulo canónico de planos es `src/flujo/plano/`. No duplicar lógica en `projects/plano/plano_stands.py` ni en el editor HTML.
- Los costos son **referenciales** y están hardcodeados; el siguiente paso es externalizarlos a un JSON de configuración.
- El editor HTML duplica la lógica del motor en JS. Si crece, conviene servirlo con backend para reusar `flujo.plano`.
