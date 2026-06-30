# HANDOFF 2026-06-30 - Agent operations base

## Objetivo

Dejar el repo operacional para agentes: lectura clara, handoff obligatorio, airdrop como base de integracion y verificacion sin dudas.

## Cambios incluidos

- `AGENTS.md` reescrito como contrato operativo principal.
- `docs/AGENT_AIRDROP_PROTOCOL.md` simplificado como protocolo unico de airdrop.
- `docs/AIRDROP.md` actualizado para reflejar el flujo real actual: `_airdrop/`, `validate_airdrop.py`, `run_airdrop_checks.py`.
- `context/LAST_HANDOFF.md` actualizado en ASCII-only con estado v0.48.x y reglas operativas.

## Reglas que quedan firmes

- Usuario trabaja en Windows + Git Bash.
- Instrucciones al usuario usan `py`, no `python`.
- Agentes sin push entregan ZIP con `_airdrop/` en raiz.
- Todo airdrop incluye `HANDOFF_*.md` o `HOTFIX_*.md` y `context/LAST_HANDOFF.md`.
- No se aceptan caches, builds, ZIPs, DBs, credenciales ni archivos pesados.
- No declarar OK sin verificacion.

## Comandos de apply

```bash
cd /c/IA/flujo
rm -rf _airdrop
unzip /ruta/al/airdrop_agent_ops_base_20260630.zip
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "agent ops base handoff airdrop"
```

## Verificacion esperada

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "agent ops base handoff airdrop"
py -m flujo verify
```

## Tareas simples para el proximo agente

1. Leer `AGENTS.md` y `context/LAST_HANDOFF.md` antes de editar.
2. Entregar solo por `_airdrop/` si no tiene push directo.
3. Mantener `context/LAST_HANDOFF.md` ASCII-only.
4. Reportar comandos reales ejecutados y resultados.
