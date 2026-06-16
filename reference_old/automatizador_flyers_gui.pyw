# -*- coding: utf-8 -*-
r"""
AUTOMATIZADOR DE FLYERS - versión con interfaz

Mantiene tus rutas originales:
- C:\rd\AUTOMATIZACION
- Droplet_Flyer.exe
- historia.psd
- input_ig.jpg

Qué agrega:
1) Interfaz gráfica para abrir con doble click (.pyw, sin consola).
2) Opción descargar desde Instagram y continuar al droplet.
3) Opción usar una imagen descargada manualmente y continuar.
4) Opción solo preparar input_ig.jpg sin abrir Photoshop/droplet.
5) Exporta 2 imágenes de color dominante para referencia de armonía.
6) Botones de búsqueda rápida en Google/Instagram para productoras/eventos.

Dependencias:
    pip install -r requirements.txt

Para doble click:
- Guarda este archivo como .pyw.
- Si Windows tiene Python asociado a .pyw, doble click lo abre sin CMD.
- Si prefieres .exe: ejecuta crear_exe.bat
"""

import glob
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Checkbutton, Entry, Frame, IntVar, Label, LabelFrame, StringVar, Tk, filedialog, messagebox, ttk

# Lazy loading para módulos opcionales
instaloader = None
Image = None
ImageDraw = None

def _load_instaloader():
    global instaloader
    try:
        import instaloader as ig
        instaloader = ig
    except ImportError:
        pass

def _load_pil():
    global Image, ImageDraw
    try:
        from PIL import Image as PILImage, ImageDraw as PILImageDraw
        Image = PILImage
        ImageDraw = PILImageDraw
    except ImportError:
        pass

# Configurar logging
LOG_FILE = os.path.join(os.path.expanduser("~"), ".automatizador_flyers.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


# --- RUTAS DE TU CARPETA ---
CARPETA_BASE = r"C:\rd\AUTOMATIZACION"
RUTA_DROPLET = os.path.join(CARPETA_BASE, "Droplet_Flyer.exe")
ARCHIVO_PSD = os.path.join(CARPETA_BASE, "historia.psd")
ARCHIVO_INPUT = os.path.join(CARPETA_BASE, "input_ig.jpg")
# ---------------------------

# Archivos nuevos que se exportan con colores predominantes.
COLOR_1 = os.path.join(CARPETA_BASE, "color_predominante_1.png")
COLOR_2 = os.path.join(CARPETA_BASE, "color_predominante_2.png")

# Carpeta temporal dentro de tu carpeta base.
TEMP_FLYER = os.path.join(CARPETA_BASE, "temp_flyer")

# Si más adelante quieres abrir un .blend exacto, pon aquí la ruta.
# Por ahora el botón "Abrir Blender/proyecto" intenta abrir el primer .blend que encuentre en CARPETA_BASE.
RUTA_BLEND_OPCIONAL = ""


class App:
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self, root):
        self.root = root
        self.root.title("Automatizador de Flyers")
        self.root.geometry("760x720")
        self.root.minsize(700, 650)

        self.url_var = StringVar()
        self.manual_img_var = StringVar()
        self.productora_var = StringVar()
        self.abrir_droplet_var = IntVar(value=1)
        self.limpiar_temp_var = IntVar(value=1)
        self.processing = False

        self._build_ui()
        self.validar_rutas_inicio()

        logging.info("Aplicación iniciada")

    def _build_ui(self):
        main = Frame(self.root, padx=14, pady=12)
        main.pack(fill=BOTH, expand=True)

        titulo = Label(main, text="AUTOMATIZADOR DE FLYERS", font=("Segoe UI", 18, "bold"))
        titulo.pack(anchor="w")

        subtitulo = Label(
            main,
            text="Descarga/prepara el flyer, genera colores de referencia y abre tu droplet de Photoshop.",
            font=("Segoe UI", 10),
        )
        subtitulo.pack(anchor="w", pady=(0, 10))

        # Instagram
        box_ig = LabelFrame(main, text="1) Descargar desde Instagram", padx=10, pady=10)
        box_ig.pack(fill=X, pady=7)

        Label(box_ig, text="Link del post/reel:").pack(anchor="w")
        row_url = Frame(box_ig)
        row_url.pack(fill=X, pady=(3, 8))
        Entry(row_url, textvariable=self.url_var).pack(side=LEFT, fill=X, expand=True)
        Button(row_url, text="Pegar", width=10, command=self.pegar_url).pack(side=RIGHT, padx=(8, 0))

        row_ig_buttons = Frame(box_ig)
        row_ig_buttons.pack(fill=X)
        Button(row_ig_buttons, text="Descargar + preparar + abrir droplet", command=self.descargar_y_procesar_thread).pack(side=LEFT, padx=(0, 8))
        Button(row_ig_buttons, text="Solo descargar/preparar input", command=lambda: self.descargar_y_procesar_thread(abrir_droplet=False)).pack(side=LEFT)

        # Manual
        box_manual = LabelFrame(main, text="2) Si el flyer lo descargaste a mano / es privado / pide sesión", padx=10, pady=10)
        box_manual.pack(fill=X, pady=7)

        Label(box_manual, text="Imagen manual:").pack(anchor="w")
        row_manual = Frame(box_manual)
        row_manual.pack(fill=X, pady=(3, 8))
        Entry(row_manual, textvariable=self.manual_img_var).pack(side=LEFT, fill=X, expand=True)
        Button(row_manual, text="Elegir imagen", command=self.elegir_imagen).pack(side=RIGHT, padx=(8, 0))

        row_manual_buttons = Frame(box_manual)
        row_manual_buttons.pack(fill=X)
        Button(row_manual_buttons, text="Usar imagen manual + abrir droplet", command=self.manual_y_procesar_thread).pack(side=LEFT, padx=(0, 8))
        Button(row_manual_buttons, text="Solo preparar input", command=lambda: self.manual_y_procesar_thread(abrir_droplet=False)).pack(side=LEFT)

        # Opciones
        box_opts = LabelFrame(main, text="3) Opciones", padx=10, pady=10)
        box_opts.pack(fill=X, pady=7)
        Checkbutton(box_opts, text="Abrir droplet/Photoshop al terminar", variable=self.abrir_droplet_var).pack(anchor="w")
        Checkbutton(box_opts, text="Limpiar carpeta temporal al terminar", variable=self.limpiar_temp_var).pack(anchor="w")

        row_ops = Frame(box_opts)
        row_ops.pack(fill=X, pady=(8, 0))
        Button(row_ops, text="Abrir carpeta base", command=self.abrir_carpeta_base).pack(side=LEFT, padx=(0, 8))
        Button(row_ops, text="Abrir input_ig.jpg", command=lambda: self.abrir_archivo(ARCHIVO_INPUT)).pack(side=LEFT, padx=(0, 8))
        Button(row_ops, text="Abrir Blender/proyecto", command=self.abrir_blender_o_proyecto).pack(side=LEFT)

        # Búsqueda productora
        box_busqueda = LabelFrame(main, text="4) Búsqueda rápida de productora / próximos eventos", padx=10, pady=10)
        box_busqueda.pack(fill=X, pady=7)

        Label(box_busqueda, text="Nombre o @ de productora:").pack(anchor="w")
        row_prod = Frame(box_busqueda)
        row_prod.pack(fill=X, pady=(3, 8))
        Entry(row_prod, textvariable=self.productora_var).pack(side=LEFT, fill=X, expand=True)
        Button(row_prod, text="Google eventos", command=self.buscar_google_eventos).pack(side=LEFT, padx=(8, 0))
        Button(row_prod, text="Instagram", command=self.buscar_instagram).pack(side=LEFT, padx=(8, 0))

        Label(
            box_busqueda,
            text="Nota: esto no intenta saltarse login ni privacidad; abre búsquedas para confirmar eventos y evitar confusiones.",
            foreground="#555",
        ).pack(anchor="w")

        # Estado / Log
        box_log = LabelFrame(main, text="Estado", padx=10, pady=10)
        box_log.pack(fill=BOTH, expand=True, pady=7)

        self.progress = ttk.Progressbar(box_log, mode="indeterminate")
        self.progress.pack(fill=X, pady=(0, 8))

        self.log = ttk.Treeview(box_log, columns=("mensaje",), show="headings", height=9)
        self.log.heading("mensaje", text="Registro")
        self.log.column("mensaje", anchor="w", stretch=True)
        self.log.pack(fill=BOTH, expand=True)

        Button(main, text="Salir", command=self.root.destroy).pack(anchor="e", pady=(8, 0))

    def log_msg(self, msg):
        def _insert():
            self.log.insert("", END, values=(msg,))
            self.log.yview_moveto(1)
        self.root.after(0, _insert)
        logging.info(msg)

    def set_busy(self, busy=True):
        def _set():
            if busy:
                self.progress.start(10)
            else:
                self.progress.stop()
        self.root.after(0, _set)

    def validar_rutas_inicio(self):
        if not os.path.isdir(CARPETA_BASE):
            self.log_msg(f"⚠ ADVERTENCIA: no existe CARPETA_BASE: {CARPETA_BASE}")
        else:
            self.log_msg(f"✓ Carpeta base OK: {CARPETA_BASE}")

        rutas_criticas = [
            (RUTA_DROPLET, "Droplet"),
            (ARCHIVO_PSD, "Archivo PSD"),
        ]

        for ruta, nombre in rutas_criticas:
            if not os.path.exists(ruta):
                self.log_msg(f"⚠ ADVERTENCIA: no se encuentra {nombre}: {ruta}")

        _load_instaloader()
        _load_pil()

        if instaloader is None:
            self.log_msg("⚠ ADVERTENCIA: falta instaloader. Instala con: pip install -r requirements.txt")
        if Image is None:
            self.log_msg("⚠ ADVERTENCIA: falta Pillow. Instala con: pip install -r requirements.txt")

    def pegar_url(self):
        try:
            txt = self.root.clipboard_get()
            self.url_var.set(txt.strip())
        except Exception:
            messagebox.showwarning("Portapapeles", "No pude leer el portapapeles.")

    def elegir_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Elegir flyer descargado manualmente",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if ruta:
            self.manual_img_var.set(ruta)

    def preparar_base(self):
        os.makedirs(CARPETA_BASE, exist_ok=True)
        os.chdir(CARPETA_BASE)

    def limpiar_temp(self):
        if self.limpiar_temp_var.get() and os.path.exists(TEMP_FLYER):
            shutil.rmtree(TEMP_FLYER, ignore_errors=True)

    def descargar_y_procesar_thread(self, abrir_droplet=None):
        if self.processing:
            messagebox.showwarning("En progreso", "Ya hay un proceso en ejecución. Espera a que termine.")
            return
        if abrir_droplet is None:
            abrir_droplet = bool(self.abrir_droplet_var.get())
        self.processing = True
        t = threading.Thread(target=self._descargar_y_procesar_safe, args=(abrir_droplet,), daemon=True)
        t.start()

    def manual_y_procesar_thread(self, abrir_droplet=None):
        if self.processing:
            messagebox.showwarning("En progreso", "Ya hay un proceso en ejecución. Espera a que termine.")
            return
        if abrir_droplet is None:
            abrir_droplet = bool(self.abrir_droplet_var.get())
        self.processing = True
        t = threading.Thread(target=self._manual_y_procesar_safe, args=(abrir_droplet,), daemon=True)
        t.start()

    def _descargar_y_procesar_safe(self, abrir_droplet=True):
        try:
            self.descargar_y_procesar(abrir_droplet)
        finally:
            self.processing = False

    def _manual_y_procesar_safe(self, abrir_droplet=True):
        try:
            self.manual_y_procesar(abrir_droplet)
        finally:
            self.processing = False

    def extraer_shortcode(self, url):
        url = (url or "").strip()
        # Acepta /p/, /reel/ y /tv/. También limpia parámetros ?utm=...
        patrones = [r"instagram\.com/(?:[^/]+/)?p/([^/?#]+)", r"instagram\.com/(?:[^/]+/)?reel/([^/?#]+)", r"instagram\.com/(?:[^/]+/)?tv/([^/?#]+)"]
        for patron in patrones:
            m = re.search(patron, url)
            if m:
                return m.group(1)

        # Compatibilidad con tu método original por si el link viene raro.
        for clave in ["/p/", "/reel/", "/tv/"]:
            if clave in url:
                return url.split(clave, 1)[1].split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]

        return None

    def descargar_y_procesar(self, abrir_droplet=True):
        self.set_busy(True)
        try:
            self.preparar_base()

            if instaloader is None:
                raise RuntimeError("Falta instaloader. Instala con: pip install -r requirements.txt")

            url = self.url_var.get().strip()
            shortcode = self.extraer_shortcode(url)
            if not shortcode:
                raise ValueError("Link no válido. Debe ser un link de Instagram tipo /p/, /reel/ o /tv/.")

            if os.path.exists(TEMP_FLYER):
                shutil.rmtree(TEMP_FLYER, ignore_errors=True)
            os.makedirs(TEMP_FLYER, exist_ok=True)

            self.log_msg(f"📥 Descargando flyer desde Instagram. Shortcode: {shortcode}")

            # Reintentos en caso de error de conexión
            ultimo_error = None
            for intento in range(1, self.MAX_RETRIES + 1):
                try:
                    L = instaloader.Instaloader(
                        download_video_thumbnails=False,
                        download_comments=False,
                        save_metadata=False,
                        compress_json=False,
                        post_metadata_txt_pattern="",
                        dirname_pattern=TEMP_FLYER,
                    )

                    post = instaloader.Post.from_shortcode(L.context, shortcode)
                    L.download_post(post, target=TEMP_FLYER)
                    break
                except Exception as e:
                    ultimo_error = e
                    if intento < self.MAX_RETRIES:
                        self.log_msg(f"⚠ Intento {intento}/{self.MAX_RETRIES} falló. Reintentando en {self.RETRY_DELAY}s...")
                        time.sleep(self.RETRY_DELAY)
                    else:
                        raise

            imagen = self.buscar_mejor_imagen(TEMP_FLYER)
            if not imagen:
                raise FileNotFoundError("No se encontró ninguna imagen descargada en temp_flyer.")

            self.log_msg(f"✓ Imagen descargada: {Path(imagen).name}")
            self.preparar_input_y_colores(imagen)

            if abrir_droplet:
                self.abrir_droplet()
            else:
                self.log_msg("✓ Listo: input_ig.jpg preparado. Droplet no abierto.")

            self.limpiar_temp()
            self.log_msg("✓ Proceso terminado.")
            self.root.after(0, lambda: messagebox.showinfo("Éxito", "Flyer descargado y preparado correctamente."))

        except Exception as e:
            error_msg = str(e)
            self.log_msg(f"❌ ERROR: {error_msg}")
            logging.error(f"Error en descargar_y_procesar: {error_msg}", exc_info=True)
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        finally:
            self.set_busy(False)

    def manual_y_procesar(self, abrir_droplet=True):
        self.set_busy(True)
        try:
            self.preparar_base()
            imagen = self.manual_img_var.get().strip().strip('"')
            if not imagen:
                raise ValueError("Elige una imagen manual primero.")
            if not os.path.exists(imagen):
                raise FileNotFoundError(f"No existe la imagen: {imagen}")

            self.log_msg(f"📁 Usando imagen manual: {Path(imagen).name}")
            self.preparar_input_y_colores(imagen)

            if abrir_droplet:
                self.abrir_droplet()
            else:
                self.log_msg("✓ Listo: input_ig.jpg preparado. Droplet no abierto.")

            self.log_msg("✓ Proceso manual terminado.")
            self.root.after(0, lambda: messagebox.showinfo("Éxito", "Imagen manual preparada correctamente."))

        except Exception as e:
            error_msg = str(e)
            self.log_msg(f"❌ ERROR: {error_msg}")
            logging.error(f"Error en manual_y_procesar: {error_msg}", exc_info=True)
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        finally:
            self.set_busy(False)

    def buscar_mejor_imagen(self, carpeta):
        extensiones = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
        archivos = []
        for ext in extensiones:
            archivos.extend(glob.glob(os.path.join(carpeta, ext)))
            archivos.extend(glob.glob(os.path.join(carpeta, "**", ext), recursive=True))

        # Ignora miniaturas de perfil si aparecieran.
        archivos = [a for a in archivos if "profile_pic" not in os.path.basename(a).lower()]
        if not archivos:
            return None

        # Elige la imagen más pesada; suele ser el flyer principal.
        archivos.sort(key=lambda p: os.path.getsize(p), reverse=True)
        return os.path.abspath(archivos[0])

    def preparar_input_y_colores(self, imagen_origen):
        if Image is None:
            raise RuntimeError("Falta Pillow para preparar/exportar colores. Instala con: pip install -r requirements.txt")

        # Convierte a JPG RGB para que input_ig.jpg sea estable aunque la fuente sea PNG/WebP.
        self.log_msg("🖼️ Actualizando input_ig.jpg...")
        try:
            with Image.open(imagen_origen) as im:
                # Verificar que es una imagen válida
                im.verify()

            with Image.open(imagen_origen) as im:
                im = im.convert("RGB")
                im.save(ARCHIVO_INPUT, "JPEG", quality=95)
        except Exception as e:
            raise RuntimeError(f"Error procesando la imagen: {str(e)}")

        self.log_msg("⏳ Dando un respiro al sistema para registrar la imagen...")
        time.sleep(1.5)

        self.exportar_colores_predominantes(ARCHIVO_INPUT)

    def exportar_colores_predominantes(self, ruta_imagen):
        colores = self.obtener_colores_predominantes(ruta_imagen, cantidad=2)
        if not colores:
            self.log_msg("⚠ No se pudieron calcular colores predominantes.")
            return

        if len(colores) == 1:
            colores.append(self.variar_color(colores[0]))

        self.crear_muestra_color(COLOR_1, colores[0])
        self.crear_muestra_color(COLOR_2, colores[1])

        self.log_msg(f"🎨 Color 1: RGB {colores[0]}")
        self.log_msg(f"🎨 Color 2: RGB {colores[1]}")

    def obtener_colores_predominantes(self, ruta_imagen, cantidad=2):
        """
        Extrae colores dominantes evitando que blanco/negro/grises se coman el resultado.
        Si el flyer es muy monocromático, retorna un color y luego se genera una variación.
        """
        with Image.open(ruta_imagen) as im:
            im = im.convert("RGB")
            im.thumbnail((180, 180))

            # Cuantización rápida.
            quant = im.quantize(colors=12, method=Image.Quantize.MEDIANCUT)
            palette = quant.getpalette()
            counts = quant.getcolors()

            candidatos = []
            for count, idx in counts:
                r, g, b = palette[idx * 3: idx * 3 + 3]
                if self.es_color_util(r, g, b):
                    candidatos.append((count, (r, g, b)))

            # Si todo era blanco/negro/gris, permite esos colores como fallback.
            if not candidatos:
                for count, idx in counts:
                    r, g, b = palette[idx * 3: idx * 3 + 3]
                    candidatos.append((count, (r, g, b)))

            candidatos.sort(reverse=True, key=lambda x: x[0])

            elegidos = []
            for _count, color in candidatos:
                if not elegidos:
                    elegidos.append(color)
                    continue
                # Exige diferencia mínima para que no salgan dos casi iguales.
                if all(self.distancia_color(color, c) > 55 for c in elegidos):
                    elegidos.append(color)
                if len(elegidos) >= cantidad:
                    break

            if len(elegidos) == 1 and candidatos:
                variacion = self.variar_color(elegidos[0])
                if self.distancia_color(elegidos[0], variacion) > 10:
                    elegidos.append(variacion)

            return elegidos[:cantidad]

    def es_color_util(self, r, g, b):
        maxc = max(r, g, b)
        minc = min(r, g, b)
        saturacion_aprox = maxc - minc
        brillo = (r + g + b) / 3

        # Evita casi blanco, casi negro y grises muy apagados.
        if brillo > 235:
            return False
        if brillo < 25:
            return False
        if saturacion_aprox < 18:
            return False
        return True

    def distancia_color(self, c1, c2):
        return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5

    def variar_color(self, color):
        r, g, b = color
        # Variación suave: si es oscuro, aclara; si es claro, oscurece y cambia levemente temperatura.
        brillo = (r + g + b) / 3
        if brillo < 130:
            factor = 1.22
            nuevo = (min(255, int(r * factor + 8)), min(255, int(g * factor + 4)), min(255, int(b * factor + 12)))
        else:
            factor = 0.82
            nuevo = (max(0, int(r * factor)), max(0, int(g * factor + 6)), max(0, int(b * factor)))
        return nuevo

    def crear_muestra_color(self, ruta, color):
        w, h = 512, 512
        im = Image.new("RGB", (w, h), color)
        draw = ImageDraw.Draw(im)
        texto = f"RGB {color[0]}, {color[1]}, {color[2]}"

        # Texto contrastado.
        brillo = sum(color) / 3
        txt_color = (0, 0, 0) if brillo > 150 else (255, 255, 255)
        draw.rectangle((0, h - 62, w, h), fill=tuple(max(0, int(c * 0.72)) for c in color))
        draw.text((22, h - 42), texto, fill=txt_color)
        im.save(ruta, "PNG")

    def abrir_droplet(self):
        if not os.path.exists(RUTA_DROPLET):
            raise FileNotFoundError(f"No se encontró el droplet: {RUTA_DROPLET}")
        if not os.path.exists(ARCHIVO_PSD):
            raise FileNotFoundError(f"No se encontró el PSD: {ARCHIVO_PSD}")
        if not os.path.exists(ARCHIVO_INPUT):
            raise FileNotFoundError(f"No se encontró input_ig.jpg: {ARCHIVO_INPUT}")

        self.log_msg("🚀 Abriendo Photoshop/droplet...")

        try:
            cmd = f'start "" "{RUTA_DROPLET}" "{ARCHIVO_PSD}"'
            subprocess.Popen(cmd, shell=True, cwd=CARPETA_BASE)
            self.log_msg("✓ Droplet lanzado.")
        except Exception as e:
            raise RuntimeError(f"No se pudo abrir el droplet: {str(e)}")

    def abrir_carpeta_base(self):
        os.makedirs(CARPETA_BASE, exist_ok=True)
        os.startfile(CARPETA_BASE)

    def abrir_archivo(self, ruta):
        if os.path.exists(ruta):
            os.startfile(ruta)
        else:
            messagebox.showwarning("No encontrado", f"No existe:\n{ruta}")

    def abrir_blender_o_proyecto(self):
        # Si configuraste RUTA_BLEND_OPCIONAL, abre ese.
        if RUTA_BLEND_OPCIONAL and os.path.exists(RUTA_BLEND_OPCIONAL):
            os.startfile(RUTA_BLEND_OPCIONAL)
            self.log_msg(f"📂 Abriendo: {Path(RUTA_BLEND_OPCIONAL).name}")
            return

        # Si no, busca un .blend en CARPETA_BASE.
        blends = glob.glob(os.path.join(CARPETA_BASE, "*.blend"))
        if blends:
            blends.sort(key=os.path.getmtime, reverse=True)
            os.startfile(blends[0])
            self.log_msg(f"📂 Abriendo Blender: {Path(blends[0]).name}")
            return

        # Fallback: abre carpeta base para que elijas tú.
        self.log_msg("ℹ No encontré .blend en carpeta base. Abriendo carpeta base.")
        self.abrir_carpeta_base()

    def buscar_google_eventos(self):
        q = self.productora_var.get().strip()
        if not q:
            messagebox.showwarning("Búsqueda", "Escribe el nombre o @ de la productora.")
            return
        consulta = f'{q} próximos eventos productora flyer Chile OR Santiago'
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(consulta)
        webbrowser.open(url)
        self.log_msg(f"🔍 Google: {q}")

    def buscar_instagram(self):
        q = self.productora_var.get().strip()
        if not q:
            messagebox.showwarning("Búsqueda", "Escribe el nombre o @ de la productora.")
            return
        usuario = q.strip().lstrip("@")
        # Si parece usuario, abre perfil. Si tiene espacios, abre búsqueda web de Instagram.
        if " " not in usuario and usuario:
            url = f"https://www.instagram.com/{urllib.parse.quote(usuario)}/"
        else:
            url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(f"site:instagram.com {q} productora eventos")
        webbrowser.open(url)
        self.log_msg(f"📱 Instagram: {q}")


def main():
    root = Tk()
    # Tema más moderno si está disponible.
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    App(root)
    logging.info("GUI iniciada correctamente")
    root.mainloop()
    logging.info("Aplicación cerrada")


if __name__ == "__main__":
    main()
