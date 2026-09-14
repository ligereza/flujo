# Grafo relacional inicial de Reduciendo Daño

Fecha: 11 de agosto de 2026
Fuente base: `rd_universo_entidades_2026-08-11.json`
Estado: candidato, pendiente de revisión humana y sanitaria especializada

## Qué se construyó

Se creó un grafo separado de la tabla. La tabla puede mostrar una relación; el grafo conserva de dónde salió, qué tipo de vínculo es, qué tan firme parece, qué prueba lo acompaña y qué límite tiene.

Estado actual: 52 relaciones candidatas, 40 entidades conectadas y 8 entidades que permanecen sin relación documentada en esta tanda.

La unidad ya no es sólo “sustancia + color”. Ahora puede ser:

- una sustancia frente a otra;
- una comparación editorial, como MDMA frente a MDA;
- una interacción contextual, como GHB/GBL con alcohol;
- un nombre comercial o mezcla variable, como tusi;
- un adulterante o contaminante posible;
- un reactivo conectado a una sustancia;
- una limitación de la prueba, como el caso de sustancias que requieren tiras específicas;
- una relación de familia, sin convertir la familia en identidad de la muestra.

## Relaciones prioritarias

### 1. Comparaciones que pueden convertirse en posts

**MDMA ↔ MDA** es la relación más clara para un post comparativo pendiente. El grafo la conecta con Marquis, Simon’s, Robadope y Froehde, pero no la reduce a un color único. La idea visual puede mostrar dos trayectorias que comparten una entrada y se separan mediante señales de varios reactivos.

**Cocaína ↔ ketamina** puede funcionar como comparación de narrativas de testeo porque ambas aparecen asociadas al reactivo de Morris en contenidos distintos. No significa que el reactivo sea una identificación universal.

### 2. Relaciones de interacción

**GHB/GBL ↔ alcohol** y **GHB/GBL ↔ ketamina** deben mantenerse como relaciones de contexto de reducción de daños. No deben transformarse automáticamente en consejos clínicos, instrucciones de dosis ni predicciones individuales.

**Poppers ↔ medicamentos para la disfunción eréctil** necesita una capa especial: el sistema puede marcar la relación, pero el texto público debe conservar un límite de información general y derivación profesional.

### 3. Mezclas y nombres de mercado

El caso **tusi** es decisivo para el diseño. El grafo no dice “tusi = ketamina”, “tusi = MDMA” ni “tusi = cocaína”. Conserva tres vínculos contextuales y una advertencia: el nombre refiere a una mezcla variable. La interfaz debería cambiar de una celda binaria a una celda con estado, evidencia y advertencia visible.

### 4. Adulterantes y contaminantes

Se incorporaron como candidatos separados: PMA y PMMA respecto de MDMA; levamisol y lidocaína respecto de cocaína; fenacetina respecto de metanfetamina; fentanilo respecto de cocaína; y xilacina como posible contexto de contaminación.

Estos vínculos no significan que toda muestra contenga el adulterante. El sistema debe usar lenguaje de posibilidad o contexto documentado, nunca de inevitabilidad.

### 5. Reactivos y límites

Se conectaron inicialmente Ehrlich, Marquis, Simon’s, Robadope y Morris. También se agregaron relaciones de límite para el método colorimétrico frente a GHB/GBL, fentanilo y xilacina.

La diferencia técnica importante es esta: un reactivo colorimétrico presumitivo, una tira específica y un análisis de laboratorio no son el mismo tipo de evidencia. Las guías de DanceSafe y NUAA también presentan los reactivos como herramientas de cribado con límites, no como certificación de composición, pureza o seguridad. [DanceSafe, instrucciones de reactivos](https://dancesafe.org/wp-content/uploads/2024/05/DS_Instructions_Reagents_v17Spring24.pdf), [NUAA, charts de reactivos](https://testkits.nuaa.org.au/pages/charts)

### 6. Ampliación desde la biblioteca de reactivos

La segunda tanda añadió relaciones explícitas para Cannabis con CBD:THC; benzodiacepinas con tira específica y con Zimmermann como relación conflictiva; anfetamina con Marquis, Simon’s, Robadope y Froehde; 5-MeO-DMT con Ehrlich/Hofmann como candidatos de evidencia insuficiente; harmalas con Hofmann; 2C-B con Marquis y Robadope; DOx como límite de Ehrlich; benzofuranos con Froehde; y opioides/medicamentos específicos con Mecke.

Las entidades DET, 4-HO-xxx, escopolamina, PCP y otras que sólo aparecieron como mención de producto o contexto no fueron conectadas automáticamente. Permanecen en el registro universal.

## Cómo debería leerlo la futura tabla interactiva

La tabla original puede conservar su lenguaje visual, pero cada celda debería abrir una ficha mínima:

1. entidades relacionadas;
2. tipo de relación;
3. fuente;
4. estado de revisión;
5. tipo de evidencia: señal presumible de reactivo, tira específica, laboratorio o contexto;
6. límite de interpretación;
7. research relacionado;
8. post existente o pendiente;
9. producto o test asociado;
10. fecha de revisión.

El color ya no debería ser el dato principal. Puede ser una señal visual, pero el estado textual debe sobrevivir a la señal: `precaución`, `alto riesgo`, `riesgo fatal`, `contexto`, `sin test en alcance`, `requiere tira específica`, `pendiente de revisión`.

## Lo que queda pendiente

- Revisar las 52 relaciones candidatas por calidad de fuente y alcance, sin repetir una revisión si la relación ya está respaldada y bien formulada.
- Reparar y verificar los slugs que puedan estar mal escritos antes de publicar.
- Añadir fuentes sanitarias primarias a cada interacción.
- Completar el resto de reactivos sin crear equivalencias falsas, especialmente para las 8 entidades todavía desconectadas.
- Definir los estados de interfaz para “presencia”, “ausencia” y “límite de prueba”.
- Conectar cada relación con los posts, research y productos de RD.
- Recién después generar una vista navegable: primero el grafo, luego la matriz, luego el carrusel o post.

## Regla semántica central

El grafo no debe decir que una muestra “es” MDMA, cocaína, ketamina o cualquier otra sustancia. Debe decir que una muestra puede contenerla y que el test produjo una señal compatible con su presencia presumible.

El test no permite inferir por sí solo:

- cantidad;
- pureza;
- potencia;
- seguridad;
- ausencia de otras sustancias;
- composición completa de la muestra.

Formulaciones permitidas:

> Resultado compatible con presencia presumible de MDMA.

> La muestra puede contener MDMA; el test no determina cantidad, pureza ni composición completa.

Formulaciones prohibidas:

> La muestra es MDMA.

> El resultado confirma que es MDMA.

Por eso el tipo de relación técnico ya no se llama `test_for`, sino `presumptive_presence_signal_for`. El nombre obliga al sistema a conservar la diferencia entre una señal de testeo y la identidad total de una muestra.

## Decisión de diseño

La matriz no debe ser el origen del significado. Debe ser una lectura parcial del grafo. Así, una sustancia sin celda, sin reactivo o sin post no desaparece: permanece en el universo y puede recibir una relación posterior sin inventar evidencia.

El siguiente paso correcto es una comprobación de fuentes y lenguaje en las relaciones nuevas, seguida de una ficha pública de entidad y de la conexión de cada relación con POST, Research y la tienda. No corresponde otra ronda automática de colores.
