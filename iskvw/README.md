# iskvw · la cara visible

El portafolio cambia seguido. Esta carpeta separa fuentes, contrato y pieles:
**cambiar el estilo no significa rehacer el sitio ni reescribir los datos**.

```
  datos/obras.json     catálogo pequeño de herramientas/obras declaradas a mano
  datos/micelio.json   snapshot de relaciones que MAK produjo
  datos/campo.json     posiciones medidas y capas del archivo
  datos/archivo.json   proyección regenerable que consume una piel (no versionada)
  ESQUEMA_ARCHIVO.md   contrato de forma y reglas de la proyección
  cultura/mak_plataforma/contrato_archivo.py  conversión pura compartida
  PROMPT_ESTETICA.md   instrucciones para pedir una piel nueva
  piel/                cada estilo, en su propia carpeta
```

## Para pedir un estilo nuevo

Pasale a un agente —Arena, Google AI Studio, el que sea— estos recursos:

    PROMPT_ESTETICA.md
    cultura/mak_plataforma/contrato_archivo.py
    datos/ESQUEMA.md

Lo que devuelva va a `piel/<nombre>/`. No tiene que tocar `datos/` ni nada más.
Si para que funcione hay que editar el contenido o inventar campos, la
propuesta no cumple el contrato.

## Por qué así

Tres razones, y las tres son del autor:

- **El estilo se reemplaza entero, no se parchea.** Cada piel vive aparte; la
  anterior no se borra.
- **El sitio no puede mentir.** Ningún elemento afirma un dato que no tiene: es
  la regla que gobierna todo este repo.
- **No es un sitio con título y menú.** La interfaz puede ser parte de la obra.
  Está explicado en el contrato.
