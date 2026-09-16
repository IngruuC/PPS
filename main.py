"""
PPS - CAETI (UAI)
Punto de entrada de la aplicación.

Flujo:
 1. Se inicializa la base de datos (crea tablas y admin si hace falta).
 2. Se muestra la pantalla de Login.
 3. Si el login es correcto, se cierra el login y se abre la Ventana Principal.
 4. Si el usuario cierra sesión desde la Ventana Principal, se vuelve a mostrar el Login.
 5. Si el usuario cierra la ventana (la X) en cualquier punto, el programa termina.
"""

import os
import sys
import customtkinter as ctk
from PIL import Image

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.database import inicializar_bd, existe_algun_usuario, crear_usuario_administrador
from modules.auth import autenticar_usuario
from modules.app_principal import VentanaPrincipal
from utils import config

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")  # se sobreescribe con nuestros propios colores


class VentanaLogin(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(config.NOMBRE_APP)
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(fg_color=config.COLOR_FONDO)

        self.usuario_autenticado = None  # acá se guarda el usuario si el login es correcto

        self._construir_interfaz()

    def _construir_interfaz(self):
        tarjeta = ctk.CTkFrame(
            self,
            fg_color=config.COLOR_FONDO_TARJETA,
            corner_radius=12,
            border_width=1,
            border_color=config.COLOR_GRIS_CLARO,
        )
        tarjeta.pack(expand=True, fill="both", padx=30, pady=30)

        if os.path.exists(config.LOGO_PATH):
            imagen = Image.open(config.LOGO_PATH)
            logo_ctk = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(120, 120))
            ctk.CTkLabel(tarjeta, image=logo_ctk, text="").pack(pady=(30, 10))
        else:
            ctk.CTkLabel(
                tarjeta, text="UAI",
                font=(config.FUENTE_PRINCIPAL, 34, "bold"),
                text_color=config.COLOR_BORDO,
            ).pack(pady=(40, 10))

        ctk.CTkLabel(
            tarjeta, text=config.NOMBRE_APP,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TITULO, "bold"),
            text_color=config.COLOR_TEXTO,
        ).pack(pady=(0, 2))

        ctk.CTkLabel(
            tarjeta, text=config.SUBTITULO_APP,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO),
            text_color=config.COLOR_GRIS,
        ).pack(pady=(0, 25))

        self.entrada_usuario = ctk.CTkEntry(
            tarjeta, placeholder_text="Usuario",
            width=260, height=38,
            border_color=config.COLOR_GRIS_CLARO,
            fg_color=config.COLOR_FONDO,
            text_color=config.COLOR_TEXTO,
        )
        self.entrada_usuario.pack(pady=(0, 12))

        self.entrada_password = ctk.CTkEntry(
            tarjeta, placeholder_text="Contraseña", show="•",
            width=260, height=38,
            border_color=config.COLOR_GRIS_CLARO,
            fg_color=config.COLOR_FONDO,
            text_color=config.COLOR_TEXTO,
        )
        self.entrada_password.pack(pady=(0, 8))

        self.label_error = ctk.CTkLabel(
            tarjeta, text="", text_color=config.COLOR_ALERTA,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO),
        )
        self.label_error.pack(pady=(0, 8))

        ctk.CTkButton(
            tarjeta, text="Ingresar",
            width=260, height=40,
            fg_color=config.COLOR_BORDO,
            hover_color=config.COLOR_BORDO_OSCURO,
            text_color=config.COLOR_TEXTO_CLARO,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO, "bold"),
            command=self._intentar_login,
        ).pack(pady=(10, 20))

        self.entrada_usuario.bind("<Return>", lambda evento: self._intentar_login())
        self.entrada_password.bind("<Return>", lambda evento: self._intentar_login())

        ctk.CTkLabel(
            tarjeta, text="CAETI - Centro de Altos Estudios en Tecnología Informática",
            font=(config.FUENTE_PRINCIPAL, 10),
            text_color=config.COLOR_GRIS,
        ).pack(side="bottom", pady=(0, 15))

    def _intentar_login(self):
        nombre_usuario = self.entrada_usuario.get().strip()
        password = self.entrada_password.get()

        if not nombre_usuario or not password:
            self.label_error.configure(text="Completá usuario y contraseña.", text_color=config.COLOR_ALERTA)
            return

        usuario = autenticar_usuario(nombre_usuario, password)

        if usuario is None:
            self.label_error.configure(text="Usuario o contraseña incorrectos.", text_color=config.COLOR_ALERTA)
            self.entrada_password.delete(0, "end")
            return

        self.usuario_autenticado = usuario
        self.label_error.configure(
            text=f"¡Bienvenido, {usuario['nombre_completo']}!",
            text_color=config.COLOR_EXITO,
        )
        # Esperamos un instante para que se vea el mensaje y cerramos el login,
        # el flujo principal (más abajo) se encarga de abrir la ventana principal.
        self.after(500, self.destroy)


class VentanaPrimerInicio(ctk.CTk):
    """
    Se muestra una única vez, cuando la base de datos todavía no tiene
    ningún usuario cargado, para crear el primer administrador del sistema.
    """

    def __init__(self):
        super().__init__()

        self.title(config.NOMBRE_APP)
        self.geometry("420x600")
        self.resizable(False, False)
        self.configure(fg_color=config.COLOR_FONDO)

        self.administrador_creado = False  # se pone en True si se crea el admin con éxito

        self._construir_interfaz()

    def _construir_interfaz(self):
        tarjeta = ctk.CTkFrame(
            self,
            fg_color=config.COLOR_FONDO_TARJETA,
            corner_radius=12,
            border_width=1,
            border_color=config.COLOR_GRIS_CLARO,
        )
        tarjeta.pack(expand=True, fill="both", padx=30, pady=30)

        if os.path.exists(config.LOGO_PATH):
            imagen = Image.open(config.LOGO_PATH)
            logo_ctk = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(90, 90))
            ctk.CTkLabel(tarjeta, image=logo_ctk, text="").pack(pady=(24, 8))
        else:
            ctk.CTkLabel(
                tarjeta, text="UAI",
                font=(config.FUENTE_PRINCIPAL, 30, "bold"),
                text_color=config.COLOR_BORDO,
            ).pack(pady=(30, 8))

        ctk.CTkLabel(
            tarjeta, text="Configuración inicial",
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TITULO, "bold"),
            text_color=config.COLOR_TEXTO,
        ).pack(pady=(0, 2))

        ctk.CTkLabel(
            tarjeta, text="Todavía no hay ningún usuario cargado.\nCreá la cuenta de administrador para continuar.",
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO),
            text_color=config.COLOR_GRIS,
            justify="center",
        ).pack(pady=(0, 20))

        self.entrada_usuario = ctk.CTkEntry(
            tarjeta, placeholder_text="Usuario",
            width=260, height=38,
            border_color=config.COLOR_GRIS_CLARO,
            fg_color=config.COLOR_FONDO,
            text_color=config.COLOR_TEXTO,
        )
        self.entrada_usuario.pack(pady=(0, 12))

        self.entrada_nombre_completo = ctk.CTkEntry(
            tarjeta, placeholder_text="Nombre completo",
            width=260, height=38,
            border_color=config.COLOR_GRIS_CLARO,
            fg_color=config.COLOR_FONDO,
            text_color=config.COLOR_TEXTO,
        )
        self.entrada_nombre_completo.pack(pady=(0, 12))

        self.entrada_password = ctk.CTkEntry(
            tarjeta, placeholder_text="Contraseña", show="•",
            width=260, height=38,
            border_color=config.COLOR_GRIS_CLARO,
            fg_color=config.COLOR_FONDO,
            text_color=config.COLOR_TEXTO,
        )
        self.entrada_password.pack(pady=(0, 12))

        self.entrada_repetir_password = ctk.CTkEntry(
            tarjeta, placeholder_text="Repetir contraseña", show="•",
            width=260, height=38,
            border_color=config.COLOR_GRIS_CLARO,
            fg_color=config.COLOR_FONDO,
            text_color=config.COLOR_TEXTO,
        )
        self.entrada_repetir_password.pack(pady=(0, 8))

        self.label_error = ctk.CTkLabel(
            tarjeta, text="", text_color=config.COLOR_ALERTA,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO),
            wraplength=260, justify="center",
        )
        self.label_error.pack(pady=(0, 8))

        ctk.CTkButton(
            tarjeta, text="Crear administrador",
            width=260, height=40,
            fg_color=config.COLOR_BORDO,
            hover_color=config.COLOR_BORDO_OSCURO,
            text_color=config.COLOR_TEXTO_CLARO,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO, "bold"),
            command=self._intentar_crear_administrador,
        ).pack(pady=(10, 20))

        self.entrada_repetir_password.bind("<Return>", lambda evento: self._intentar_crear_administrador())

        ctk.CTkLabel(
            tarjeta, text="CAETI - Centro de Altos Estudios en Tecnología Informática",
            font=(config.FUENTE_PRINCIPAL, 10),
            text_color=config.COLOR_GRIS,
        ).pack(side="bottom", pady=(0, 15))

    def _intentar_crear_administrador(self):
        nombre_usuario = self.entrada_usuario.get().strip()
        nombre_completo = self.entrada_nombre_completo.get().strip()
        password = self.entrada_password.get()
        repetir_password = self.entrada_repetir_password.get()

        if not nombre_usuario or not nombre_completo or not password or not repetir_password:
            self.label_error.configure(text="Completá todos los campos.", text_color=config.COLOR_ALERTA)
            return

        if password != repetir_password:
            self.label_error.configure(text="Las contraseñas no coinciden.", text_color=config.COLOR_ALERTA)
            return

        if len(password) < 8:
            self.label_error.configure(
                text="La contraseña debe tener al menos 8 caracteres.",
                text_color=config.COLOR_ALERTA,
            )
            return

        crear_usuario_administrador(nombre_usuario, password, nombre_completo)

        self.administrador_creado = True
        self.label_error.configure(text="¡Administrador creado con éxito!", text_color=config.COLOR_EXITO)
        self.after(500, self.destroy)


def main():
    inicializar_bd()  # se asegura de que la base y las tablas existan

    if not existe_algun_usuario():
        primer_inicio = VentanaPrimerInicio()
        primer_inicio.mainloop()

        if not primer_inicio.administrador_creado:
            return  # se cerró la ventana con la X sin crear el administrador: termina el programa

    # Este ciclo permite volver a la pantalla de login si el usuario cierra sesión,
    # y termina el programa si cierra la ventana con la X en cualquier punto.
    while True:
        login = VentanaLogin()
        login.mainloop()

        usuario = login.usuario_autenticado
        if usuario is None:
            break  # se cerró la ventana sin loguearse: termina el programa

        app = VentanaPrincipal(usuario)
        app.mainloop()

        if not app.cerrar_sesion_solicitado:
            break  # se cerró la ventana principal con la X: termina el programa
        # si pidió "Cerrar sesión", el ciclo vuelve a mostrar el login


if __name__ == "__main__":
    main()