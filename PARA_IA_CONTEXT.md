# 🤖 Contexto para IA (Handover Document)

**Estado del Proyecto:** flujo v0.20.0
**Fecha de última actualización:** 2026-06-18

## 🛠️ Cambios Críticos Recientes
Se ha implementado el sistema **Zero-Friction Airdrop**.
- El flujo de actualización ya no es manual (Bash scripts) sino integrado en la CLI.
- Comando maestro: `flujo airdrop apply <versión>`.
- Este comando ahora orquestra: Backup $\rightarrow$ Aplicación $\rightarrow$ Checkpoint $\rightarrow$ Git Push.

## ⚠️ Reglas Innegociables (Constraints)
1. **Instagram:** Descargas ÚNICAMENTE con `instaloader`. Prohibido usar `yt-dlp`.
2. **Entorno:** No crear venvs pesados. Usar el comando `py` o el intérprete del sistema.
3. **Privacidad:** Siempre ejecutar `flujo privacy` antes de enviar datos a IAs externas.
4. **Checkpoints:** Cada avance debe quedar registrado en `/checkpoints` mediante la lógica de `checkpoint.sh`.

## 🗺️ Mapa del Pipeline actual
Intake (Correo/IG) $\rightarrow$ Privacy Scan $\rightarrow$ Brief Extraction $\rightarrow$ Project Creation $\rightarrow$ Vector Render.
