import customtkinter as ctk
import tkinter as tk
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Polygon as MplPolygon, Rectangle
from matplotlib.figure import Figure
from tkinter import messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class PlanoTeatroVisualizer(ctk.CTk):
    COLOR_ESCENARIO = "#1c2833"
    COLOR_BUTACA_PRINCIPAL = "#e63946"
    COLOR_BUTACA_BALCON = "#d62839"
    COLOR_PARED = "#d4b78f"
    COLOR_PASILLO = "#888888"
    COLOR_MEDIDAS = "#ffcc00"
    COLOR_GRID = "#4a4f55"
    COLOR_EMPTY = "#ffcc00"

    def __init__(self):
        super().__init__()
        self.title("PLANO ARQUITECTÓNICO PRO v3.4 - Teatro SCD Plaza Egaña")
        self.geometry("1920x1080")

        self.grid_columnconfigure(0, weight=1, minsize=680)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)

        # ====================== VARIABLES ======================
        self.prof_total = tk.DoubleVar(value=4.5)
        self.prof_recta = tk.DoubleVar(value=3.6)
        self.ancho_esc = tk.DoubleVar(value=10.0)

        self.dist_fila1 = tk.DoubleVar(value=2.0)
        self.ancho_pasillo = tk.DoubleVar(value=1.2)
        self.cant_filas = tk.IntVar(value=7)
        self.huella = tk.DoubleVar(value=0.9)
        self.ancho_butaca = tk.DoubleVar(value=0.55)

        self.c_f1 = tk.IntVar(value=9)
        self.c_ff = tk.IntVar(value=20)
        self.l_f1 = tk.IntVar(value=4)
        self.l_ff = tk.IntVar(value=5)

        self.incluir_balcon = tk.BooleanVar(value=True)
        self.dist_balcon = tk.DoubleVar(value=3.8)
        self.cant_filas_balcon = tk.IntVar(value=3)

        self.walls_only_mode = tk.BooleanVar(value=False)
        self.show_grid = tk.BooleanVar(value=True)
        self.show_labels = tk.BooleanVar(value=True)
        self.show_dimensions = tk.BooleanVar(value=True)
        self.wall_thickness = tk.DoubleVar(value=0.42)
        self.wall_margin_deg = tk.DoubleVar(value=6.0)
        self.usar_config_manual = tk.BooleanVar(value=False)

        self.usar_config_manual_balcon = tk.BooleanVar(value=True)
        self.balcon_fila_config = []
        self.table_frame_balcon = None

        self.dist_back_wall = tk.DoubleVar(value=5.0)
        self.pasillo_backstage_width = tk.DoubleVar(value=1.0)

        self.align_radial = tk.BooleanVar(value=True)

        self.fila_config = []
        self.table_frame = None

        self.current_full_xlim = None
        self.current_full_ylim = None

        self.crear_interfaz()
        self.actualizar_vista()

    def crear_interfaz(self):
        panel = ctk.CTkScrollableFrame(self, corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        ctk.CTkLabel(panel, text="PLANO ARQUITECTÓNICO PRO v3.4\nTeatro SCD Plaza Egaña",
                     font=("Helvetica", 26, "bold")).pack(pady=(30, 15))

        self.crear_seccion(panel, "1. Geometría del Escenario")
        self.crear_slider_con_entrada(panel, "Profundidad Total (m)", self.prof_total, 3.0, 6.0)
        self.crear_slider_con_entrada(panel, "Profundidad Recta (m)", self.prof_recta, 1.0, 5.0)
        self.crear_slider_con_entrada(panel, "Ancho Escenario (Cuerda) (m)", self.ancho_esc, 6.0, 16.0)

        self.crear_seccion(panel, "2. Sala Principal - Butacas")
        self.crear_slider_con_entrada(panel, "Distancia Fila 1 al Escenario (m)", self.dist_fila1, 1.0, 4.0)
        self.crear_slider_con_entrada(panel, "Ancho Pasillos (m)", self.ancho_pasillo, 0.8, 2.0)
        self.crear_slider_con_entrada(panel, "Cantidad de Filas", self.cant_filas, 1, 12, es_entero=True, extra_command=self.refresh_fila_table)
        self.crear_slider_con_entrada(panel, "Huella (profundidad fila) (m)", self.huella, 0.7, 1.2)

        self.crear_seccion(panel, "Progresión de Bloques (Simétrica) - Planta Baja")
        self.crear_slider_con_entrada(panel, "Centro - Fila 1", self.c_f1, 1, 15, es_entero=True)
        self.crear_slider_con_entrada(panel, "Centro - Última Fila", self.c_ff, 1, 30, es_entero=True)
        self.crear_slider_con_entrada(panel, "Laterales - Fila 1", self.l_f1, 1, 8, es_entero=True)
        self.crear_slider_con_entrada(panel, "Laterales - Última Fila", self.l_ff, 1, 10, es_entero=True)

        self.crear_seccion(panel, "Configuración Manual por Fila - Planta Baja")
        self.table_frame = ctk.CTkFrame(panel, fg_color="#1f252d", corner_radius=8)
        self.table_frame.pack(fill="x", padx=20, pady=8)
        ctk.CTkCheckBox(panel, text="Usar configuración manual por fila (sobrescribe progresión)",
                        variable=self.usar_config_manual, command=self.refresh_fila_table).pack(anchor="w", padx=20, pady=6)

        self.crear_seccion(panel, "Configuración Manual por Fila - BALCÓN")
        self.table_frame_balcon = ctk.CTkFrame(panel, fg_color="#1f252d", corner_radius=8)
        self.table_frame_balcon.pack(fill="x", padx=20, pady=8)
        ctk.CTkCheckBox(panel, text="Usar configuración manual por fila en el BALCÓN",
                        variable=self.usar_config_manual_balcon, command=self.refresh_balcon_table).pack(anchor="w", padx=20, pady=6)
        ctk.CTkButton(panel, text="Generar 8-11-8 en todas las filas del balcón",
                      command=self.generar_balcon_8_11_8).pack(pady=8, padx=20)

        balcon_frame = ctk.CTkFrame(panel, fg_color="#252a32", corner_radius=12)
        balcon_frame.pack(fill="x", padx=20, pady=25)
        ctk.CTkCheckBox(balcon_frame, text="Incluir Balcón Superior",
                        variable=self.incluir_balcon, command=self.actualizar_vista).pack(anchor="w", padx=18, pady=8)
        self.crear_slider_con_entrada(balcon_frame, "Distancia al Balcón (m)", self.dist_balcon, 2.0, 6.0)
        self.crear_slider_con_entrada(balcon_frame, "Cantidad de Filas en Balcón", self.cant_filas_balcon, 1, 8, es_entero=True, extra_command=self.refresh_balcon_table)

        self.crear_seccion(panel, "Controles Visuales y Modelaje")
        ctk.CTkCheckBox(panel, text="Modo Solo Paredes + delineado de bloques de butacas (3 por fila)",
                        variable=self.walls_only_mode, command=self.actualizar_vista).pack(anchor="w", padx=20, pady=4)
        ctk.CTkCheckBox(panel, text="Mostrar grid arquitectónico (cuadriculado)",
                        variable=self.show_grid, command=self.actualizar_vista).pack(anchor="w", padx=20, pady=4)
        ctk.CTkCheckBox(panel, text="Mostrar etiquetas de filas",
                        variable=self.show_labels, command=self.actualizar_vista).pack(anchor="w", padx=20, pady=4)
        ctk.CTkCheckBox(panel, text="Mostrar medidas dimensionales",
                        variable=self.show_dimensions, command=self.actualizar_vista).pack(anchor="w", padx=20, pady=8)

        self.crear_slider_con_entrada(panel, "Distancia última fila al muro posterior (m)", self.dist_back_wall, 2.0, 12.0)
        self.crear_slider_con_entrada(panel, "Ancho pasillos backstage (m) - máximo 1 m", self.pasillo_backstage_width, 0.5, 1.0)

        self.crear_slider_con_entrada(panel, "Grosor de paredes REAL (m) - para exportar", self.wall_thickness, 0.2, 1.0)
        self.crear_slider_con_entrada(panel, "Margen extra de paredes (°)", self.wall_margin_deg, 0, 15)

        # Exportación
        export_frame = ctk.CTkFrame(panel, fg_color="#252a32", corner_radius=12)
        export_frame.pack(fill="x", padx=20, pady=25)
        ctk.CTkLabel(export_frame, text="Exportar Plano", font=("Helvetica", 16, "bold"), text_color="#5cc0ff").pack(pady=(12, 6))
        btn_frame = ctk.CTkFrame(export_frame, fg_color="transparent")
        btn_frame.pack(pady=8, padx=18, fill="x")
        ctk.CTkButton(btn_frame, text="PNG 300 dpi", width=130, command=lambda: self.exportar("png")).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="PDF", width=130, command=lambda: self.exportar("pdf")).pack(side="left", padx=3)
        ctk.CTkButton(btn_frame, text="SVG", width=130, command=lambda: self.exportar("svg")).pack(side="left", padx=3)
        ctk.CTkButton(export_frame, text="Exportar SOLO CONTORNOS (SVG/PDF) - para Blender EXTRUDE",
                      font=("Helvetica", 13, "bold"), fg_color="#ff8800",
                      command=lambda: self.exportar("svg", outline_only=True)).pack(pady=12, padx=18, fill="x")

        self.lbl_radio = ctk.CTkLabel(export_frame, text="Radio escenario: — m", font=("Consolas", 13))
        self.lbl_radio.pack(anchor="w", padx=18)
        self.lbl_empty = ctk.CTkLabel(export_frame, text="Posición Empty: — m", font=("Consolas", 13))
        self.lbl_empty.pack(anchor="w", padx=18)
        self.lbl_total = ctk.CTkLabel(export_frame, text="Total butacas: —",
                                      font=("Consolas", 15, "bold"), text_color="#ffcc00")
        self.lbl_total.pack(anchor="w", padx=18, pady=(6, 12))

        # ====================== VISTA ======================
        vista_frame = ctk.CTkFrame(self, fg_color="#1a1d24")
        vista_frame.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

        control_bar = ctk.CTkFrame(vista_frame, fg_color="#252a32", corner_radius=8)
        control_bar.pack(side="top", fill="x", padx=12, pady=8)
        ctk.CTkButton(control_bar, text="🔄 Vista Completa",
                      font=("Helvetica", 14, "bold"), width=180,
                      command=self.reset_view).pack(side="left", padx=12, pady=6)

        self.fig = Figure(figsize=(18.5, 12.8), dpi=100, facecolor="#1a1d24")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1a1d24")

        self.canvas_mat = FigureCanvasTkAgg(self.fig, master=vista_frame)
        self.canvas_widget = self.canvas_mat.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas_mat, vista_frame)
        self.toolbar.pack(side="top", fill="x", pady=(0, 8))

        self.canvas_widget.bind("<Configure>", self.actualizar_vista)
        self.canvas_mat.mpl_connect('scroll_event', self._on_scroll)
        self.canvas_mat.mpl_connect('key_press_event', self._on_key_press)

        self.refresh_fila_table()
        self.refresh_balcon_table()

    # ==================== TABLAS ====================
    def refresh_fila_table(self):
        if not self.table_frame: return
        for widget in self.table_frame.winfo_children(): widget.destroy()
        self.fila_config = []
        cant = self.cant_filas.get()
        for f in range(cant):
            row_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=3, padx=12)
            ctk.CTkLabel(row_frame, text=f"Fila {f+1}", width=80, font=("Consolas", 13)).pack(side="left")
            cen_var = tk.IntVar(value=9)
            lat_var = tk.IntVar(value=4)
            if f == 0: cen_var.set(self.c_f1.get()); lat_var.set(self.l_f1.get())
            elif f == cant-1: cen_var.set(self.c_ff.get()); lat_var.set(self.l_ff.get())
            entry_cen = ctk.CTkEntry(row_frame, width=70, textvariable=cen_var, font=("Consolas", 13))
            entry_cen.pack(side="left", padx=8)
            entry_lat = ctk.CTkEntry(row_frame, width=70, textvariable=lat_var, font=("Consolas", 13))
            entry_lat.pack(side="left", padx=8)
            total_var = tk.StringVar()
            def actualizar_total(*args):
                try: total_var.set(str(cen_var.get() + 2 * lat_var.get()))
                except: total_var.set("—")
            cen_var.trace("w", actualizar_total)
            lat_var.trace("w", actualizar_total)
            actualizar_total()
            ctk.CTkLabel(row_frame, text="Butacas:", font=("Consolas", 12)).pack(side="left", padx=(20, 4))
            ctk.CTkLabel(row_frame, textvariable=total_var, font=("Consolas", 14, "bold"), text_color="#ffcc00").pack(side="left")
            self.fila_config.append({"cen": cen_var, "lat": lat_var})

    def refresh_balcon_table(self):
        if not self.table_frame_balcon: return
        for widget in self.table_frame_balcon.winfo_children(): widget.destroy()
        self.balcon_fila_config = []
        cant = self.cant_filas_balcon.get()
        for f in range(cant):
            row_frame = ctk.CTkFrame(self.table_frame_balcon, fg_color="transparent")
            row_frame.pack(fill="x", pady=3, padx=12)
            ctk.CTkLabel(row_frame, text=f"B{f+1}", width=80, font=("Consolas", 13)).pack(side="left")
            cen_var = tk.IntVar(value=11)
            lat_var = tk.IntVar(value=8)
            entry_cen = ctk.CTkEntry(row_frame, width=70, textvariable=cen_var, font=("Consolas", 13))
            entry_cen.pack(side="left", padx=8)
            entry_lat = ctk.CTkEntry(row_frame, width=70, textvariable=lat_var, font=("Consolas", 13))
            entry_lat.pack(side="left", padx=8)
            total_var = tk.StringVar()
            def actualizar_total(*args):
                try: total_var.set(str(cen_var.get() + 2 * lat_var.get()))
                except: total_var.set("—")
            cen_var.trace("w", actualizar_total)
            lat_var.trace("w", actualizar_total)
            actualizar_total()
            ctk.CTkLabel(row_frame, text="Butacas:", font=("Consolas", 12)).pack(side="left", padx=(20, 4))
            ctk.CTkLabel(row_frame, textvariable=total_var, font=("Consolas", 14, "bold"), text_color="#ffcc00").pack(side="left")
            self.balcon_fila_config.append({"cen": cen_var, "lat": lat_var})

    def generar_balcon_8_11_8(self):
        self.usar_config_manual_balcon.set(True)
        self.refresh_balcon_table()
        self.actualizar_vista()

    # ==================== PASILLOS BACKSTAGE (L hacia DENTRO + polígono cerrado) ====================
 # ==================== PASILLOS BACKSTAGE (REDISEÑADO - CÓDIGO INTACTO) ====================
    # ==================== PASILLOS BACKSTAGE (SOLUCIÓN SIMPLE Y DIRECTA) ====================
    def _dibujar_pasillos_backstage(self, ax, ancho, p_rec, pw):
        lw = self.wall_thickness.get() * 8

        # El borde del escenario es exactamente ancho / 2
        x_esc = ancho /1.6
        y_start = p_rec

        # ALARGAMOS LA FORMA:
        # Sumamos pw * 2.5 para que la línea sobresalga y conecte con la pared diagonal.
        # (Si ves que le falta o se pasa un poco al chocar con la pared, solo ajusta ese 2.5)
        x_fin = x_esc + (pw )

        largo_atras = pw * 5.0

        # --- LADO IZQUIERDO ---
        # Línea del escenario hacia afuera
        ax.plot([-x_esc, -x_fin], [y_start, y_start], color=self.COLOR_PARED, linewidth=lw)
        # Línea bajando
        ax.plot([-x_fin, -x_fin], [y_start, y_start - largo_atras], color=self.COLOR_PARED, linewidth=lw)

        # --- LADO DERECHO ---
        # Línea del escenario hacia afuera
        ax.plot([x_esc, x_fin], [y_start, y_start], color=self.COLOR_PARED, linewidth=lw)
        # Línea bajando
        ax.plot([x_fin, x_fin], [y_start, y_start - largo_atras], color=self.COLOR_PARED, linewidth=lw)

        # --- CIERRE TRASERO ---
        ax.plot([-x_fin, x_fin], [y_start - largo_atras, y_start - largo_atras], color=self.COLOR_PARED, linewidth=lw)

    # ==================== ESCENARIO + PAREDES LATERALES ====================
    def _dibujar_escenario(self, ax, radio, y_empty, ancho, p_rec, fill_enabled, walls_only):
        alpha = 1.0 if fill_enabled else 0.0
        edge_w = 4 if fill_enabled else 3.0
        rect = Rectangle((-ancho/2, 0), ancho, p_rec, facecolor=self.COLOR_ESCENARIO if fill_enabled else "none", edgecolor="#555555", linewidth=edge_w, alpha=alpha)
        ax.add_patch(rect)

        # Paredes laterales paralelas del escenario
        side_lw = 5 if fill_enabled else 3.5
        ax.plot([-ancho/2, -ancho/2], [0, p_rec], color="#555555", linewidth=side_lw)
        ax.plot([ancho/2, ancho/2], [0, p_rec], color="#555555", linewidth=side_lw)

        # Curva
        ang_mitad = math.asin((ancho/2) / radio)
        theta = np.linspace(-ang_mitad, ang_mitad, 120)
        x_curve = radio * np.sin(theta)
        y_curve = y_empty + radio * np.cos(theta)
        x_poly = np.concatenate((x_curve, [ancho/2, -ancho/2]))
        y_poly = np.concatenate((y_curve, [p_rec, p_rec]))
        ax.fill(x_poly, y_poly, color="#0f1419" if fill_enabled else "none", edgecolor="#555555", linewidth=edge_w, alpha=alpha)

        for dy in [0.6, 1.2, 1.8, 2.4, 3.0]:
            ax.plot([-ancho/2 + 0.3, ancho/2 - 0.3], [dy, dy], color="#666666", linewidth=1.2, linestyle="--", alpha=0.8)
        ax.plot([-ancho/2, ancho/2], [p_rec, p_rec], color="#777777", linewidth=3.5)
        ax.plot(0, y_empty, 'o', markersize=12, color=self.COLOR_EMPTY, markeredgecolor="white", markeredgewidth=2.5)

    # ==================== DIBUJO PRINCIPAL (ZOOM SIN RECORTE + GRID SIEMPRE VISIBLE) ====================
    def _draw_to_ax(self, ax, walls_only=False, wireframe=False, set_full_limits=True):
        p_tot = self.prof_total.get()
        p_rec = self.prof_recta.get()
        ancho = self.ancho_esc.get()
        sagita = max(p_tot - p_rec, 0.01)
        radio = (sagita**2 + (ancho/2)**2) / (2 * sagita)
        y_empty = p_tot - radio

        self.lbl_radio.configure(text=f"Radio escenario: {radio:.3f} m")
        self.lbl_empty.configure(text=f"Posición Empty: {y_empty:.3f} m")

        r_max = radio + self.dist_fila1.get() + (self.cant_filas.get() - 1) * self.huella.get() + self.dist_back_wall.get() + 35
        if self.incluir_balcon.get():
            r_max += self.dist_balcon.get() + (self.cant_filas_balcon.get() - 1) * self.huella.get() + 20

        # GRID PRIMERO
        if self.show_grid.get():
            ax.grid(True, color=self.COLOR_GRID, linestyle="-", linewidth=1.5, alpha=0.9, zorder=5)

        fill_enabled = not wireframe
        draw_butacas = True
        if walls_only:
            fill_enabled = False

        self._dibujar_escenario(ax, radio, y_empty, ancho, p_rec, fill_enabled, walls_only)
        total, last_n_cen, last_n_lat, ang_max, ang_cen_last, ang_pasillo_last, ang_lat_last = self._dibujar_butacas_principales(ax, radio, y_empty, draw_butacas, fill_enabled)

        if self.incluir_balcon.get():
            total += self._dibujar_balcon(ax, radio, y_empty, last_n_cen, last_n_lat, ang_max, ang_cen_last, ang_pasillo_last, ang_lat_last, draw_butacas, fill_enabled, wireframe)

        self.lbl_total.configure(text=f"Total butacas: {total:,}")

        self._dibujar_paredes(ax, radio, y_empty, ang_max, wireframe, ancho, p_rec)

        if self.show_dimensions.get():
            self._dibujar_medidas(ax, radio, y_empty, ancho, p_rec, r_max, sagita, ang_max)

        # GRID FINAL (nunca se tapa)
        if self.show_grid.get():
            ax.grid(True, color=self.COLOR_GRID, linestyle="-", linewidth=1.5, alpha=0.9, zorder=100)

        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.axis('off')

        ax.text(0, -radio - 9, "PLANTA - SALA SCD PLAZA EGAÑA", ha='center', va='top', fontsize=20, fontweight='bold', color="#cccccc")
        ax.text(0, -radio - 13, "Escala 1:50  •  Geometría Radial  •  Simétrica", ha='center', va='top', fontsize=12, color="#666666")

        # PADDING MUY GRANDE → zoom nunca recorta
        full_xlim = (-r_max * 2.35, r_max * 2.35)
        full_ylim = (-radio - 90, p_tot + r_max + 90)

        if set_full_limits:
            ax.set_xlim(full_xlim)
            ax.set_ylim(full_ylim)

        return full_xlim, full_ylim

    def _dibujar_paredes(self, ax, radio, y_empty, ang_max, wireframe=False, ancho=None, p_rec=None):
        r_fin = radio + self.dist_fila1.get() + (self.cant_filas.get()-1)*self.huella.get() + self.dist_back_wall.get()
        if self.incluir_balcon.get():
            r_fin += self.dist_balcon.get() + (self.cant_filas_balcon.get()-1)*self.huella.get() + 2
        r_in = radio
        lw = self.wall_thickness.get() * 12 if not wireframe else 4

        for signo in [1, -1]:
            x1 = r_in * math.sin(signo * ang_max)
            y1 = y_empty + r_in * math.cos(signo * ang_max)
            x2 = r_fin * math.sin(signo * ang_max)
            y2 = y_empty + r_fin * math.cos(signo * ang_max)
            ax.plot([x1, x2], [y1, y2], color=self.COLOR_PARED, linewidth=lw)

        theta = np.linspace(-ang_max, ang_max, 70)
        xf = r_fin * np.sin(theta)
        yf = y_empty + r_fin * np.cos(theta)
        ax.plot(xf, yf, color=self.COLOR_PARED, linewidth=lw * 0.85)

        if ancho is not None and p_rec is not None:
            self._dibujar_pasillos_backstage(ax, ancho, p_rec, self.pasillo_backstage_width.get())

    # ==================== MÉTODOS RESTANTES (sin cambios) ====================
    def crear_seccion(self, parent, titulo):
        ctk.CTkLabel(parent, text=titulo, font=("Helvetica", 16, "bold"), text_color="#aaaaaa").pack(anchor="w", padx=20, pady=(25, 8))

    def crear_slider_con_entrada(self, container, texto, variable, min_val, max_val, es_entero=False, extra_command=None):
        frame = ctk.CTkFrame(container, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(frame, text=texto, font=("Helvetica", 13)).pack(anchor="w", pady=(0, 4))
        subframe = ctk.CTkFrame(frame, fg_color="transparent")
        subframe.pack(fill="x")
        entry = ctk.CTkEntry(subframe, width=72, font=("Consolas", 13), justify="center")
        entry.pack(side="right", padx=(8, 0))

        def set_entry(val):
            entry.delete(0, "end")
            entry.insert(0, str(int(val)) if es_entero else f"{float(val):.2f}")

        def al_mover(val):
            if es_entero:
                valor = int(round(float(val)))
                variable.set(valor)
            else:
                variable.set(float(val))
            set_entry(variable.get())
            self.actualizar_vista()
            if extra_command: extra_command()

        kwargs = {"from_": min_val, "to": max_val, "variable": variable, "command": al_mover, "height": 22}
        if es_entero:
            kwargs["number_of_steps"] = int(max_val - min_val + 1)
        slider = ctk.CTkSlider(subframe, **kwargs)
        slider.pack(side="right", fill="x", expand=True, padx=12)

        def on_entry(event=None):
            try:
                val = int(entry.get()) if es_entero else float(entry.get())
                variable.set(max(min_val, min(max_val, val)))
                self.actualizar_vista()
            except:
                set_entry(variable.get())
        entry.bind("<Return>", on_entry)
        entry.bind("<FocusOut>", on_entry)
        set_entry(variable.get())

    def _dibujar_butacas_principales(self, ax, radio, y_empty, draw=True, fill_enabled=True):
        # (código idéntico a versiones anteriores - alineación radial intacta)
        cant_f = self.cant_filas.get()
        total = 0
        last_n_cen = self.c_f1.get()
        last_n_lat = self.l_f1.get()
        ang_max = math.radians(40)
        ang_cen_last = ang_pasillo_last = ang_lat_last = 0.0

        r_last = radio + self.dist_fila1.get() + (cant_f - 1) * self.huella.get()
        if self.usar_config_manual.get() and len(self.fila_config) == cant_f:
            n_cen_last = self.fila_config[-1]["cen"].get()
            n_lat_last = self.fila_config[-1]["lat"].get()
        else:
            n_cen_last = self.c_ff.get()
            n_lat_last = self.l_ff.get()

        ang_cen_last = (n_cen_last * self.ancho_butaca.get()) / r_last
        ang_pasillo_last = self.ancho_pasillo.get() / r_last
        ang_lat_last = (n_lat_last * self.ancho_butaca.get()) / r_last
        ang_max = (ang_cen_last / 2) + ang_pasillo_last + ang_lat_last + math.radians(self.wall_margin_deg.get())

        for f in range(cant_f):
            r_fila = radio + self.dist_fila1.get() + f * self.huella.get()
            if self.usar_config_manual.get() and len(self.fila_config) == cant_f and not self.align_radial.get():
                n_cen = self.fila_config[f]["cen"].get()
                n_lat = self.fila_config[f]["lat"].get()
            else:
                n_cen = round(ang_cen_last * r_fila / self.ancho_butaca.get())
                n_lat = round(ang_lat_last * r_fila / self.ancho_butaca.get())

            last_n_cen = n_cen
            last_n_lat = n_lat
            total += n_cen + 2 * n_lat

            ang_cen_total = (n_cen * self.ancho_butaca.get()) / r_fila
            ang_pasillo = self.ancho_pasillo.get() / r_fila if not self.align_radial.get() else ang_pasillo_last
            ang_lat_total = (n_lat * self.ancho_butaca.get()) / r_fila

            if draw:
                self._dibujar_bloque(ax, r_fila, y_empty, n_cen, -ang_cen_total/2, ang_cen_total, self.COLOR_BUTACA_PRINCIPAL, fill_enabled)
                self._dibujar_bloque(ax, r_fila, y_empty, n_lat, ang_cen_total/2 + ang_pasillo, ang_lat_total, self.COLOR_BUTACA_PRINCIPAL, fill_enabled)
                self._dibujar_bloque(ax, r_fila, y_empty, n_lat, -(ang_cen_total/2 + ang_pasillo + ang_lat_total), ang_lat_total, self.COLOR_BUTACA_PRINCIPAL, fill_enabled)

                if self.show_labels.get():
                    ang_left = -(ang_cen_total/2) - ang_pasillo - ang_lat_total
                    lx = r_fila * math.sin(ang_left)
                    ly = y_empty + r_fila * math.cos(ang_left)
                    ax.text(lx - 1.2, ly, f"F{f+1}", color="#aaaaaa", fontsize=9.5, ha='right', va='center', fontweight='bold')

        if draw and self.align_radial.get():
            r_start = radio + self.dist_fila1.get()
            r_end = radio + self.dist_fila1.get() + (cant_f - 1) * self.huella.get() + 12
            for signo in [1, -1]:
                self._dibujar_linea_radial(ax, y_empty, r_start, r_end, signo * (ang_cen_last / 2))
                self._dibujar_linea_radial(ax, y_empty, r_start, r_end, signo * (ang_cen_last / 2 + ang_pasillo_last))

        return total, last_n_cen, last_n_lat, ang_max, ang_cen_last, ang_pasillo_last, ang_lat_last

    def _dibujar_balcon(self, ax, radio, y_empty, last_n_cen, last_n_lat, ang_max, ang_cen_last, ang_pasillo_last, ang_lat_last, draw=True, fill_enabled=True, wireframe=False):
        r_inicio = radio + self.dist_fila1.get() + (self.cant_filas.get()-1)*self.huella.get() + self.dist_balcon.get()
        total = 0
        cant_b = self.cant_filas_balcon.get()
        for fb in range(cant_b):
            r_fila = r_inicio + fb * self.huella.get()
            if self.usar_config_manual_balcon.get() and len(self.balcon_fila_config) == cant_b:
                n_cen = self.balcon_fila_config[fb]["cen"].get()
                n_lat = self.balcon_fila_config[fb]["lat"].get()
            else:
                n_cen = round(ang_cen_last * r_fila / self.ancho_butaca.get())
                n_lat = round(ang_lat_last * r_fila / self.ancho_butaca.get())
            total += n_cen + 2 * n_lat
            ang_cen_total = (n_cen * self.ancho_butaca.get()) / r_fila
            ang_pasillo = ang_pasillo_last
            ang_lat_total = (n_lat * self.ancho_butaca.get()) / r_fila
            if draw:
                self._dibujar_bloque(ax, r_fila, y_empty, n_cen, -ang_cen_total/2, ang_cen_total, self.COLOR_BUTACA_BALCON, fill_enabled)
                self._dibujar_bloque(ax, r_fila, y_empty, n_lat, ang_cen_total/2 + ang_pasillo, ang_lat_total, self.COLOR_BUTACA_BALCON, fill_enabled)
                self._dibujar_bloque(ax, r_fila, y_empty, n_lat, -(ang_cen_total/2 + ang_pasillo + ang_lat_total), ang_lat_total, self.COLOR_BUTACA_BALCON, fill_enabled)
                if self.show_labels.get():
                    ang_left = -(ang_cen_total/2) - ang_pasillo - ang_lat_total
                    lx = r_fila * math.sin(ang_left)
                    ly = y_empty + r_fila * math.cos(ang_left)
                    ax.text(lx - 1.2, ly, f"B{fb+1}", color="#aaaaaa", fontsize=9.5, ha='right', va='center', fontweight='bold')
        r_bar = r_inicio - 0.4
        theta = np.linspace(-ang_max, ang_max, 80)
        xb = r_bar * np.sin(theta)
        yb = y_empty + r_bar * np.cos(theta)
        ax.plot(xb, yb, color="#cccccc", linewidth=6 if not wireframe else 4)
        return total

    def _dibujar_linea_radial(self, ax, y_empty: float, r_start: float, r_end: float, ang: float):
        x1 = r_start * math.sin(ang)
        y1 = y_empty + r_start * math.cos(ang)
        x2 = r_end * math.sin(ang)
        y2 = y_empty + r_end * math.cos(ang)
        ax.plot([x1, x2], [y1, y2], color=self.COLOR_PASILLO, linewidth=1.8, alpha=0.7, linestyle='--')

    def _dibujar_bloque(self, ax, r_fila, y_empty, num, ang_inicio, ang_total, color, fill_enabled=True):
        if num <= 0: return
        paso = ang_total / num if num > 1 else 0
        for i in range(num):
            ang = ang_inicio + i * paso + paso / 2
            ax_pos = r_fila * math.sin(ang)
            ay_pos = y_empty + r_fila * math.cos(ang)
            ux_rad = math.sin(ang)
            uy_rad = math.cos(ang)
            ux_tan = math.cos(ang)
            uy_tan = -math.sin(ang)
            w = self.ancho_butaca.get()
            d = 0.48
            hw = w / 2
            hd = d / 2
            pts = [(ax_pos - hd*ux_rad - hw*ux_tan, ay_pos - hd*uy_rad - hw*uy_tan),
                   (ax_pos - hd*ux_rad + hw*ux_tan, ay_pos - hd*uy_rad + hw*uy_tan),
                   (ax_pos + hd*ux_rad + hw*ux_tan, ay_pos + hd*uy_rad + hw*uy_tan),
                   (ax_pos + hd*ux_rad - hw*ux_tan, ay_pos + hd*uy_rad - hw*uy_tan)]
            patch = MplPolygon(pts, closed=True, facecolor=color if fill_enabled else "none", edgecolor="#0f1c33", linewidth=2.2 if not fill_enabled else 1.2)
            ax.add_patch(patch)
            if fill_enabled:
                hw_inner = hw * 0.78
                hd_inner = hd * 0.68
                pts_inner = [(ax_pos - hd_inner*ux_rad - hw_inner*ux_tan, ay_pos - hd_inner*uy_rad - hw_inner*uy_tan),
                             (ax_pos - hd_inner*ux_rad + hw_inner*ux_tan, ay_pos - hd_inner*uy_rad + hw_inner*uy_tan),
                             (ax_pos + hd_inner*ux_rad + hw_inner*ux_tan, ay_pos + hd_inner*uy_rad + hw_inner*uy_tan),
                             (ax_pos + hd_inner*ux_rad - hw_inner*ux_tan, ay_pos + hd_inner*uy_rad - hw_inner*uy_tan)]
                inner_patch = MplPolygon(pts_inner, closed=True, facecolor="#a00f2a", edgecolor="#111111", linewidth=0.8)
                ax.add_patch(inner_patch)

    def _dibujar_medidas(self, ax, radio, y_empty, ancho, p_rec, r_max, sagita, ang_max):
        ax.annotate("", xy=(-ancho/2, p_rec + 1.0), xytext=(ancho/2, p_rec + 1.0), arrowprops=dict(arrowstyle="<->", color=self.COLOR_MEDIDAS, lw=1.5))
        ax.text(0, p_rec + 1.6, f"{ancho:.1f} m", ha='center', fontsize=11, color=self.COLOR_MEDIDAS, fontweight="bold")
        ax.annotate("", xy=(ancho/2 + 0.8, 0), xytext=(ancho/2 + 0.8, p_rec), arrowprops=dict(arrowstyle="<->", color=self.COLOR_MEDIDAS, lw=1.5))
        ax.text(ancho/2 + 1.6, p_rec/2, f"{p_rec:.1f} m", rotation=90, fontsize=11, color=self.COLOR_MEDIDAS, fontweight="bold", va='center')
        ax.annotate("", xy=(ancho/2 + 2.2, 0), xytext=(ancho/2 + 2.2, p_rec + sagita), arrowprops=dict(arrowstyle="<->", color=self.COLOR_MEDIDAS, lw=1.5))
        ax.text(ancho/2 + 3.0, (p_rec + sagita)/2, f"{p_rec + sagita:.1f} m", rotation=90, fontsize=11, color=self.COLOR_MEDIDAS, fontweight="bold", va='center')
        wall_len = r_max - radio * 0.82
        ax.annotate("", xy=(-r_max * 0.95, y_empty + radio * 0.4), xytext=(-r_max * 0.95, y_empty + r_max), arrowprops=dict(arrowstyle="<->", color="#d4b78f", lw=1.5))
        ax.text(-r_max * 1.05, y_empty + radio * 0.8, f"{wall_len:.1f} m", rotation=90, fontsize=11, color="#d4b78f", fontweight="bold", va='center')
        r_ult = radio + self.dist_fila1.get() + (self.cant_filas.get()-1) * self.huella.get()
        ancho_total = 2 * r_ult * math.sin(ang_max)
        ax.annotate("", xy=(-r_ult * math.sin(ang_max), y_empty + r_ult * math.cos(ang_max)), xytext=(r_ult * math.sin(ang_max), y_empty + r_ult * math.cos(ang_max)), arrowprops=dict(arrowstyle="<->", color=self.COLOR_MEDIDAS, lw=1.5))
        ax.text(0, y_empty + r_ult * math.cos(ang_max) + 1.2, f"{ancho_total:.1f} m", ha='center', fontsize=11, color=self.COLOR_MEDIDAS, fontweight="bold")

    def generar_desde_progresion(self):
        self.usar_config_manual.set(True)
        self.refresh_fila_table()
        cant = self.cant_filas.get()
        for f in range(cant):
            ratio = f / (cant - 1) if cant > 1 else 0
            n_cen = int(self.c_f1.get() + (self.c_ff.get() - self.c_f1.get()) * ratio)
            n_lat = int(self.l_f1.get() + (self.l_ff.get() - self.l_f1.get()) * ratio)
            self.fila_config[f]["cen"].set(n_cen)
            self.fila_config[f]["lat"].set(n_lat)
        self.actualizar_vista()

    def reset_view(self):
        if self.current_full_xlim and self.current_full_ylim:
            self.ax.set_xlim(self.current_full_xlim)
            self.ax.set_ylim(self.current_full_ylim)
            self.canvas_mat.draw()

    def exportar(self, formato, outline_only=False):
        try:
            fname = f"plano_scd_egaña{'_contornos' if outline_only else ''}.{formato}"
            temp_fig = Figure(figsize=(18.5, 12.8), dpi=300 if formato == "png" else 150)
            temp_ax = temp_fig.add_subplot(111)
            temp_ax.set_facecolor("#1a1d24" if not outline_only else "#0f1218")
            self._draw_to_ax(temp_ax, walls_only=outline_only, wireframe=outline_only, set_full_limits=True)
            temp_fig.savefig(fname, dpi=300 if formato == "png" else None, bbox_inches='tight', transparent=outline_only)
            plt.close(temp_fig)
            messagebox.showinfo("¡Exportado!", f"✅ Guardado como:\n{fname}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def actualizar_vista(self, event=None):
        try:
            old_xlim = self.ax.get_xlim()
            old_ylim = self.ax.get_ylim()
        except:
            old_xlim = None
            old_ylim = None

        self.ax.clear()
        walls_only = self.walls_only_mode.get()
        full_xlim, full_ylim = self._draw_to_ax(self.ax, walls_only=walls_only, wireframe=False, set_full_limits=False)

        self.current_full_xlim = full_xlim
        self.current_full_ylim = full_ylim

        if old_xlim is None or old_ylim is None:
            self.ax.set_xlim(full_xlim)
            self.ax.set_ylim(full_ylim)
        else:
            if (abs(old_xlim[0] - full_xlim[0]) < 0.12 * (full_xlim[1] - full_xlim[0]) and
                abs(old_xlim[1] - full_xlim[1]) < 0.12 * (full_xlim[1] - full_xlim[0])):
                self.ax.set_xlim(full_xlim)
                self.ax.set_ylim(full_ylim)
            else:
                self.ax.set_xlim(old_xlim)
                self.ax.set_ylim(old_ylim)
        self.canvas_mat.draw()

    def _on_scroll(self, event):
        if event.inaxes != self.ax: return
        factor = 0.85 if event.button == 'up' else 1.18
        xdata, ydata = event.xdata, event.ydata
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.set_xlim([xdata + factor * (x - xdata) for x in xlim])
        self.ax.set_ylim([ydata + factor * (y - ydata) for y in ylim])
        self.canvas_mat.draw_idle()

    def _on_key_press(self, event):
        if event.key == ' ':
            self.toolbar.pan()
            self.canvas_mat.draw_idle()


if __name__ == "__main__":
    app = PlanoTeatroVisualizer()
    app.mainloop()
