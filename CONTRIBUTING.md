# Cómo contribuir a flujo

Este es un repo personal de organización creativa. Si quieres proponer cambios:

1. Abre un issue o envía un mensaje describiendo el cambio.
2. Si es aceptado, crea un airdrop en `_airdrop/` o un PR.
3. Asegúrate de que pasen los checks:
   - `py scripts/flujo_health.py`
   - `py -m pytest tests/ -q`
4. Guarda un checkpoint con `bash scripts/checkpoint.sh "mensaje"`.

## Reglas

- Avanzar paso a paso.
- No subir archivos pesados.
- No automatizar Photoshop/Blender sin acuerdo.
- No borrar sin confirmación.
- Usar `py` en Windows y `python3` en Linux/macOS.
- Después de cada mejora, hacer checkpoint.
