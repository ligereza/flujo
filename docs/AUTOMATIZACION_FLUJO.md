# Automatización flujo — revisión sin revisión

Objetivo pedido por el jefe (2026-07-03): automatizar el trabajo del área y
tener al asistente (Cauce) trabajando **sin necesidad de tener el PC
encendido**, con calidad garantizada sin auditorías que expongan errores.

## La analogía: el molde del orfebre

Una auditoría revisa cada copia buscando defectos — y cada defecto encontrado
es un error tuyo expuesto. Un **molde** funciona al revés: se perfecciona UNA
vez, y desde entonces toda copia nace correcta. Nadie inspecciona la copia;
se confía en el molde. La obra de arte no se corrige en la galería.

En flujo, el molde ya existe — esta arquitectura solo lo cierra:

```txt
EL METAL      contenido_suplementos_rd.json + Propuesta_Reduciendo_Dano.txt
              + linea_editorial/v4.1.md  (la verdad, aprobada una vez)
EL MOLDE      generadores de la skill entregas-rd (.claude/skills/entregas-rd/)
              -> toda pieza NACE del JSON maestro, con paleta y margenes
                 correctos por construccion. Los errores no entran.
EL HORNO      validador (flujo suplementos validate) + asserts de desborde
              + CI (.github/workflows/validar-piezas.yml)
              -> lo que sale mal NO PUEDE llegar a main. Nadie lo audita:
                 simplemente no existe en el repo.
LA FIRMA      tu aprobacion del PR desde el telefono. Ese es todo tu trabajo
              manual: firmar la obra.
```

"Revisión sin revisión" = el pipeline es la revisión. Cuando un PR llega a tu
teléfono ya pasó el molde y el horno; apruebas arte terminado, no borradores.

## Las 4 fases (de hoy a cero clicks)

### Fase 0 — lo que YA existe (nada que hacer)

- Gmail → GitHub Issues: correos con asunto "Eventos - ..." / "Suplementos -
  ..." crean issues etiquetados solos (Apps Script, docs/GMAIL_A_REPO_GRATIS.md).
- Generadores deterministas: skill entregas-rd (6 recetas: cotización,
  reversos QR, planos, dark, frentes, vectorizar).
- Validador mecánico + CI de tests (ci.yml) + render manual de piezas
  (render_piezas_vectoriales.yml).

### Fase 1 — el molde en CI (incluida en este cambio)

`.github/workflows/validar-piezas.yml`: cada push/PR que toque `svg/**`
valida TODAS las piezas (crema, dark, vectorizados). Pieza inválida = PR
rojo = no entra. Cero auditorías posteriores.

### Fase 2 — Cauce en la nube (requiere 2 activaciones tuyas)

Con esto el asistente trabaja con tu PC apagado:

1. **Acceso de escritura** para las sesiones web: en claude.ai/code →
   configuración del repositorio → lectura y escritura. (Hoy las sesiones
   remotas son solo-lectura: pueden crear todo pero no pushear — por eso
   los airdrops.)
2. **Claude GitHub Actions**: instalar la app de Claude en el repo (desde
   Claude Code local: `/install-github-app`, o github.com/apps/claude) y
   agregar el secret `ANTHROPIC_API_KEY`. Eso habilita mencionar
   **@claude** en cualquier issue o PR: Claude despierta en un runner de
   GitHub (no en tu PC), lee el issue, carga la skill entregas-rd del repo,
   genera las piezas, y abre un PR que ya viene validado por la Fase 1.

Ciclo resultante:

```txt
correo "Suplementos - etiqueta nueva X"
  -> issue automatico [SUPLEMENTOS] (ya funciona)
  -> comentas "@claude genera la pieza segun la skill entregas-rd"
  -> Claude (en la nube) genera SVG + valida + abre PR
  -> el molde (CI) lo marca verde
  -> apruebas desde el telefono. Fin.
```

### Fase 3 — cero clicks

Cuando la Fase 2 esté probada: el Apps Script de Gmail agrega la línea
"@claude procesa este pedido con la skill entregas-rd" al cuerpo del issue
que ya crea. Desde ese momento el ciclo completo corre solo; tu único punto
de contacto es aprobar el PR (la firma).

Extras opcionales de Fase 3:
- `flujo issue import` (mejora ya anotada en
  docs/FLUJO_AREAS_EVENTOS_SUPLEMENTOS.md) para bajar issues a jobs locales
  cuando trabajas en el PC.
- Un workflow con `schedule:` (cron) que revise issues `estado/por-revisar`
  antiguos y los recuerde/procese cada mañana.

## Qué NO se automatiza (a propósito)

- Precios y tarifas: siempre humanos (regla dura de la skill).
- El logo: nunca se regenera (regla v4.1); solo se compone desde
  assets/logo/.
- La firma final: aprobar el PR es tuyo. El molde garantiza la forma;
  el criterio comercial es del orfebre.

## Requisitos honestos de la Fase 2

- Plan de Anthropic con API key (o suscripción que incluya GitHub Actions).
- Minutos de GitHub Actions (el plan gratis suele alcanzar para este volumen).
- Una prueba guiada: crear un issue de prueba, mencionar @claude y revisar
  el primer PR con calma antes de confiar el ciclo.
