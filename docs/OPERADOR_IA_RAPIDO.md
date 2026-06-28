# Operador IA rápido · flujo v0.16

## Si el usuario pega un correo

```bash
flujo job new "nombre pedido" --email inbox/correo.txt
flujo job prepare jobs/<job>
flujo job next
```

## Si el job está listo

```bash
flujo job activate jobs/<job>
flujo render run projects/piezas_vectoriales/<proyecto>/config.json
flujo render validate projects/piezas_vectoriales/<proyecto>/config.json
```

## Si faltan datos

```bash
flujo brief show jobs/<job>/brief.yaml
# editar brief.yaml manualmente
flujo job prepare jobs/<job>    # re-extraer
```

## Si el correo tiene links IG

```bash
flujo flyer-import inbox/correo.txt
flujo analyze
flujo export projects/flyer_eventos/<proj>
```

## Privacidad antes de IA externa

```bash
flujo privacy scan inbox/correo.txt
flujo privacy sanitize inbox/correo.txt --out inbox/correo_san.txt
```

## Antes de commit

```bash
flujo clean
flujo health
flujo version
```

## Cheat sheet

| Acción | Comando |
|--------|---------|
| Crear job | `flujo job new X --email F` |
| Preparar job | `flujo job prepare jobs/X` |
| Ver estado | `flujo job status jobs/X` |
| Activar | `flujo job activate jobs/X` |
| Renderizar | `flujo render run cfg.json` |
| Validar config | `flujo render validate cfg.json` |
| Sugerir formato | `flujo render formats -w W -h H` |
| Dashboard | `flujo daily` |
| Sanitizar | `flujo privacy sanitize F` |
| Web UI | `flujo serve` |
