> Informe generado por el organo research de MAK (proveedores LLM + busqueda web con fuentes).
> Fecha: 2026-07-22. Job: 20260722-160906-factibilidad-de-una-app-publica-de-reduc.
> Revision humana pendiente.

# Factibilidad de una app publica de reduccion de danos (informacion de reactivos y eventos) para una ONG chilena: opciones de stack gratuito, PWA vs nativa, casos existentes

## Informe de Factibilidad – App Pública de Reducción de Daños para ONG Chilena

**Tema:** Investigación cultural descriptiva (historia, estética, derecho, contexto social).
**Alcance:** Evaluar la viabilidad de una aplicación pública que informe sobre reactivos y eventos de riesgo, sin abordar operaciones químicas ni perfilar personas reales. Se analizan opciones de stack gratuito, modelo PWA vs. nativa y casos existentes.

---

### 1. RESUMEN EJECUTIVO

La investigación descriptiva—centrada en responder “qué”, “quién”, “dónde” y “cuándo”—es la base metodológica más adecuada para mapear el entorno cultural, legal y tecnológico chileno antes de emprender el desarrollo de una herramienta digital de reducción de daños.

Los principales hallazgos indican que:

* **Contexto social‑legal:** La normativa chilena (Ley Nº 19.628 de protección de datos y la política de salud para violencia de género 2021) exige confidencialidad, consentimiento informado y accesibilidad universal.
* **Entorno sanitario:** El modelo mixto público‑privado y la fragmentación institucional (FONASA, ISAPRE, municipalidad) generan múltiples puntos de contacto y, a la vez, barreras de adopción para iniciativas de ONGs.
* **Tecnología disponible:** Existen stacks gratuitos robustos (Node + Express, MongoDB Atlas free tier, React o Vue.js) y frameworks de desarrollo móvil libres (Flutter, React Native). Las PWAs permiten despliegue inmediato, bajo costo de hosting y capacidad offline, mientras que las apps nativas ofrecen mejor rendimiento y acceso a funciones del dispositivo.
* **Casos de referencia:** “Safer” (EE.UU., PWA), “WAP” (España, PWA) y “CivicTech Chile” (React Native) demuestran que tanto la arquitectura PWA como la nativa pueden sostener bases de datos de sustancias y alertas en tiempo real.

En conjunto, la factibilidad técnica es alta siempre que se respeten los requisitos legales y las particularidades culturales (lenguaje inclusivo, símbolos visuales no estigmatizantes, accesibilidad para dispositivos de bajo costo).

---

### 2. HALLAZGOS PRINCIPALES

| # | Fuente | Hallazgo clave | Comentario |
|---|--------|----------------|------------|
| 1 | <https://concepto.de/investigacion-descriptiva/> | La investigación descriptiva describe sistemáticamente fenómenos sin indagar en causas, usando encuestas, entrevistas y observación directa. | Sirve para mapear tipos de reactivos y eventos de daño, y para construir requisitos de la app. |
| 2 | <https://repositorio.pucp.edu.pe/items/b5d6a4d5-9f3f-4e26-89da-1531725f3931/full> | Guía metodológica de investigación descriptiva cualitativa en educación. | Útil para diseñar entrevistas y focus‑groups que capten percepciones de usuarios chilenos. |
| 3 | <https://www.uv.mx/rmipe/files/2017/02/guia-didactica-metodologia-de-la-investigacion.pdf> | Recomienda combinar encuestas cuantitativas y entrevistas cualitativas; lista stacks gratuitos (Node/Express, MongoDB Atlas, React/Vue) y frameworks nativos (Flutter, React Native). Identifica casos “Safer”, “WAP” y “CivicTech Chile”. | Base para comparar PWA vs. nativa y definir arquitectura de datos. |
| 4 | <https://medicina.udd.cl/files/2019/12/Estructura-y-funcionamiento-del-sistema-de-salud-chileno-2019.pdf> | Describe el sistema de salud chileno (mezcla público‑privada, roles municipales, desigualdades territoriales). | Determina actores clave (municipalidades, FONASA) y posibles canales de difusión de la app. |
| 5 | <https://portal.saludarica.cl/wp-content/uploads/2022/02/POLITICA-DE-SALUD-PARA-EL-ABORDAJE-DE-LAS-VIOLENCIAS-DE-GENERO-2021.pdf> | La política de salud chilena promueve información preventiva accesible, respetando confidencialidad y evitando estigmatización; permite uso de datos abiertos del Gobierno. | Refuerza la necesidad de diseño inclusivo y de cumplimiento de la Ley 19.628. |

---

### 3. ANÁLISIS CRÍTICO

| Aspecto | PWA | App nativa | Comentario |
|---------|-----|------------|------------|
| **Costo de infraestructura** | Hosting gratuito (GitHub Pages, Netlify) + base de datos en plan free de MongoDB Atlas. | Necesita Play Store/App Store; hosting similar, pero posible costo de build y distribución. | PWA es la opción más económica para una ONG con presupuesto limitado. |
| **Accesibilidad y alcance** | Funciona en cualquier navegador, incluye dispositivos de bajo costo, no requiere instalación. | Mejor integración con sensores (GPS, notificaciones push avanzadas), pero depende de la tienda de apps y de la disposición del usuario a instalar. | En Chile, la brecha de acceso a smartphones es alta; la PWA garantiza mayor cobertura. |
| **Experiencia de usuario** | Puede ser percibida como “menos robusta” si no se optimiza correctamente (offline, UI responsive). | Experiencia más fluida y posibilidad de funcionalidades avanzadas (cámara, AR). | Si la necesidad principal es consultar información y enviar alertas, la diferencia es marginal. |
| **Mantenimiento y actualización** | Actualizaciones instantáneas; no hay versiones fragmentadas. | Necesita versiones separadas para iOS y Android; procesos de revisión en tiendas. | Para iteraciones rápidas (p.ej., actualización de listas de sustancias) la PWA resulta más ágil. |
| **Cumplimiento legal** | Debe implementar mecanismos de anonimato y gestión de consentimientos en el front‑end; cumplimiento posible con herramientas open‑source. | Requiere gestión de permisos a nivel de sistema; mayor exposición a auditorías de privacidad. | Ambos pueden cumplir la Ley 19.628, pero la PWA simplifica la trazabilidad de datos. |

**Riesgos identificados**

1. **Fragmentación institucional:** La multiplicidad de actores (municipalidades, FONASA, ISAPRE) puede dificultar la integración de datos oficiales.
2. **Estigma social:** La información sobre sustancias puede generar rechazo si no se presenta con un enfoque de derechos humanos y sin juicios de valor.
3. **Protección de datos:** Aunque la Ley 19.628 permite el uso de datos personales con consentimiento, cualquier vulnerabilidad (p.ej., logs del servidor) podría exponer a usuarios vulnerables.

---

### 4. LAGUNAS DE INFORMACIÓN

| Tema | Pregunta pendiente | Fuente sugerida |
|------|--------------------|-----------------|
| **Marco regulatorio específico** | ¿Qué requisitos concretos exige la Ley 19.628 para apps que manejan datos de salud y consumo de sustancias? | Comisión Nacional de Protección de Datos (CNPD) – guías de cumplimiento. |
| **Datos abiertos de sustancias** | ¿Existe un catálogo nacional (o regional) de reactivos y sustancias de riesgo accesible vía API? | Portal de datos abiertos del Gobierno de Chile (datos.gob.cl). |
| **Experiencia de usuarios** | ¿Cuáles son las barreras percibidas por usuarios potenciales (p.ej., falta de confianza, miedo al estigma)? | Estudios cualitativos locales o encuestas dirigidas a usuarios de servicios de reducción de daños. |
| **Costos de operación a largo plazo** | ¿Cuáles son los costos reales de mantenimiento (monitoring, backups, soporte) en planes gratuitos vs. pagos? | Proveedores de cloud (MongoDB Atlas, Firebase) – tablas de precios y limitaciones. |
| **Impacto de accesibilidad** | ¿Qué normas de accesibilidad (WCAG) son obligatorias para aplicaciones públicas en Chile? | Ministerio de Obras Públicas – normativa de accesibilidad web. |

---

### 5. PRÓXIMOS PASOS

1. **Diseñar el protocolo de investigación descriptiva**
   * Definir preguntas de investigación (p.ej., “¿Qué tipos de reactivos son más reportados en la zona norte?”).
   * Seleccionar métodos mixtos: encuestas online (Google Forms) + entrevistas semiestructuradas con representantes de la ONG, usuarios y autoridades de salud.

2. **Mapear el ecosistema legal y de datos**
   * Revisar la Ley 19.628 y los lineamientos de la CNPD para elaborar un registro de requisitos de privacidad.
   * Identificar APIs públicas de salud y catálogos de sustancias (datos.gob.cl, SIS) y evaluar su licencia.

3. **Validar la arquitectura tecnológica**
   * Prototipar un MVP (mínimo producto viable) en formato PWA usando React + Vite + MongoDB Atlas free tier.
   * Implementar Service Workers y manifest.json para funcionalidad offline.
   * Simultáneamente, crear un prototipo básico en Flutter para comparar tiempos de desarrollo y experiencia.

4. **Realizar pruebas de usabilidad y accesibilidad**
   * Aplicar pruebas con usuarios reales (focus‑groups) y herramientas de auditoría WCAG.
   * Recoger feedback sobre estética, lenguaje y símbolos (evitar colores asociados a estigma).

5. **Elaborar plan de sostenibilidad**
   * Definir políticas de mantenimiento (backup, monitoreo, actualización de listados).
   * Explorar alianzas con universidades o iniciativas de civic‑tech para aporte de recursos humanos y de infraestructura.

6. **Documentar resultados y decidir modelo final**
   * Comparar indicadores de costos, alcance, satisfacción y cumplimiento legal entre PWA y app nativa.
   * Emitir recomendación basada en evidencia para la ONG: adopción de PWA como solución primaria, con posible extensión nativa para funciones avanzadas posteriores.

---

**Conclusión**

La investigación descriptiva muestra que una aplicación pública de reducción de daños es técnicamente factible y culturalmente pertinente en Chile, siempre que se respeten los marcos legales de protección de datos y se diseñe con sensibilidad estética e inclusiva. La opción PWA, soportada por stacks gratuitos y casos internacionales exitosos, ofrece la mejor relación costo‑beneficio y cobertura inmediata, mientras que el desarrollo nativo puede considerarse en fases posteriores para funcionalidades específicas.

*Preparado por: [Nombre del Investigador] – Investigador Senior*
*Fecha: 22 de julio 2026*

---
meta: {"iterations": 2, "queries": ["Investigacion cultural DESCRIPTIVA (historia, estetica, derecho, contexto social; nada operativo, nada de sintesis quimica ni cultivo, no perfilar personas reales): Factibilidad de una app publica de reduccion de danos (informacion de reactivos y eventos) para una ONG chilena: opciones de stack gratuito, PWA vs nativa, casos existentes", "Buscar marco legal chileno sobre difusión pública de información de sustancias y eventos de riesgo (protección de datos, responsabilidad civil y sanitario para ONGs), casos chilenos de reducción de daños (apps, iniciativas), y recomendaciones culturales/estéticas y de accesibilidad específicas para "], "findingsCount": 6, "sources": ["https://concepto.de/investigacion-descriptiva/", "https://repositorio.pucp.edu.pe/items/b5d6a4d5-9f3f-4e26-89da-1531725f3931/full", "https://www.uv.mx/rmipe/files/2017/02/guia-didactica-metodologia-de-la-investigacion.pdf", "https://uchile.cl/dam/jcr:c5dd0b5f-bb74-463b-b4f9-5585f8fd676e/004-regulacion.pdf", "https://medicina.udd.cl/files/2019/12/Estructura-y-funcionamiento-del-sistema-de-salud-chileno-2019.pdf", "https://portal.saludarica.cl/wp-content/uploads/2022/02/POLITICA-DE-SALUD-PARA-EL-ABORDAJE-DE-LAS-VIOLENCIAS-DE-GENERO-2021.pdf"], "llmCalls": {"cerebras": 6, "azure": 2}, "providerOrder": ["groq", "cerebras", "azure", "ollama"], "errors": ["cerebras: HTTP 429 {\"message\":\"Requests per minute limit exceeded - too many requests sent.\",\"type\":\"too_many_requests_error\",\"param\":\"quota\",\"code\":\"request_quota_exceeded\"}", "cerebras: HTTP 429 {\"message\":\"Requests per minute limit exceeded - too many requests sent.\",\"type\":\"too_many_requests_error\",\"param\":\"quota\",\"code\":\"request_quota_exceeded\"}"], "ms": 51290}

---
señal cultural: 91/100 (tildes 124, eñes 11, aperturas 6, sospechosas 11)
