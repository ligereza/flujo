# Research Agent n8n -- APIs gratis (multi-proveedor)

Workflow: `cultura/research_agent_free_apis.json`. Reemplaza a
`research_agent_mistral_nemo.json` (v1, NO importable: usaba el nodo
`n8n-nodes-base.llm` que no existe en n8n, y `this.helpers` dentro de
`function` declarations, que crashea en el Code node).

Agente de investigacion autonomo: webhook recibe un tema, bucle
SEARCH (Tavily) -> FETCH -> ANALYZE (LLM) -> DECIDE, y genera informe final
en Markdown. Todo el LLM va por una cadena de fallback de APIs gratis;
Ollama local (MAK) queda como ultimo recurso ilimitado/privado.

## Arquitectura (4 nodos)

```
Webhook POST /research
  -> Config: Variables y Keys   (Set: body override o $env)
  -> Research Loop + Informe    (Code: bucle completo + informe)
  -> Responder Webhook          (firstIncomingItem)
```

Decisiones de diseno vs v1:
- 1 solo Code node hace loop + informe: el nodo LLM inexistente muere.
- `httpRequest` como arrow function: captura el `this` del sandbox
  (las `function` declarations de la v1 dejaban `this` undefined).
- `seenUrls`: dedupe de URLs entre iteraciones (v1 re-bajaba las mismas).
- Ultima iteracion no gasta la llamada DECIDIR.
- `meta` en la respuesta: queries, fuentes, llamadas por proveedor,
  errores no fatales, duracion ms.

## Cadena LLM (probada 2026-07-15, llamadas reales)

| Orden | Proveedor | Modelo default | Estado | Nota |
|---|---|---|---|---|
| 1 | Groq | `llama-3.3-70b-versatile` | OK | Free tier, rapido; tambien `qwen3-32b`, `openai/gpt-oss-120b` |
| 2 | Cerebras | `gpt-oss-120b` | OK | Free tier; catalogo chico y CAMBIA (llama3.1-8b ya no existe); razona -> el code ya suma margen de tokens |
| 3 | Azure Foundry | deployment `gpt-5-mini` | OK | endpoint `https://ligereza.services.ai.azure.com`, api-version 2024-10-21; NO acepta temperature custom; usa `max_completion_tokens` (el code lo maneja) |
| 4 | Ollama (MAK) | `mistral-nemo:latest` | local | Ilimitado/privado pero lento (10-60s/llamada) |

Azure classic `risearch.openai.azure.com`: auth OK pero 0 deployments ->
inutilizable hasta crear un deployment en ese recurso.

Search: Tavily (1000 creditos/mes gratis). `search_depth` default `basic`
(1 credito); `advanced` gasta 2.

## Setup en n8n (MAK)

Variables de entorno del contenedor n8n (docker-compose):

```yaml
services:
  n8n:
    environment:
      - TAVILY_API_KEY=tvly-...
      - GROQ_API_KEY=gsk_...
      - CEREBRAS_API_KEY=csk-...
      - AZURE_API_KEY=...
      - AZURE_ENDPOINT=https://ligereza.services.ai.azure.com
      - AZURE_DEPLOYMENT=gpt-5-mini
      - OLLAMA_BASE_URL=http://ollama:11434
```

Las keys reales viven en `cultura/.dev` (gitignored, NUNCA commitear).
Si `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` estuviera seteado, el `$env` no
funciona: pasar las keys por body del webhook (ver abajo).

Importar: n8n -> Workflows -> Import from File ->
`research_agent_free_apis.json` -> Activate. Sin credenciales de n8n:
todo va por HTTP directo.

## Uso

```bash
curl -X POST http://192.168.50.2:5678/webhook/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "estado del arte timecode OSC para shows en vivo", "max_iterations": 3}'
```

Body (todo opcional salvo `topic`):

| Campo | Default | Nota |
|---|---|---|
| `topic` | (requerido) | tema |
| `max_iterations` | 4 | tope duro 10 |
| `search_depth` | `basic` | `advanced` = 2 creditos Tavily |
| `providers` | `groq,cerebras,azure,ollama` | orden de fallback, CSV |
| `tavily_api_key` / `groq_api_key` / `cerebras_api_key` / `azure_api_key` | `$env.*` | override por request |
| `azure_endpoint` / `azure_deployment` | env o `ligereza`/`gpt-5-mini` | |
| `ollama_base_url` / `ollama_model` | `http://ollama:11434` / `mistral-nemo:latest` | |
| `groq_model` / `cerebras_model` | ver tabla | |

Respuesta: `{topic, report (Markdown), meta {iterations, queries,
findingsCount, sources, llmCalls, providerOrder, errors, ms}, findings}`.

## Verificacion hecha (2026-07-15)

- JSON del workflow valido (`py -m json.tool`); JS del Code node
  `node --check` OK.
- Harness que simula el sandbox n8n (`this.helpers.httpRequest`) corrio el
  code REAL contra APIs reales: 1 iteracion, 4 findings, 3 fuentes,
  informe coherente, 17s, 0 errores (todo Groq).
- Fallback probado: con Groq roto a proposito -> 4x 401 en `meta.errors`,
  Cerebras absorbio las 4 llamadas, informe igual generado (12s).

## Troubleshooting

- `Todos los proveedores LLM fallaron`: revisar `meta.errors` (viene en la
  respuesta) -- trae el error por proveedor recortado.
- Cerebras `model_not_found`: el catalogo free rota; listar con
  `GET https://api.cerebras.ai/v1/models` y pasar `cerebras_model`.
- Azure `DeploymentNotFound`: el deployment se llama `gpt-5-mini`
  (no `gpt-4o-mini`); listar via
  `GET {endpoint}/api/projects/LIGEREZA-project/deployments?api-version=v1`.
- Respuestas vacias de gpt-5-mini / gpt-oss: modelos razonadores; si se
  ajusta el code, mantener el margen extra de `max_completion_tokens`.
- Ollama lento: es el ultimo de la cadena a proposito; subirlo de orden
  solo si se quiere privacidad total (`providers: "ollama"`).
