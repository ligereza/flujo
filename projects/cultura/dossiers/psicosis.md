# Dossier: psicosis — how a behavior is studied, and what if the record is wrong

Status: INVESTIGADO (Gemini API 2026-07-10) + spot-check de fuentes (Claude,
WebSearch, 2026-07-10) + curado a herramienta.

HARD LIMIT (binding): this line studies HOW BEHAVIOR IS STUDIED — historiography,
detective method, unreliable records. It never analyzes, diagnoses, or profiles a
real living person. The user-input tool compares READINGS (empathic vs paranoid)
of a situation as an introspective exercise, not a verdict about anyone.

## Research questions (from the rainstorm)
1. Enable user to input an idea/situation -> compare how that BEHAVIOR has been
   STUDIED across lenses (clinical, detective/forensic, historiographic).
2. The detective/historical ANGLE: how a case is reconstructed from traces; the
   epistemics of evidence (Ginzburg's evidential paradigm, the unreliable narrator).
3. What if the HISTORY / INFO is wrong? Reconstruction from corrupt records:
   how historians handle forgery, propaganda, memory error.
4. Merge culture + psychosis: the "collective map of individual projections"
   (plague axis from the original backlog) as a cultural, not clinical, object.

## Gemini web prompt (paste, one block)
```
Investigador de historia de las ideas y epistemologia. Espanol, bullets, CITA
fuente, marca incierto. NO diagnostiques ni perfiles personas; es un estudio de
COMO se estudia la conducta.
1) Como se reconstruye un caso desde indicios: paradigma indiciario de Carlo
   Ginzburg, metodo detective/forense, el narrador no confiable.
2) Como maneja la historia registros corruptos: falsificacion, propaganda, error
   de memoria.
3) La idea de un "mapa colectivo de proyecciones individuales" como objeto
   cultural (no clinico) — antecedentes (histeria colectiva, panicos morales).
<= 30 lineas con fuentes.
```

## Findings

_via Gemini + busqueda, curar antes de usar:_

La investigación de la historia de las ideas y la epistemología aborda la reconstrucción de eventos y la interpretación de la conducta a través de metodologías específicas, reconociendo la complejidad de las fuentes y las narrativas humanas:

*   **Reconstrucción de un caso desde indicios:**
    *   El **paradigma indiciario de Carlo Ginzburg** propone una forma de conocimiento basada en la observación minuciosa de detalles y huellas aparentemente insignificantes para inferir una realidad más amplia. Se asemeja al método de un detective o un médico, donde se conectan pequeños hallazgos para generar conjeturas sobre eventos ocultos. Ginzburg lo vincula con el método de Giovanni Morelli en la historia del arte, el psicoanálisis de Freud y la figura de Sherlock Holmes.
    *   El **método detective/forense** se basa en la lectura de "indicios", es decir, esos pequeños gestos inconscientes, lapsus o detalles que revelan el carácter o una situación que escapa al control consciente.
    *   El **narrador no confiable** es un recurso en el que la credibilidad de quien cuenta la historia está comprometida, ofreciendo información incorrecta, parcial o distorsionada. Esto obliga al lector o historiador a adoptar una postura crítica y a dudar de la objetividad de lo relatado, invitando a una lectura entre líneas.

*   **Manejo histórico de registros corruptos:**
    *   **Falsificación:** La historia lidia con documentos falsos en su contenido o en su forma. Los historiadores investigan los procedimientos y motivos detrás de las falsificaciones (como pleitos legales o justificación de identidades), comparando y contextualizando los registros para discernir la autenticidad y el propósito de la alteración.
    *   **Propaganda:** Entendida como comunicación sesgada para influir en creencias y comportamientos, la propaganda ha existido desde la Antigüedad (Grecia, Roma, movimientos religiosos). Los historiadores la analizan reconociendo sus diversas formas (discursos, arte, medios) y su objetivo de manipular opiniones, lo que requiere un escrutinio crítico de las fuentes.
    *   **Error de memoria:** La memoria es subjetiva, afectiva y susceptible a manipulaciones y deformaciones inconscientes, a diferencia de la historia que busca una reconstrucción crítica y analítica. Los historiadores deben reconocer que la memoria individual y colectiva está influenciada por el presente y puede ser incompleta o sesgada, lo que implica una triangulación con otras fuentes y una conciencia de su naturaleza.

*   **"Mapa colectivo de proyecciones individuales" como objeto cultural:**
    *   Esta idea se relaciona con el **mapeo colectivo**, una metodología participativa para construir conocimiento y relatos compartidos sobre un territorio o cuerpo social. No se limita a un inventario técnico, sino que busca comprender significados y percepciones locales, visibilizando encuentros y consensos sin aplanar diversidades. Es una herramienta para elaborar narraciones que disputan discursos hegemónicos.
    *   **Antecedentes:**
        *   La **histeria colectiva** (o enfermedad sociogénica masiva) son reacciones donde grupos de personas experimentan síntomas físicos o psicológicos sin una causa orgánica clara, a menudo catalizados por el estrés, la ansiedad o la amplificación mediática. Ejemplos incluyen la epidemia de baile de 1518 y los juicios de Salem.
        *   Los **pánicos morales**, concepto desarrollado por Stanley Cohen, describen la reacción social ante la percepción exagerada de una amenaza a los valores o intereses de una comunidad, frecuentemente amplificada por los medios de comunicación y que puede llevar a respuestas desproporcionadas.

## Verificacion de fuentes (spot-check por Claude, WebSearch, 2026-07-10)

Este dossier no trae una lista numerada de URLs como tapiz.md; las afirmaciones
citan autores/conceptos academicos por nombre. El spot-check verifico cada
atribucion nombrada contra busqueda web real:

- **Paradigma indiciario de Ginzburg (vinculo Morelli - Freud - Sherlock
  Holmes)**: [VERIFICADA]. El ensayo de Ginzburg ("Indicios: raices de un
  paradigma indiciario", 1979) efectivamente conecta el metodo de atribucion
  de Giovanni Morelli, el psicoanalisis de Freud y el metodo deductivo de
  Sherlock Holmes/Conan Doyle como una misma forma de conocimiento basada en
  detalles marginales. Confirmado via multiples resumenes academicos y el PDF
  del texto original.
- **Metodo Morelli (orejas, unas como "firma" inconsciente del pintor)**:
  [VERIFICADA]. Confirmado en Britannica/Wikipedia: Morelli (1816-1891)
  atribuia pinturas comparando detalles menores donde el pintor bajaba la
  guardia formal.
- **Stanley Cohen, "moral panic", *Folk Devils and Moral Panics* (1972)**:
  [VERIFICADA]. Libro real, primer texto en definir la teoria social del
  panico moral, basado en su investigacion sobre mods y rockers en Reino
  Unido. Confirmado en Wikipedia/Essex University/tutor2u.
- **Epidemia de baile de 1518 en Estrasburgo como histeria colectiva**:
  [VERIFICADA]. Evento historico real (jul-sep 1518); la teoria dominante hoy
  es histeria colectiva inducida por estres (John Waller). Confirmado en
  Wikipedia/Britannica/National Geographic.
- **Juicios de Salem como histeria colectiva**: [VERIFICADA]. Evento real
  (1692-1693), descrito consistentemente como caso de histeria/panico
  colectivo en fuentes academicas y divulgativas.
- **"Mapeo colectivo" como metodologia participativa territorial**:
  [VERIFICADA]. Metodologia real con referente directo en el colectivo
  argentino Iconoclasistas (Risler y Ares), manual publicado y documentado
  (ArchDaily, biodiversidadla.org, manual propio).

Resultado del spot-check: ninguna atribucion resulto inventada o
no localizable. Se corrige la ADVERTENCIA generica heredada del prompt
Gemini (sin groundingMetadata): en este dossier el riesgo de alucinacion no
se materializo -- los conceptos citados son atribuciones academicas estandar,
verificables por nombre de autor/obra aunque el dossier no incluyera URLs
propias. Tratar como confiable para curar la herramienta.

## Del dossier a la herramienta (curado por Claude desde los findings)

**Pregunta madre**: si el registro de una situacion puede estar corrupto
(memoria, propaganda, relato parcial), como se puede leer esa situacion sin
emitir un veredicto sobre nadie? Respuesta del dossier: no se certifica una
verdad, se comparan LECTURAS -- igual que el historiador frente a una fuente
sospechosa, la herramienta ofrece mas de una interpretacion posible de lo
mismo y deja la conjetura abierta, nunca un diagnostico cerrado.

Mapeo de los findings a un instrumento (spec, no construido en esta sesion):

- **Lente indiciaria/detective** (Ginzburg + Morelli + Holmes) -> modo
  "indicios": la herramienta resalta detalles marginales del texto que el
  usuario ingresa (lo que el propio relato deja escapar sin querer), y arma
  una conjetura EXPLICITAMENTE etiquetada como conjetura, no como hallazgo
  certero.
- **Registro corrupto** (falsificacion / propaganda / error de memoria) ->
  toggle "relato no confiable": la misma situacion se relee dos veces, una
  asumiendo el relato literal y otra asumiendo que esta distorsionado por
  memoria o interes propio de quien narra -- sin acusar a un tercero real de
  mentir, solo mostrando que la lectura cambia segun el supuesto.
- **Panico moral (Cohen) + histeria colectiva (1518, Salem) + mapeo colectivo
  (Iconoclasistas)** -> lente "cultural/colectiva": lee la situacion como
  posible amplificacion de grupo (rumor, presion social, medios), no como
  sintoma de una persona -- coherente con el eje "mapa colectivo de
  proyecciones individuales" del backlog original.

**Fuera de alcance (limite duro, no desarrollar)**: la pregunta de research
original nombraba tambien una "lente clinica" para comparar contra la
detective/historiografica. El prompt real enviado a Gemini la excluyo a
proposito y los findings no la trajeron -- se mantiene excluida aqui. La
herramienta NUNCA debe ofrecer una lectura clinica/diagnostica ni pedir datos
de una persona real identificable; el input es siempre una "situacion"
generica u ficcionalizada, y la salida son lecturas comparadas (empatica vs
paranoica, literal vs no-confiable), nunca un perfil de alguien.

Proxima iteracion del instrumento (no en esta sesion): un modulo chico tipo
`projects/cultura/psicosis/lector_indicios.py` que tome un texto libre y
devuelva 2-3 lecturas estructuradas (indiciaria, no-confiable, colectiva) como
ejercicio introspectivo -- sin storage de inputs reales de terceros. Trabajo
mecanico de armado -> candidato a Qwen/Gemini por el gate; la decision de que
lentes incluir/excluir (este limite duro) queda fija y no se delega.
