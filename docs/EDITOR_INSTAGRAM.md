# Editor — pestaña Instagram (analizar → descargar → paleta)

Flujo de 3 pasos para arrancar una pieza desde un post de Instagram.

```
1. Analizar          2. Descargar post        3. Aplicar paleta
   (avisos)             (instaloader)            (a la pieza del editor)
   privado/video     imagen + caption          colores → palette del config
   links detectados  + paleta de colores        → preview con esos colores
```

## Cómo se usa

1. Pegá el correo/mensaje **o el link directo** (acepta
   `instagram.com/<usuario>/p/CODE/` y `instagram.com/p/CODE/`, con o sin https).
2. **1. Analizar:** detecta links y avisa si el perfil es privado o la primera
   del carrusel es video (antes de gastar una descarga).
3. **2. Descargar post:** baja la imagen con `instaloader` a
   `projects/flyer_eventos/<slug>/input/`, muestra la imagen y **extrae su paleta
   de 6 colores dominantes**.
4. **3. Aplicar paleta a la pieza:** vuelca esos colores al `palette` del formato
   que tengas cargado en la pestaña EDITOR y refresca el preview.

## Notas

- La descarga usa **solo instaloader** (regla del repo). Si el perfil es privado
  o hay rate-limit (429), lo informa con un mensaje claro y no rompe.
- La extracción de paleta reusa `flujo.analyze.colors.extract_palette` (Pillow,
  sin dependencias nuevas).
- El mapeo de colores a nombres (`accent`, `ink`, `muted`, `line`, `paper`,
  `white`) es por orden de dominancia; podés ajustar los hex luego en el config.
- Esto **no** reemplaza el pipeline `flujo flyer-import` (intake masivo desde
  correo); es el atajo visual para una pieza puntual.

## Para la siguiente IA

Funciones puras en `src/flujo/web/editor.py`:
- `descargar_instagram(texto, slug="") -> (dict, msg, img_path)` — mockeable
  (parchea `flujo.ig.download.download_post`).
- `aplicar_paleta(config, descarga) -> (config, msg)`.

Tests: `tests/test_ig_download_palette.py` (mock de download) y
`tests/test_ig_usuario.py` (regex de URLs).
