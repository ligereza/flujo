# Airdrop - flujo

Airdrop es el mecanismo oficial para recibir cambios de agentes externos sin darles push directo.

## Regla unica

El ZIP debe contener `_airdrop/` como carpeta superior. Dentro van archivos reales copiables a sus rutas finales.

```txt
_airdrop/HANDOFF_2026-06-30_cambio.md
_airdrop/context/LAST_HANDOFF.md
_airdrop/src/flujo/archivo.py
_airdrop/tests/test_archivo.py
```

No usar `airdrop/`. No anidar `_airdrop/_airdrop/`. No enviar archivos sueltos fuera de `_airdrop/`.

## Aplicar un airdrop

En Windows/Git Bash:

```bash
cd /c/IA/flujo
rm -rf _airdrop
unzip /ruta/al/paquete.zip
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "mensaje corto"
```

Si el runner ya aplico pero fallo en checks posteriores:

```bash
py scripts/run_airdrop_checks.py --resume "mensaje corto"
```

## Verificacion manual util

```bash
py -m compileall src/flujo
py -m pytest tests/ -q
py -m flujo verify
```

Para web:

```bash
cd web
npm run typecheck
npm run build:context
cd ..
```

## Limpieza local

```bash
rm -rf _airdrop
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
rm -rf .pytest_cache
git status --short
```

## Archivos prohibidos en airdrops

```txt
__pycache__/
.pytest_cache/
node_modules/
dist/
build/
_airdrop_backups/
_logs/
*.zip
*.db
credenciales
archivos pesados reales
```
