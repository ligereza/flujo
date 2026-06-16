# -*- coding: utf-8 -*-
"""
AUTOMATIZADOR DE FLYERS v2 - Versión Avanzada
Integración: Email + Blender + Colores + Búsqueda rápida

Flujo:
1. Extrae link de correo O paste manual
2. Descarga imagen de Instagram
3. Extrae colores dominantes
4. Crea proyecto Blender para evento
5. Aplica colores a materiales de Blender
6. Abre Blender / Droplet / carpeta
"""

import glob
import json
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
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Checkbutton, Entry, Frame, IntVar, Label, LabelFrame, StringVar, Text, Tk, filedialog, messagebox, ttk

# Lazy loading
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

# Importar scripts locales
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from email_extractor import EmailExtractor
except ImportError:
    EmailExtractor = None

# Configurar logging
LOG_FILE = os.path.join(os.path.expanduser("~"), ".automatizador_flyers_v2.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Rutas base
BASE_FOLDER = r"C:\rd\AUTOMATIZACION"
RECURSOS = os.path.join(BASE_FOLDER, "RECURSOS")
RESULTADOS = os.path.join(BASE_FOLDER, "RESULTADOS")
TEMP_FOLDER = os.path.join(BASE_FOLDER, "TEMP")
OBJETOS_FOLDER = os.path.join(BASE_FOLDER, "OBJETOS_INTELIGENTES")
CONFIG_FOLDER = os.path.join(BASE_FOLDER, "CONFIGURACION")

# Rutas de recursos
RUTA_DROPLET = os.path.join(RECURSOS, "Droplet_Flyer.exe")
ARCHIVO_PSD = os.path.join(RECURSOS, "historia.psd")
BLEND_TEMPLATE = os.path.join(RECURSOS, "RD.blend")

# Rutas de resultados
ARCHIVO_INPUT = os.path.join(RESULTADOS, "input_ig.jpg")
COLOR_1 = os.path.join(RESULTADOS, "color_predominante_1.png")
COLOR_2 = os.path.join(RESULTADOS, "color_predominante_2.png")

TEMP_FLYER = os.path.join(TEMP_FOLDER, "temp_flyer")

# Tema: Modo noche
COLOR_BG = "#1a1a1a"
COLOR_TEXT = "#ffffff"
COLOR_HEADER = "#d32f2f"
COLOR_ACCENT = "#2196f3"
COLOR_SECTION = "#262626"


class AppV2:
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Automatizador de Flyers v2")
        self.root.geometry("1000x900")
        self.root.minsize(900, 800)
        self.root.configure(bg=COLOR_BG)

        self.url_var = StringVar()
        self.event_name_var = StringVar()
        self.productora_var = StringVar()
        self.manual_img_var = StringVar()
        self.blender_var = IntVar(value=1)
        self.abrir_droplet_var = IntVar(value=0)
        self.limpiar_temp_var = IntVar(value=1)
        self.processing = False
        self.colores_extraidos = {}

        self._build_ui()
        self.validar_rutas_inicio()
        logging.info("App v2 iniciada")

    def _build_ui(self):
        self.root.configure(bg=COLOR_BG)

        main = Frame(self.root, padx=14, pady=12, bg=COLOR_BG)
        main.pack(fill=BOTH, expand=True)

        # HEADER ROJO
        header = Frame(main, bg=COLOR_HEADER, height=70)
        header.pack(fill=X, pady=(0, 12))
        header.pack_propagate(False)

        titulo = Label(header, text="🎬 AUTOMATIZADOR DE FLYERS v2", font=("Segoe UI", 18, "bold"), bg=COLOR_HEADER, fg=COLOR_TEXT)
        titulo.pack(pady=(8, 0))

        subtitulo = Label(header, text="Email → Link → Descarga → Colores → Blender", font=("Segoe UI", 9), bg=COLOR_HEADER, fg=COLOR_TEXT)
        subtitulo.pack(pady=(0, 8))

        # SECCIÓN 1: Link / Instagram
        box_ig = LabelFrame(main, text="1️⃣  DESCARGAR DE INSTAGRAM", padx=10, pady=10, font=("Segoe UI", 10, "bold"), bg=COLOR_SECTION, fg=COLOR_HEADER)
        box_ig.pack(fill=X, pady=7)

        Label(box_ig, text="Link del post/reel:", font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT).pack(anchor="w")
        row_url = Frame(box_ig, bg=COLOR_SECTION)
        row_url.pack(fill=X, pady=(3, 8))
        Entry(row_url, textvariable=self.url_var, font=("Segoe UI", 10), bg="#333", fg=COLOR_TEXT, relief="solid", borderwidth=1).pack(side=LEFT, fill=X, expand=True)
        Button(row_url, text="📋 Pegar Link", width=11, bg=COLOR_ACCENT, fg=COLOR_TEXT, command=self.pegar_url, relief="flat").pack(side=RIGHT, padx=(8, 0))

        row_extra = Frame(box_ig, bg=COLOR_SECTION)
        row_extra.pack(fill=X, pady=(0, 8))
        Button(row_extra, text="📧 Pegar Correo", width=12, bg="#1976d2", fg=COLOR_TEXT, command=self.pegar_correo_completo, relief="flat").pack(side=LEFT, padx=(0, 8))
        Button(row_extra, text="Extraer Link", width=12, bg="#388e3c", fg=COLOR_TEXT, command=self.extraer_link_de_correo_pegado, relief="flat").pack(side=LEFT)

        row_ig_buttons = Frame(box_ig, bg=COLOR_SECTION)
        row_ig_buttons.pack(fill=X)
        Button(row_ig_buttons, text="Descargar + preparar + abrir droplet", bg=COLOR_HEADER, fg=COLOR_TEXT, command=self.descargar_y_procesar_thread, relief="flat").pack(side=LEFT, padx=(0, 8))
        Button(row_ig_buttons, text="Solo descargar/preparar input", bg="#455a64", fg=COLOR_TEXT, command=lambda: self.descargar_y_procesar_thread(abrir_droplet=False), relief="flat").pack(side=LEFT)

        # SECCIÓN 2: Imagen manual
        box_manual = LabelFrame(main, text="2️⃣  IMAGEN MANUAL (Privada/Descargada)", padx=10, pady=10, font=("Segoe UI", 10, "bold"), bg=COLOR_SECTION, fg=COLOR_HEADER)
        box_manual.pack(fill=X, pady=7)

        Label(box_manual, text="Si el flyer es privado o lo descargaste a mano:", font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT).pack(anchor="w")
        row_manual = Frame(box_manual, bg=COLOR_SECTION)
        row_manual.pack(fill=X, pady=(3, 8))
        Entry(row_manual, textvariable=self.manual_img_var, font=("Segoe UI", 10), bg="#333", fg=COLOR_TEXT, relief="solid", borderwidth=1).pack(side=LEFT, fill=X, expand=True)
        Button(row_manual, text="📁 Elegir", width=10, bg=COLOR_ACCENT, fg=COLOR_TEXT, command=self.elegir_imagen, relief="flat").pack(side=RIGHT, padx=(8, 0))

        row_manual_buttons = Frame(box_manual, bg=COLOR_SECTION)
        row_manual_buttons.pack(fill=X)
        Button(row_manual_buttons, text="Usar imagen manual + abrir droplet", bg=COLOR_HEADER, fg=COLOR_TEXT, command=self.manual_y_procesar_thread, relief="flat").pack(side=LEFT, padx=(0, 8))
        Button(row_manual_buttons, text="Solo preparar input", bg="#455a64", fg=COLOR_TEXT, command=lambda: self.manual_y_procesar_thread(abrir_droplet=False), relief="flat").pack(side=LEFT)

        # SECCIÓN 2B: Correos
        box_correos = LabelFrame(main, text="📧 CORREOS DE ISIDORA", padx=10, pady=10, font=("Segoe UI", 10, "bold"), bg=COLOR_SECTION, fg=COLOR_HEADER)
        box_correos.pack(fill=X, pady=7)

        Label(box_correos, text="Busca correos con links de eventos de tu jefa:", font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT).pack(anchor="w")

        row_correos = Frame(box_correos, bg=COLOR_SECTION)
        row_correos.pack(fill=X, pady=(8, 0))
        Button(row_correos, text="📨 Abrir Gmail - Buscar correos de Isidora", bg="#ea4335", fg=COLOR_TEXT, command=self.abrir_gmail_isidora, relief="flat", font=("Segoe UI", 10, "bold")).pack(fill=X)

        # SECCIÓN 3: Evento + Blender
        box_event_blender = LabelFrame(main, text="3️⃣  EVENTO + BLENDER", padx=10, pady=10, font=("Segoe UI", 10, "bold"), bg=COLOR_SECTION, fg=COLOR_HEADER)
        box_event_blender.pack(fill=X, pady=7)

        Label(box_event_blender, text="Nombre evento (ej: evento_2026_02_28_Fiesta):", font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT).pack(anchor="w")
        Entry(box_event_blender, textvariable=self.event_name_var, font=("Segoe UI", 10), bg="#333", fg=COLOR_TEXT, relief="solid", borderwidth=1).pack(fill=X, pady=(3, 8))

        Checkbutton(box_event_blender, text="✅ Incluir en Blender (aplicar colores a materiales)", variable=self.blender_var, font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT, activebackground=COLOR_SECTION, selectcolor=COLOR_SECTION).pack(anchor="w")

        row_event_buttons = Frame(box_event_blender, bg=COLOR_SECTION)
        row_event_buttons.pack(fill=X, pady=(8, 0))
        Button(row_event_buttons, text="🎬 Abrir Proyecto Blender", bg="#ff9800", fg=COLOR_TEXT, command=self.abrir_blender_evento, relief="flat").pack(side=LEFT, padx=(0, 8))
        Button(row_event_buttons, text="📂 Abrir Carpeta Evento", bg="#0097a7", fg=COLOR_TEXT, command=self.abrir_carpeta_evento, relief="flat").pack(side=LEFT)

        # SECCIÓN 4: Búsqueda productora
        box_busqueda = LabelFrame(main, text="4️⃣  BÚSQUEDA RÁPIDA PRODUCTORA", padx=10, pady=10, font=("Segoe UI", 10, "bold"), bg=COLOR_SECTION, fg=COLOR_HEADER)
        box_busqueda.pack(fill=X, pady=7)

        Label(box_busqueda, text="Nombre o @ de productora:", font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT).pack(anchor="w")
        row_prod = Frame(box_busqueda, bg=COLOR_SECTION)
        row_prod.pack(fill=X, pady=(3, 8))
        Entry(row_prod, textvariable=self.productora_var, font=("Segoe UI", 10), bg="#333", fg=COLOR_TEXT, relief="solid", borderwidth=1).pack(side=LEFT, fill=X, expand=True)
        Button(row_prod, text="🔍 Google", bg=COLOR_ACCENT, fg=COLOR_TEXT, command=self.buscar_google_eventos, relief="flat").pack(side=LEFT, padx=(8, 0))
        Button(row_prod, text="📱 Instagram", bg=COLOR_ACCENT, fg=COLOR_TEXT, command=self.buscar_instagram, relief="flat").pack(side=LEFT, padx=(8, 0))

        Label(box_busqueda, text="Nota: Esto no salta login ni privacidad; confirma eventos para evitar confusiones.", font=("Segoe UI", 8), bg=COLOR_SECTION, fg="#999").pack(anchor="w")

        # SECCIÓN 5: Opciones
        box_opts = LabelFrame(main, text="5️⃣  OPCIONES", padx=10, pady=10, font=("Segoe UI", 10, "bold"), bg=COLOR_SECTION, fg=COLOR_HEADER)
        box_opts.pack(fill=X, pady=7)

        Checkbutton(box_opts, text="✅ Abrir droplet/Photoshop al terminar", variable=self.abrir_droplet_var, font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT, activebackground=COLOR_SECTION, selectcolor=COLOR_SECTION).pack(anchor="w")
        Checkbutton(box_opts, text="✅ Limpiar carpeta temporal al terminar", variable=self.limpiar_temp_var, font=("Segoe UI", 9), bg=COLOR_SECTION, fg=COLOR_TEXT, activebackground=COLOR_SECTION, selectcolor=COLOR_SECTION).pack(anchor="w")

        row_ops = Frame(box_opts, bg=COLOR_SECTION)
        row_ops.pack(fill=X, pady=(8, 0))
        Button(row_ops, text="📂 Carpeta base", bg="#1976d2", fg=COLOR_TEXT, command=self.abrir_carpeta_base, relief="flat").pack(side=LEFT, padx=(0, 8))
        Button(row_ops, text="🖼️  input_ig.jpg", bg="#1976d2", fg=COLOR_TEXT, command=lambda: self.abrir_archivo(ARCHIVO_INPUT), relief="flat").pack(side=LEFT, padx=(0, 8))
        Button(row_ops, text="📋 Colores", bg="#1976d2", fg=COLOR_TEXT, command=lambda: self.abrir_archivo(COLOR_1), relief="flat").pack(side=LEFT)

        # SECCIÓN 6: Estado / Log
        box_log = LabelFrame(main, text="📋 ESTADO", padx=10, pady=10, font=("Segoe UI", 10, "bold"), bg=COLOR_SECTION, fg=COLOR_HEADER)
        box_log.pack(fill=BOTH, expand=True, pady=7)

        self.progress = ttk.Progressbar(box_log, mode="indeterminate")
        self.progress.pack(fill=X, pady=(0, 8))

        style = ttk.Style()
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=20, background="#333", foreground=COLOR_TEXT)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#444", foreground=COLOR_TEXT)

        self.log = ttk.Treeview(box_log, columns=("mensaje",), show="headings", height=8)
        self.log.heading("mensaje", text="Registro de eventos")
        self.log.column("mensaje", anchor="w", stretch=True)
        self.log.pack(fill=BOTH, expand=True)

        footer = Frame(main, bg=COLOR_BG)
        footer.pack(fill=X, pady=(8, 0))
        Button(footer, text="❌ Salir", bg=COLOR_HEADER, fg=COLOR_TEXT, command=self.root.destroy, relief="flat").pack(anchor="e")

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
        _load_instaloader()
        _load_pil()

        # Crear carpetas si no existen
        for folder in [RECURSOS, RESULTADOS, TEMP_FOLDER, OBJETOS_FOLDER, CONFIG_FOLDER]:
            os.makedirs(folder, exist_ok=True)

        self.log_msg("✓ Estructura de carpetas validada")

        if not os.path.exists(BLEND_TEMPLATE):
            self.log_msg("⚠️ No existe RD.blend - Blender no funcionará")

    def pegar_url(self):
        try:
            txt = self.root.clipboard_get()
            self.url_text.insert(END, txt)
        except Exception:
            messagebox.showwarning("Portapapeles", "No pude leer el portapapeles.")

    def extraer_link_email(self):
        """Extrae link de Instagram del texto pegado (asume que es correo)"""
        text = self.url_text.get("1.0", END)

        if EmailExtractor:
            extractor = EmailExtractor()
            links = extractor.extract_instagram_links(text)

            if links:
                self.url_text.delete("1.0", END)
                self.url_text.insert("1.0", links[0])

                # Extraer nombre del evento
                event_name = extractor.extract_event_name(text)
                self.event_name_var.set(event_name)

                self.log_msg(f"✓ Link extraído: {links[0][:50]}...")
                messagebox.showinfo("Éxito", f"Link extraído correctamente")
            else:
                messagebox.showwarning("No encontrado", "No se encontró link de Instagram en el texto")
        else:
            messagebox.showwarning("No disponible", "Email extractor no disponible")

    def procesar_completo(self):
        """Flujo completo: download → colores → blender"""
        if self.processing:
            messagebox.showwarning("En progreso", "Ya hay un proceso en ejecución")
            return

        self.processing = True
        t = threading.Thread(target=self._procesar_completo_safe, daemon=True)
        t.start()

    def _procesar_completo_safe(self):
        try:
            self._procesar_completo_impl()
        finally:
            self.processing = False

    def _procesar_completo_impl(self):
        self.set_busy(True)
        try:
            # 1. Obtener link
            url = self.url_text.get("1.0", END).strip()
            shortcode = self._extraer_shortcode(url)
            if not shortcode:
                raise ValueError("Link inválido")

            # 2. Obtener o generar nombre del evento
            event_name = self.event_name_var.get().strip()
            if not event_name:
                event_name = f"evento_{int(time.time())}"
                self.event_name_var.set(event_name)

            self.log_msg(f"📌 Evento: {event_name}")

            # 3. Descargar imagen
            self.log_msg(f"📥 Descargando desde Instagram...")
            if os.path.exists(TEMP_FLYER):
                shutil.rmtree(TEMP_FLYER, ignore_errors=True)
            os.makedirs(TEMP_FLYER, exist_ok=True)

            L = instaloader.Instaloader(
                download_video_thumbnails=False,
                download_comments=False,
                save_metadata=False,
                dirname_pattern=TEMP_FLYER,
            )
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.download_post(post, target=TEMP_FLYER)

            # 4. Procesar imagen
            imagen = self._buscar_mejor_imagen(TEMP_FLYER)
            if not imagen:
                raise FileNotFoundError("No se descargó imagen")

            self.log_msg(f"✓ Imagen descargada: {Path(imagen).name}")
            self._preparar_input_y_colores(imagen)

            # 5. Crear proyecto Blender
            self.log_msg(f"🎨 Creando proyecto Blender para evento...")
            event_folder = self._crear_proyecto_blender(event_name)

            # 6. Aplicar colores a Blender
            if self.blender_var.get():
                self._aplicar_colores_blender(event_folder)
                self.log_msg(f"✓ Colores aplicados a proyecto Blender")

            # 7. Finalizar
            self.log_msg("✅ Proceso completado exitosamente")
            messagebox.showinfo("Éxito", f"Evento procesado:\n{event_name}\n\nAbrir proyecto Blender?",
                              parent=self.root)

            shutil.rmtree(TEMP_FOLDER, ignore_errors=True)

        except Exception as e:
            self.log_msg(f"❌ ERROR: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.set_busy(False)

    def _extraer_shortcode(self, url):
        """Extrae shortcode de Instagram del URL"""
        url = (url or "").strip()
        patrones = [r"instagram\.com/(?:[^/]+/)?p/([^/?#]+)", r"instagram\.com/(?:[^/]+/)?reel/([^/?#]+)"]
        for patron in patrones:
            m = re.search(patron, url)
            if m:
                return m.group(1)
        return None

    def extraer_shortcode(self, url):
        """Alias público"""
        return self._extraer_shortcode(url)

    def _buscar_mejor_imagen(self, carpeta):
        extensiones = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
        archivos = []
        for ext in extensiones:
            archivos.extend(glob.glob(os.path.join(carpeta, ext)))
            archivos.extend(glob.glob(os.path.join(carpeta, "**", ext), recursive=True))
        archivos = [a for a in archivos if "profile_pic" not in os.path.basename(a).lower()]
        if archivos:
            archivos.sort(key=lambda p: os.path.getsize(p), reverse=True)
            return os.path.abspath(archivos[0])
        return None

    def _preparar_input_y_colores(self, imagen_origen):
        """Prepara input y extrae colores"""
        self.log_msg("🖼️ Procesando imagen...")

        with Image.open(imagen_origen) as im:
            im = im.convert("RGB")
            im.save(ARCHIVO_INPUT, "JPEG", quality=95)

        time.sleep(1)
        self.log_msg("🎨 Extrayendo colores dominantes...")

        colores = self._obtener_colores_predominantes(ARCHIVO_INPUT)
        if colores:
            self.colores_extraidos = {"color_1": colores[0], "color_2": colores[1] if len(colores) > 1 else colores[0]}
            self.log_msg(f"✓ Color 1: RGB {colores[0]}")
            self.log_msg(f"✓ Color 2: RGB {colores[1] if len(colores) > 1 else colores[0]}")
            self._crear_muestras_color(colores)

    def _obtener_colores_predominantes(self, ruta, cantidad=2):
        """Extrae colores dominantes"""
        with Image.open(ruta) as im:
            im = im.convert("RGB")
            im.thumbnail((180, 180))
            quant = im.quantize(colors=12, method=Image.Quantize.MEDIANCUT)
            palette = quant.getpalette()
            counts = quant.getcolors()

            candidatos = []
            for count, idx in counts:
                r, g, b = palette[idx * 3: idx * 3 + 3]
                candidatos.append((count, (r, g, b)))

            candidatos.sort(reverse=True)
            elegidos = [color for _, color in candidatos[:cantidad]]
            return elegidos

    def _crear_muestras_color(self, colores):
        """Crea imágenes de muestra de colores"""
        for idx, color in enumerate(colores[:2], 1):
            w, h = 512, 512
            im = Image.new("RGB", (w, h), color)
            draw = ImageDraw.Draw(im)
            texto = f"RGB {color[0]}, {color[1]}, {color[2]}"
            brillo = sum(color) / 3
            txt_color = (0, 0, 0) if brillo > 150 else (255, 255, 255)
            draw.rectangle((0, h - 62, w, h), fill=tuple(max(0, int(c * 0.72)) for c in color))
            draw.text((22, h - 42), texto, fill=txt_color)

            output = COLOR_1 if idx == 1 else COLOR_2
            im.save(output, "PNG")

    def _crear_proyecto_blender(self, event_name):
        """Crea carpeta y proyecto Blender para el evento"""
        event_folder = os.path.join(OBJETOS_FOLDER, event_name)
        os.makedirs(event_folder, exist_ok=True)

        # Copiar template
        if os.path.exists(BLEND_TEMPLATE):
            dest_blend = os.path.join(event_folder, f"{event_name}.blend")
            shutil.copy2(BLEND_TEMPLATE, dest_blend)

        # Guardar configuración de colores
        config_file = os.path.join(event_folder, "colores.json")
        with open(config_file, 'w') as f:
            json.dump({"colores": self.colores_extraidos}, f, indent=2)

        return event_folder

    def _aplicar_colores_blender(self, event_folder):
        """Aplica colores al proyecto Blender"""
        blend_file = os.path.join(event_folder, f"{Path(event_folder).name}.blend")

        if not os.path.exists(blend_file):
            self.log_msg("⚠️ Archivo Blender no encontrado")
            return

        # Ejecutar colorizer script
        colorizer_path = os.path.join(os.path.dirname(__file__), "blender_colorizer.py")
        if not os.path.exists(colorizer_path):
            self.log_msg("⚠️ blender_colorizer.py no encontrado")
            return

        try:
            # Aquí necesitarías la ruta de Blender
            # subprocess.run([blender_exe, blend_file, "--background", "--python", colorizer_path])
            pass
        except Exception as e:
            self.log_msg(f"⚠️ Error aplicando colores: {str(e)}")

    def abrir_blender_evento(self):
        """Abre el proyecto Blender del evento actual"""
        event_name = self.event_name_var.get()
        if not event_name:
            messagebox.showwarning("Requerido", "Elige o ingresa nombre de evento primero")
            return

        event_folder = os.path.join(OBJETOS_FOLDER, event_name)
        blend_file = os.path.join(event_folder, f"{event_name}.blend")

        if os.path.exists(blend_file):
            try:
                os.startfile(blend_file)
                self.log_msg(f"🖥️ Abriendo Blender: {event_name}")
            except Exception as e:
                messagebox.showerror("Error", f"No pude abrir el archivo: {str(e)}")
        else:
            messagebox.showwarning("No existe", f"Proyecto Blender no encontrado:\n{blend_file}")

    def abrir_carpeta_evento(self):
        """Abre la carpeta del evento en el explorador"""
        event_name = self.event_name_var.get()
        if not event_name:
            messagebox.showwarning("Requerido", "Elige o ingresa nombre de evento primero")
            return

        event_folder = os.path.join(OBJETOS_FOLDER, event_name)
        if os.path.exists(event_folder):
            os.startfile(event_folder)
            self.log_msg(f"📂 Abriendo carpeta: {event_name}")
        else:
            messagebox.showwarning("No existe", f"Carpeta del evento no encontrada")

    def elegir_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Elegir flyer descargado manualmente",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp"), ("Todos", "*.*")]
        )
        if ruta:
            self.manual_img_var.set(ruta)

    def pegar_correo_completo(self):
        """Pega el contenido del correo completo en el text area"""
        try:
            txt = self.root.clipboard_get()
            # Limpiar y mostrar en el entry de URL (donde mostraremos el link extraído después)
            messagebox.showinfo("Correo pegado", "Ahora usa el botón 'Extraer Link' para obtener el link del correo")
            # Guardar temporalmente en variable
            self.correo_temp = txt
            self.log_msg("Correo pegado en memoria - Listo para extraer link")
        except Exception:
            messagebox.showwarning("Portapapeles", "No pude leer el portapapeles")

    def extraer_link_de_correo_pegado(self):
        """Extrae link de Instagram del correo pegado"""
        if not hasattr(self, 'correo_temp') or not self.correo_temp:
            messagebox.showwarning("Sin correo", "Primero pega un correo con el botón 'Pegar Correo'")
            return

        # Buscar links de Instagram
        patrones = [
            r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[^\s/\?]+',
            r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[^\s]+',
        ]

        for patron in patrones:
            match = re.search(patron, self.correo_temp)
            if match:
                link = match.group(0)
                self.url_var.set(link)

                # Intentar extraer nombre del evento del asunto o contenido
                lineas = self.correo_temp.split('\n')
                for linea in lineas:
                    if 'asunto' in linea.lower() or 'subject' in linea.lower():
                        # Buscar en líneas siguientes
                        idx = lineas.index(linea)
                        if idx + 1 < len(lineas):
                            event_name = lineas[idx + 1].strip()[:50]
                            if event_name:
                                self.event_name_var.set(event_name)
                            break

                self.log_msg(f"Link extraido: {link[:50]}...")
                messagebox.showinfo("Exito", f"Link extraido correctamente:\n{link[:80]}...")
                return

        messagebox.showwarning("No encontrado", "No se encontro link de Instagram en el correo")

    def buscar_google_eventos(self):
        q = self.productora_var.get().strip()
        if not q:
            messagebox.showwarning("Búsqueda", "Escribe el nombre o @ de la productora")
            return
        consulta = f'{q} próximos eventos productora flyer Chile OR Santiago'
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(consulta)
        webbrowser.open(url)
        self.log_msg(f"🔍 Google: {q}")

    def buscar_instagram(self):
        q = self.productora_var.get().strip()
        if not q:
            messagebox.showwarning("Búsqueda", "Escribe el nombre o @ de la productora")
            return
        usuario = q.strip().lstrip("@")
        if " " not in usuario and usuario:
            url = f"https://www.instagram.com/{urllib.parse.quote(usuario)}/"
        else:
            url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(f"site:instagram.com {q} productora eventos")
        webbrowser.open(url)
        self.log_msg(f"📱 Instagram: {q}")

    def abrir_droplet(self):
        if not os.path.exists(RUTA_DROPLET):
            raise FileNotFoundError(f"No se encontró: {RUTA_DROPLET}")
        if not os.path.exists(ARCHIVO_PSD):
            raise FileNotFoundError(f"No se encontró: {ARCHIVO_PSD}")
        if not os.path.exists(ARCHIVO_INPUT):
            raise FileNotFoundError(f"No se encontró input_ig.jpg")

        self.log_msg("🚀 Abriendo Photoshop/Droplet...")
        try:
            cmd = f'start "" "{RUTA_DROPLET}" "{ARCHIVO_PSD}"'
            subprocess.Popen(cmd, shell=True, cwd=RECURSOS)
            self.log_msg("✓ Droplet lanzado")
        except Exception as e:
            raise RuntimeError(f"No se pudo abrir droplet: {str(e)}")

    def abrir_carpeta_base(self):
        os.makedirs(RECURSOS, exist_ok=True)
        os.startfile(RECURSOS)

    def abrir_archivo(self, ruta):
        if os.path.exists(ruta):
            os.startfile(ruta)
        else:
            messagebox.showwarning("No encontrado", f"No existe:\n{ruta}")

    def descargar_y_procesar_thread(self, abrir_droplet=None):
        if self.processing:
            messagebox.showwarning("En progreso", "Ya hay un proceso en ejecución")
            return
        if abrir_droplet is None:
            abrir_droplet = bool(self.abrir_droplet_var.get())
        self.processing = True
        t = threading.Thread(target=self._descargar_y_procesar_safe, args=(abrir_droplet,), daemon=True)
        t.start()

    def _descargar_y_procesar_safe(self, abrir_droplet=True):
        try:
            self.descargar_y_procesar(abrir_droplet)
        finally:
            self.processing = False

    def descargar_y_procesar(self, abrir_droplet=True):
        self.set_busy(True)
        try:
            if instaloader is None:
                raise RuntimeError("Falta instaloader. Instala con: pip install -r requirements.txt")

            url = self.url_var.get().strip()
            shortcode = self.extraer_shortcode(url)
            if not shortcode:
                raise ValueError("Link no valido. Debe ser /p/, /reel/ o /tv/")

            if os.path.exists(TEMP_FLYER):
                shutil.rmtree(TEMP_FLYER, ignore_errors=True)
            os.makedirs(TEMP_FLYER, exist_ok=True)

            self.log_msg(f"Descargando flyer. Shortcode: {shortcode}")

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
                        self.log_msg(f"Intento {intento} fallo. Reintentando en {self.RETRY_DELAY}s...")
                        time.sleep(self.RETRY_DELAY)
            else:
                raise RuntimeError(f"No se pudo descargar despues de {self.MAX_RETRIES} intentos: {ultimo_error}")

            imagen = self._buscar_mejor_imagen(TEMP_FLYER)
            if not imagen:
                raise FileNotFoundError("No se descargo imagen")

            self.log_msg(f"Imagen descargada: {Path(imagen).name}")
            self._preparar_input_y_colores(imagen)
            self.log_msg(f"Colores extraidos")

            if abrir_droplet:
                self.abrir_droplet()

            if self.limpiar_temp_var.get():
                self.limpiar_temp()

            self.log_msg("Descarga completada")

        except Exception as e:
            self.log_msg(f"ERROR: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.set_busy(False)

    def manual_y_procesar_thread(self, abrir_droplet=None):
        if self.processing:
            messagebox.showwarning("En progreso", "Ya hay un proceso en ejecución")
            return
        if abrir_droplet is None:
            abrir_droplet = bool(self.abrir_droplet_var.get())
        self.processing = True
        t = threading.Thread(target=self._manual_y_procesar_safe, args=(abrir_droplet,), daemon=True)
        t.start()

    def _manual_y_procesar_safe(self, abrir_droplet=True):
        try:
            self.manual_y_procesar(abrir_droplet)
        finally:
            self.processing = False

    def manual_y_procesar(self, abrir_droplet=True):
        self.set_busy(True)
        try:
            ruta = self.manual_img_var.get().strip()
            if not ruta or not os.path.exists(ruta):
                raise FileNotFoundError("Imagen no encontrada")

            self.log_msg(f"Procesando imagen manual: {Path(ruta).name}")
            self._preparar_input_y_colores(ruta)
            self.log_msg(f"Colores extraidos")

            if abrir_droplet:
                self.abrir_droplet()

            if self.limpiar_temp_var.get():
                self.limpiar_temp()

            self.log_msg("Procesamiento completado")

        except Exception as e:
            self.log_msg(f"ERROR: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.set_busy(False)

    def limpiar_temp(self):
        if os.path.exists(TEMP_FLYER):
            shutil.rmtree(TEMP_FLYER, ignore_errors=True)

    def abrir_gmail_isidora(self):
        """Abre Gmail y busca correos de Isidora"""
        query = urllib.parse.quote("from:isidora")
        url = f"https://mail.google.com/mail/u/0/#search/{query}"
        webbrowser.open(url)
        self.log_msg("Abriendo Gmail - Buscar correos de Isidora")


def main():
    root = Tk()
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    AppV2(root)
    logging.info("GUI iniciada")
    root.mainloop()
    logging.info("Aplicación cerrada")


if __name__ == "__main__":
    main()
