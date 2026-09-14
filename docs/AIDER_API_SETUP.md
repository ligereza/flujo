# Aider API setup - flujo

Aider como orquestador API del repo: **architect = Claude** (planifica), **editor = modelo barato**
(Qwen / NVIDIA NIM / OpenRouter) aplica el diff. Todo por variables de entorno; **nunca** claves en el repo.

Aider usa litellm, asi que los modelos se nombran con prefijo de proveedor.

## 1. Instalar y claves

```bash
py -m pip install aider-install && aider-install   # o: pipx install aider-chat
cp .env.example .env        # rellena tus claves reales en .env (gitignored)
cp .aider.conf.example.yml .aider.conf.yml         # elige un perfil (gitignored)
```

Variables (ver `.env.example`): `ANTHROPIC_API_KEY`, `DASHSCOPE_API_KEY` (Qwen),
`NVIDIA_API_KEY` (NIM), `OPENROUTER_API_KEY`.

## 2. Nombres de modelo (litellm)

| Proveedor | Ejemplo de --model | Env var | Notas |
|---|---|---|---|
| Claude (architect) | `anthropic/claude-opus-4-8` | ANTHROPIC_API_KEY | usar como architect/reviewer |
| Qwen DashScope | `dashscope/qwen-max` o `dashscope/qwen2.5-coder-32b-instruct` | DASHSCOPE_API_KEY | editor barato |
| NVIDIA NIM | `nvidia_nim/qwen/qwen2.5-coder-32b-instruct` | NVIDIA_API_KEY | tambien deepseek/nemotron |
| OpenRouter | `openrouter/qwen/qwen-2.5-coder-32b-instruct` | OPENROUTER_API_KEY | fallback/router |

Los ids exactos dependen de tu cuenta; ajusta el sufijo si el proveedor renombra el modelo.

## 3. Uso (architect + editor barato)

```bash
# Claude planifica, Qwen edita (modo architect)
aider --architect --model anthropic/claude-opus-4-8 \
      --editor-model dashscope/qwen2.5-coder-32b-instruct \
      src/flujo/algo.py tests/test_algo.py

# Con .aider.conf.yml ya configurado, basta:
aider src/flujo/algo.py

# Editor alternativo NVIDIA NIM
aider --architect --model anthropic/claude-opus-4-8 \
      --editor-model nvidia_nim/qwen/qwen2.5-coder-32b-instruct src/flujo/algo.py

# Barato puro (sin Claude), para tareas mecanicas
aider --model dashscope/qwen2.5-coder-32b-instruct src/flujo/algo.py

# Fallback por OpenRouter
aider --model openrouter/qwen/qwen-2.5-coder-32b-instruct src/flujo/algo.py
```

## 4. Reglas en este repo

- Da a Aider **solo los archivos de la tarea** (menos contexto = mas barato y preciso).
  Primero `py tools/vibo_voz/contexto_repo.py task "<keywords>"` para saber cuales.
- Deja que **Claude (architect) valide el plan** antes de que el editor barato aplique.
- **Revisa el diff** antes de commitear (Claude para lo critico). Ver CLAUDE.md (bloque "Equipo multi-agente").
- Verifica siempre: `py -m compileall src/flujo && py -m pytest tests/ -q && py -m flujo verify`.
  Si tocaste web: `cd web && npm run build:context && cd ..`.
- Cierra la sesion actualizando `context/LAST_HANDOFF.md` + `context/SESSION_STATE.json`.
- Aider commitea solo; NO pushear a `main` directo (usar rama + PR).

`.aider.conf.yml`, `.aider.chat.history.md` y `.aider.input.history` estan gitignored:
no versiones tu config con claves ni el historial de chat.
