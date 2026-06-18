# 🤖 Contexto para IA (Handover Document)

**Estado del Proyecto:** flujo v0.25.0
**Fecha de última actualización:** 2026-06-18

## 👉 Empieza por aquí
Lee **`README.md`** completo, especialmente la sección "Cómo trabaja otra IA
aquí" y "El sistema de Airdrops". Es la guía definitiva de cómo colaborar.

## 🛠️ Cambios recientes
- **v0.25.0:** README reescrito como guía maestra para agentes. Nueva
  especificación de **intake por JSON** para colegas (`docs/INTAKE_JSON.md` +
  `schemas/intake.schema.json` + ejemplos en `schemas/ejemplos/`).
- **v0.24.1:** fix de rutas del airdrop en Windows (`rel.as_posix()`).
- **v0.24.0:** reparados los comandos `flujo airdrop` (estaban rotos por
  desincronización cli.py↔airdrop.py) + versión centralizada.

## 🔑 Cómo entregas tu trabajo (resumen)
NO tienes push. Entregas un **ZIP** con una carpeta `_airdrop/` que replica la
estructura del repo (sin subcarpetas de versión). Incluye SIEMPRE un handoff
(`HANDOFF_<fecha>.md`), actualiza la doc, y bumpea versión en `version.py` +
`pyproject.toml`. El dueño aplica con `flujo airdrop apply "msg"` o
`bash scripts/apply_airdrop.sh --apply` + `bash scripts/checkpoint.sh "msg"`.

## ⚠️ Reglas innegociables
1. **Instagram:** solo `instaloader`. Prohibido `yt-dlp`.
2. **Entorno:** sin venvs pesados; usar `py` / `python3`.
3. **Privacidad:** `flujo privacy` antes de mandar datos a IAs externas.
4. **Checkpoints:** cada avance commiteado y pusheado, sin mensajes vacíos.
5. **Borrado:** solo con `scripts/cleanup_safe.sh` (reversible).

## 🗺️ Pipeline actual
Pedido (correo / JSON) → Privacy Scan → Brief → Job → Proyecto (config.json +
plantilla de formato) → Render → Export ZIP.

## 🚧 Trabajo en curso / próximos pasos
1. **Implementar `flujo intake json <archivo>`** que consuma el esquema 1.0
   (ver roadmap en `docs/INTAKE_JSON.md`). Hoy la estructura está definida y
   validada, pero el comando que la procesa end-to-end aún no existe.
2. **Recepción automática** (poller IMAP de correo o formulario web) para que
   los pedidos lleguen y se acuse recibo sin el dueño presente. Decisión de
   canal pendiente del dueño; el contrato JSON ya está fijado.
3. Deuda técnica heredada: patrón PII de "tarjeta" demasiado amplio; `serve()`
   depende de `scripts/app.py` legacy (migrar a `src/flujo/web/`); cache de
   `repo_root()`.
