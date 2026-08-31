"""
PPS - CAETI (UAI)
Ventana principal del sistema, con menú lateral (sidebar) y área de contenido.

El menú lateral solo muestra los módulos a los que el usuario logueado
tiene permiso de "ver" (según su grupo). El módulo de Seguridad solo lo ve
quien tenga permiso sobre 'seguridad'.
"""

import os
import sys
import customtkinter as ctk
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import config
from modules.auth import tiene_permiso
from modules.inventario import InventarioFrame
from modules.personas import PersonasFrame
from modules.prestamos import PrestamosFrame


class VentanaPrincipal(ctk.CTk):
    def __init__(self, usuario):
        super().__init__()

        self.usuario = usuario  # diccionario con datos y permisos del usuario logueado
        self.cerrar_sesion_solicitado = False  # True si el usuario apretó "Cerrar sesión"

        self.title(config.NOMBRE_APP)
        self.geometry("1100x650")
        self.minsize(950, 600)
        self.configure(fg_color=config.COLOR_FONDO)

        # Estructura general: sidebar a la izquierda, contenido a la derecha
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construir_sidebar()
        self._construir_area_contenido()

        # Al abrir, mostramos el módulo de Inventario por defecto (si tiene permiso),
        # o el primer módulo disponible para ese usuario.
        self._mostrar_modulo_inicial()

    # ----------------------------------------------------------------
    # SIDEBAR (menú lateral)
    # ----------------------------------------------------------------
    def _construir_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color=config.COLOR_BORDO,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        # Logo chico arriba del sidebar
        if os.path.exists(config.LOGO_PATH):
            imagen = Image.open(config.LOGO_PATH)
            logo_ctk = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(60, 60))
            ctk.CTkLabel(self.sidebar, image=logo_ctk, text="").pack(pady=(25, 5))
        else:
            ctk.CTkLabel(
                self.sidebar, text="UAI",
                font=(config.FUENTE_PRINCIPAL, 24, "bold"),
                text_color=config.COLOR_TEXTO_CLARO,
            ).pack(pady=(25, 5))

        ctk.CTkLabel(
            self.sidebar, text="CAETI",
            font=(config.FUENTE_PRINCIPAL, 14, "bold"),
            text_color=config.COLOR_TEXTO_CLARO,
        ).pack(pady=(0, 25))

        # Botones de navegación, solo si el usuario tiene permiso de "ver" ese módulo
        self.botones_menu = {}

        self._agregar_boton_menu("inventario", "📦  Inventario", self.mostrar_inventario)
        self._agregar_boton_menu("personas", "👥  Personas", self.mostrar_personas)
        self._agregar_boton_menu("prestamos", "🔄  Préstamos", self.mostrar_prestamos)
        self._agregar_boton_menu("seguridad", "🔒  Seguridad", self.mostrar_seguridad)

        # Espacio flexible para empujar el botón de cerrar sesión hacia abajo
        ctk.CTkLabel(self.sidebar, text="", fg_color="transparent").pack(expand=True, fill="both")

        # Datos del usuario logueado + botón cerrar sesión, abajo del todo
        ctk.CTkFrame(self.sidebar, height=1, fg_color=config.COLOR_BORDO_OSCURO).pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            self.sidebar, text=self.usuario["nombre_completo"],
            font=(config.FUENTE_PRINCIPAL, 12, "bold"),
            text_color=config.COLOR_TEXTO_CLARO,
            wraplength=190, justify="left",
        ).pack(padx=15, anchor="w")

        ctk.CTkLabel(
            self.sidebar, text=self.usuario["nombre_grupo"],
            font=(config.FUENTE_PRINCIPAL, 11),
            text_color=config.COLOR_GRIS_CLARO,
        ).pack(padx=15, anchor="w", pady=(0, 12))

        ctk.CTkButton(
            self.sidebar, text="Cerrar sesión",
            fg_color="transparent",
            hover_color=config.COLOR_BORDO_OSCURO,
            text_color=config.COLOR_TEXTO_CLARO,
            border_width=1, border_color=config.COLOR_TEXTO_CLARO,
            height=32,
            command=self._cerrar_sesion,
        ).pack(padx=15, pady=(0, 20), fill="x")

    def _agregar_boton_menu(self, modulo, texto, comando):
        """Agrega un botón al sidebar solo si el usuario tiene permiso de 'ver' ese módulo."""
        if not tiene_permiso(self.usuario, modulo, "ver"):
            return

        boton = ctk.CTkButton(
            self.sidebar, text=texto,
            anchor="w",
            fg_color="transparent",
            hover_color=config.COLOR_BORDO_OSCURO,
            text_color=config.COLOR_TEXTO_CLARO,
            font=(config.FUENTE_PRINCIPAL, 13),
            height=40,
            corner_radius=6,
            command=comando,
        )
        boton.pack(fill="x", padx=12, pady=3)
        self.botones_menu[modulo] = boton

    def _marcar_boton_activo(self, modulo):
        """Resalta visualmente el botón del módulo que se está mostrando."""
        for nombre_modulo, boton in self.botones_menu.items():
            if nombre_modulo == modulo:
                boton.configure(fg_color=config.COLOR_BORDO_OSCURO)
            else:
                boton.configure(fg_color="transparent")

    # ----------------------------------------------------------------
    # ÁREA DE CONTENIDO (donde se muestra cada módulo)
    # ----------------------------------------------------------------
    def _construir_area_contenido(self):
        contenedor = ctk.CTkFrame(self, fg_color=config.COLOR_FONDO)
        contenedor.grid(row=0, column=1, sticky="nsew")
        contenedor.grid_rowconfigure(1, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        # Header superior con el título del módulo actual
        self.header = ctk.CTkFrame(contenedor, height=60, fg_color=config.COLOR_FONDO_TARJETA, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)

        self.label_titulo_modulo = ctk.CTkLabel(
            self.header, text="",
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_SUBTITULO, "bold"),
            text_color=config.COLOR_TEXTO,
        )
        self.label_titulo_modulo.pack(side="left", padx=25, pady=15)

        # Área donde cada módulo va a dibujar su contenido (tablas, filtros, etc.)
        self.area_contenido = ctk.CTkFrame(contenedor, fg_color=config.COLOR_FONDO)
        self.area_contenido.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

    def _limpiar_area_contenido(self):
        """Borra todo lo que esté dibujado en el área de contenido antes de mostrar otro módulo."""
        for widget in self.area_contenido.winfo_children():
            widget.destroy()

    def _mostrar_placeholder(self, titulo, mensaje):
        """
        Muestra un mensaje temporal para módulos que todavía no están construidos.
        Esto se va a ir reemplazando en las próximas partes por las tablas reales.
        """
        self._limpiar_area_contenido()
        self.label_titulo_modulo.configure(text=titulo)

        ctk.CTkLabel(
            self.area_contenido, text=mensaje,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO),
            text_color=config.COLOR_GRIS,
        ).pack(expand=True)

    # ----------------------------------------------------------------
    # NAVEGACIÓN ENTRE MÓDULOS (por ahora placeholders, se completan después)
    # ----------------------------------------------------------------
    
    def mostrar_inventario(self):
        self._marcar_boton_activo("inventario")
        self._limpiar_area_contenido()
        self.label_titulo_modulo.configure(text="Inventario")
        frame = InventarioFrame(self.area_contenido, self.usuario)
        frame.pack(fill="both", expand=True)

    def mostrar_personas(self):
        self._marcar_boton_activo("personas")
        self._limpiar_area_contenido()
        self.label_titulo_modulo.configure(text="Personas")
        frame = PersonasFrame(self.area_contenido, self.usuario)
        frame.pack(fill="both", expand=True)

    def mostrar_prestamos(self):
        self._marcar_boton_activo("prestamos")
        self._limpiar_area_contenido()
        self.label_titulo_modulo.configure(text="Préstamos")
        frame = PrestamosFrame(self.area_contenido, self.usuario)
        frame.pack(fill="both", expand=True)

    def mostrar_seguridad(self):
        self._marcar_boton_activo("seguridad")
        self._mostrar_placeholder("Seguridad", "El módulo de Seguridad (usuarios, grupos, permisos y auditoría) se construye más adelante.")

    def _mostrar_modulo_inicial(self):
        """Muestra el primer módulo disponible según los permisos del usuario."""
        orden_modulos = [
            ("inventario", self.mostrar_inventario),
            ("personas", self.mostrar_personas),
            ("prestamos", self.mostrar_prestamos),
            ("seguridad", self.mostrar_seguridad),
        ]
        for modulo, funcion in orden_modulos:
            if modulo in self.botones_menu:
                funcion()
                return

        # Si no tiene permiso de ver ningún módulo (caso raro), mostramos un aviso
        self.label_titulo_modulo.configure(text="Sin acceso")
        ctk.CTkLabel(
            self.area_contenido,
            text="Tu usuario no tiene permisos asignados para ver ningún módulo.\nConsultá con el administrador.",
            text_color=config.COLOR_ALERTA,
        ).pack(expand=True)

    # ----------------------------------------------------------------
    # CERRAR SESIÓN
    # ----------------------------------------------------------------
    def _cerrar_sesion(self):
        self.cerrar_sesion_solicitado = True
        self.destroy()