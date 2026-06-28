# PARA IA

**NO HAGAS PUSH SIN LEER TODO ESTO.**

## PUNTO DE ENTRADA ÚNICO DIARIO
```bash
py -m flujo app    # o --desktop
```
Sirve servidor real + APIs + Hub HTML como UI. Si falla, abre `context/flujo_hub.html` estático.

## LECTURA OBLIGATORIA EN ORDEN

1. ✅ **Este archivo** (PARA_IA.md)
2. ✅ `context/LAST_HANDOFF.md` (estado actual, qué pasó)
3. ✅ `docs/AGENT_OPERATING_MANUAL.md` (flujos, delegación)
4. ✅ `docs/HERRAMIENTAS_VISUALES.md` (si tocas HTML visual tools)
5. ✅ `docs/AGENT_GUARDRAILS_VISUAL_TOOLS.md` (la lista NO hacerlo)

**Si vas a modificar herramientas HTML directamente:** Además lee `docs/AGENT_GUARDRAILS_VISUAL_TOOLS.md` PRIMERO.

## COSAS QUE NO SON NEGOCIABLES

| Regla | Por qué |
|---|---|
| **Usa `py`, no `python`** | Windows Git Bash está configurado así |
| **Solo `instaloader`, nunca `yt-dlp`** | Policies |
| **No crees venvs pesados** | Usa entorno del sistema |
| **Privacidad antes de IAs externas** | `py -m flujo privacy scan` |
| **Valida airdrop antes de aplicar** | `py scripts/validate_airdrop.py` |
| **No hagas push sin especificar qué cambió** | HANDOFF o commit detallado |
| **Las herramientas visuales NO son juguetes** | Leen de docs específicos (ver HERRAMIENTAS_VISUALES.md) |

## ÁREAS DE TRABAJO

| Área | Entrada | Formato |
|---|---|---|
| **EVENTOS** | Gmail `subject:evento` + IG link | Flyer 10×14cm, Rider A4, Cartelera 9:16 |
| **SUPLEMENTOS** | WhatsApp/correo | Etiqueta 16.5×6.5cm, Flyer A5, Pendón, Logo |

## COMANDOS BÁSICOS

```bash
py -m flujo version          # Ver versión
py -m flujo health           # Diagnóstico
py -m flujo app              # Iniciar hub (OBLIGATORIO diario)
py -m flujo job new "..."    # Crear job
py -m flujo datadrop scan    # Procesar fotos terminadas
py -m flujo privacy scan     # Antes de mandar a IAs
```

## HERRAMIENTAS HTML CRÍTICAS

⚠️ **NO TOQUES SIN LEER COMPLETO:**

- `context/plano_demo.html` = RIDER RD EVENTOS (documento operativo)
  - Lee: `docs/RIDER_EVENTOS.md` + `Propuesta_Reduciendo_Dano.txt`
  
- `context/svg_visualizer.html` = Visor SUPLEMENTOS (galería diseños)
  - Lee: `BRIEF_SUPLEMENTOS_RD.md` + `CATALOGO_FORMATOS.md`

**LEE `docs/AGENT_GUARDRAILS_VISUAL_TOOLS.md` (5-question rule).**

## ENTREGAS

Haces un **ZIP con `_airdrop/`** (NO push directo):

```
_airdrop/
  ├── HANDOFF_vX.Y.Z.md
  ├── cambios en rutas reales
  └── tests si es lógica nueva

Validación:
  py scripts/validate_airdrop.py
  py scripts/run_airdrop_checks.py "vX.Y.Z - desc"
```

## ERRORES FRECUENTES = NO LOS REPITAS

❌ Modificar `plano_demo.html` o `svg_visualizer.html` sin entender propósito  
❌ Cambiar colores/referencia sin doc  
❌ Hacer push sin pasar pruebas navegador  
❌ Ignorar HANDOFF/LAST_HANDOFF  
❌ Usar `python` en lugar de `py` (Windows)  

## REGLA DE ORO

**SI NO ENTIENDES POR QUÉ ALGO EXISTE, NO LO TOQUES.**

Lee primero. Pregunta después. Modifica por último.

---

**Próximo paso:** Lee `context/LAST_HANDOFF.md` (estado actual)
