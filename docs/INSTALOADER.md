# Descarga Instagram con instaloader

`flujo` usa **exclusivamente instaloader** para descargar posts de Instagram. No yt-dlp.

## Instalación

```
py -m pip install instaloader>=4.10
```

Ya incluido en `requirements.txt`.

## Uso básico

```
py scripts/ig_download.py "https://www.instagram.com/p/SHORTCODE/" ./salida
```

Desde correo (automático):

```
py scripts/flyer_from_email.py "inbox/correo.txt"
```

Reintentar fallidos:

```
py scripts/ig_redownload.py
```

## Qué descarga

- Imágenes JPG del post / carrusel
  - `input_ig.jpg`
  - `input_ig_2.jpg`, `input_ig_3.jpg` ...
- Video MP4 si existe
  - `input_ig_video.mp4`
- Caption
  - `ig_caption.txt`

Manifest guarda:
```
instagram: {
  url, shortcode, type,
  download_status,
  media_type: image | carousel | video | carousel_or_video,
  file_count,
  owner,
  date_utc
}
```

## Limitaciones

- Solo posts públicos.
- Perfiles privados → `login_requerido_o_privado`, descarga manual.
- Rate limit Instagram → `rate_limit`, reintentar más tarde con `ig_redownload.py`
- Reels largos a veces fallan → descarga manual
- No se salta login / 2FA / privacidad. Si pide login, marcar manual.

## Login opcional (no recomendado por defecto)

instaloader puede usar sesión guardada para aumentar límite, pero en `flujo` preferimos no loguearse para evitar bloqueos de cuenta.

Si realmente necesitas login:

```python
L = instaloader.Instaloader(...)
L.load_session_from_file("tu_usuario")
```

No incluido en el script base para mantener portabilidad.

## Errores comunes

| error | significado | acción |
|---|---|---|
| `login_requerido_o_privado` | Post privado o IG pide login | Descarga manual |
| `post_no_encontrado` | Shortcode inválido / borrado | Revisar URL |
| `rate_limit` | Demasiadas requests | Esperar 1h, reintentar con `ig_redownload.py` |
| `sin_archivos` | Post sin media descargable | Manual |
| `instaloader_no_instalado` | Falta dependencia | `py -m pip install instaloader` |

## Buenas prácticas

- No descargar 20 posts seguidos rápido → riesgo rate limit. Espaciar 5-10s (flyer_from_email ya lo hace secuencial).
- Si falla un post, queda marcado en manifest, puedes reintentar después.
- Guarda siempre `ig_caption.txt`, útil para extraer fecha/lugar/productora.
- Los archivos descargados están en `.gitignore`, no se suben al repo.

## ¿Por qué solo instaloader y no yt-dlp?

- yt-dlp instala ~15 dependencias + ffmpeg, ~400 MB entorno.
- instaloader es puro Python, ~5 MB, estable para IG.
- En flujo buscamos ligereza. "Dimensiones del Orden" = menos basura, más control.
- Si un post no baja con instaloader, mejor marcar manual que instalar un monstruo.

## Scripts relacionados

- `scripts/ig_download.py` – descarga individual
- `scripts/flyer_from_email.py` – extrae links y descarga batch
- `scripts/ig_redownload.py` – reintenta fallidos
- `scripts/flyer_status.py` – ver estado + archivos IG
