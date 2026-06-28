# Sistema de Airdrop — flujo

El sistema de airdrop permite aplicar actualizaciones rápidas y parches al repositorio sin necesidad de PRs complejos para cada pequeña mejora.

## 🚀 Nueva CLI Integrada

Ahora el sistema de airdrop está integrado directamente en la CLI de `flujo`.

### Comandos Disponibles:

| Comando | Descripción |
| :--- | :--- |
| `flujo airdrop list` | Lista las versiones disponibles en `_airdrop/`. |
| `flujo airdrop dry-run <v>` | Simula los cambios que aplicaría la versión `<v>`. |
| `flujo airdrop apply <v>` | Aplica la versión `<v>` y crea un backup automático. |
| `flujo airdrop rollback` | Revierte al último backup realizado. |
| `flujo airdrop finish` | Muestra el estado de git y pasos finales. |

## 🛠️ Flujo de Trabajo Recomendado

1. **Listar:** `flujo airdrop list`
2. **Simular:** `flujo airdrop dry-run v0.18`
3. **Aplicar:** `flujo airdrop apply v0.18`
4. **Finalizar:** `flujo airdrop finish`

---

**Versión:** Junio 2026 · v0.18 (Enhanced)
