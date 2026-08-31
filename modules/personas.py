"""
PPS - CAETI (UAI)
Módulo Personas: pasantes, laboratoristas, docentes, investigadores, etc.

En vez de eliminar definitivamente a una persona, se la "da de baja"
(activo = 0). Así se conserva el historial de préstamos asociados a ella.
"""

import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import conectar
from utils.auditoria import registrar_auditoria

ROLES_DISPONIBLES = ["Pasante", "Laboratorista", "Docente", "Investigador"]


# ----------------------------------------------------------------
# CAPA DE DATOS
# ----------------------------------------------------------------

def listar_personas(texto_busqueda=None, rol=None, estado=None):
    """
    Devuelve las personas registradas, con filtros opcionales:
      - texto_busqueda: busca en nombre, apellido, dni o email.
      - rol: 'Pasante', 'Laboratorista', 'Docente' o 'Investigador'.
      - estado: True (activos), False (inactivos) o None (todos).
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        consulta = "SELECT * FROM personas WHERE 1=1"
        parametros = []

        if texto_busqueda:
            consulta += " AND (nombre LIKE ? OR apellido LIKE ? OR dni LIKE ? OR email LIKE ?)"
            comodin = f"%{texto_busqueda}%"
            parametros += [comodin, comodin, comodin, comodin]

        if rol:
            consulta += " AND rol = ?"
            parametros.append(rol)

        if estado is not None:
            consulta += " AND activo = ?"
            parametros.append(1 if estado else 0)

        consulta += " ORDER BY apellido, nombre"

        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()


def obtener_persona(id_persona):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM personas WHERE id = ?", (id_persona,))
        return cursor.fetchone()
    finally:
        conexion.close()


def crear_persona(datos, id_usuario):
    """'datos': nombre, apellido, dni, rol, email, telefono, fecha_ingreso, observaciones."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO personas
                (nombre, apellido, dni, rol, email, telefono, fecha_ingreso, observaciones, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                datos["nombre"].strip(),
                datos["apellido"].strip(),
                datos.get("dni", "").strip(),
                datos["rol"],
                datos.get("email", "").strip(),
                datos.get("telefono", "").strip(),
                datos.get("fecha_ingreso") or None,
                datos.get("observaciones", "").strip(),
            )
        )
        conexion.commit()
        id_nuevo = cursor.lastrowid

        registrar_auditoria(
            id_usuario, "ALTA", "personas",
            f"Se dio de alta a {datos['nombre']} {datos['apellido']} ({datos['rol']})"
        )
        return id_nuevo
    finally:
        conexion.close()


def actualizar_persona(id_persona, datos, id_usuario):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE personas SET
                nombre = ?, apellido = ?, dni = ?, rol = ?,
                email = ?, telefono = ?, fecha_ingreso = ?, observaciones = ?
            WHERE id = ?
            """,
            (
                datos["nombre"].strip(),
                datos["apellido"].strip(),
                datos.get("dni", "").strip(),
                datos["rol"],
                datos.get("email", "").strip(),
                datos.get("telefono", "").strip(),
                datos.get("fecha_ingreso") or None,
                datos.get("observaciones", "").strip(),
                id_persona,
            )
        )
        conexion.commit()

        registrar_auditoria(
            id_usuario, "MODIFICACION", "personas",
            f"Se modificaron los datos de {datos['nombre']} {datos['apellido']}"
        )
    finally:
        conexion.close()


def cambiar_estado_persona(id_persona, nuevo_estado_activo, id_usuario):
    """Da de baja (False) o reactiva (True) a una persona, sin borrar sus datos."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT nombre, apellido FROM personas WHERE id = ?", (id_persona,))
        fila = cursor.fetchone()
        nombre_completo = f"{fila['nombre']} {fila['apellido']}" if fila else f"id {id_persona}"

        cursor.execute(
            "UPDATE personas SET activo = ? WHERE id = ?",
            (1 if nuevo_estado_activo else 0, id_persona)
        )
        conexion.commit()

        accion = "REACTIVACION" if nuevo_estado_activo else "BAJA"
        registrar_auditoria(
            id_usuario, accion, "personas",
            f"Se {'reactivó' if nuevo_estado_activo else 'dio de baja a'} {nombre_completo}"
        )
    finally:
        conexion.close()


def existe_dni(dni, id_persona_excluir=None):
    """Chequea si un DNI ya está registrado en otra persona (si se cargó un DNI)."""
    if not dni or not dni.strip():
        return False
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        if id_persona_excluir:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM personas WHERE dni = ? AND id != ?",
                (dni.strip(), id_persona_excluir)
            )
        else:
            cursor.execute("SELECT COUNT(*) AS total FROM personas WHERE dni = ?", (dni.strip(),))
        return cursor.fetchone()["total"] > 0
    finally:
        conexion.close()


# ==================================================================
# INTERFAZ GRÁFICA DEL MÓDULO PERSONAS
# ==================================================================

import customtkinter as ctk
from tkinter import ttk, messagebox
from utils import config
from modules.auth import tiene_permiso


class PersonasFrame(ctk.CTkFrame):
    """Pantalla del módulo Personas: filtros de búsqueda + tabla."""

    def __init__(self, parent, usuario):
        super().__init__(parent, fg_color=config.COLOR_FONDO)
        self.usuario = usuario
        self.persona_seleccionada_id = None
        self.persona_seleccionada_activa = None

        self._configurar_estilo_tabla()
        self._construir_barra_filtros()
        self._construir_tabla()
        self._construir_barra_acciones()

        self.buscar()

    # ----------------------------------------------------------------
    def _configurar_estilo_tabla(self):
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure(
            "Personas.Treeview",
            background=config.COLOR_FONDO_TARJETA,
            fieldbackground=config.COLOR_FONDO_TARJETA,
            foreground=config.COLOR_TEXTO,
            rowheight=32, borderwidth=0,
            font=(config.FUENTE_PRINCIPAL, 11),
        )
        estilo.configure(
            "Personas.Treeview.Heading",
            background=config.COLOR_BORDO, foreground=config.COLOR_TEXTO_CLARO,
            font=(config.FUENTE_PRINCIPAL, 11, "bold"), borderwidth=0,
        )
        estilo.map(
            "Personas.Treeview",
            background=[("selected", config.COLOR_BORDO)],
            foreground=[("selected", config.COLOR_TEXTO_CLARO)],
        )

    # ----------------------------------------------------------------
    def _construir_barra_filtros(self):
        barra = ctk.CTkFrame(self, fg_color=config.COLOR_FONDO_TARJETA, corner_radius=8)
        barra.pack(fill="x", pady=(0, 15))

        self.entrada_busqueda = ctk.CTkEntry(
            barra, placeholder_text="Buscar por nombre, apellido, DNI o email...",
            width=280, height=34,
        )
        self.entrada_busqueda.pack(side="left", padx=(15, 10), pady=12)
        self.entrada_busqueda.bind("<Return>", lambda evento: self.buscar())

        self.combo_rol = ctk.CTkComboBox(
            barra, values=["Todos los roles"] + ROLES_DISPONIBLES, width=160, height=34
        )
        self.combo_rol.set("Todos los roles")
        self.combo_rol.pack(side="left", padx=(0, 10), pady=12)

        self.combo_estado = ctk.CTkComboBox(
            barra, values=["Todos", "Activos", "Inactivos"], width=130, height=34
        )
        self.combo_estado.set("Activos")
        self.combo_estado.pack(side="left", padx=(0, 10), pady=12)

        ctk.CTkButton(
            barra, text="Buscar", width=90, height=34,
            fg_color=config.COLOR_BORDO, hover_color=config.COLOR_BORDO_OSCURO,
            command=self.buscar,
        ).pack(side="left", padx=(0, 10), pady=12)

        ctk.CTkButton(
            barra, text="Limpiar", width=90, height=34,
            fg_color="transparent", border_width=1,
            border_color=config.COLOR_GRIS, text_color=config.COLOR_TEXTO,
            hover_color=config.COLOR_GRIS_CLARO,
            command=self._limpiar_filtros,
        ).pack(side="left", pady=12)

    # ----------------------------------------------------------------
    def _construir_tabla(self):
        contenedor_tabla = ctk.CTkFrame(self, fg_color=config.COLOR_FONDO_TARJETA, corner_radius=8)
        contenedor_tabla.pack(fill="both", expand=True)

        columnas = ("apellido", "nombre", "dni", "rol", "email", "telefono", "estado")
        self.tabla = ttk.Treeview(
            contenedor_tabla, columns=columnas, show="headings",
            style="Personas.Treeview", selectmode="browse",
        )

        encabezados = {
            "apellido": "Apellido", "nombre": "Nombre", "dni": "DNI", "rol": "Rol",
            "email": "Email", "telefono": "Teléfono", "estado": "Estado",
        }
        anchos = {
            "apellido": 130, "nombre": 130, "dni": 90, "rol": 110,
            "email": 180, "telefono": 110, "estado": 80,
        }
        for columna in columnas:
            self.tabla.heading(columna, text=encabezados[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="w")

        scrollbar = ttk.Scrollbar(contenedor_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scrollbar.set)

        self.tabla.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10, padx=(0, 10))

        self.tabla.bind("<<TreeviewSelect>>", self._al_seleccionar_fila)

    # ----------------------------------------------------------------
    def _construir_barra_acciones(self):
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(15, 0))

        self.label_contador = ctk.CTkLabel(
            barra, text="", text_color=config.COLOR_GRIS,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO),
        )
        self.label_contador.pack(side="left")

        if tiene_permiso(self.usuario, "personas", "eliminar"):
            self.boton_estado = ctk.CTkButton(
                barra, text="Dar de baja", width=150, height=36,
                fg_color=config.COLOR_ALERTA, hover_color=config.COLOR_BORDO_OSCURO,
                state="disabled", command=self._alternar_estado_seleccionado,
            )
            self.boton_estado.pack(side="right", padx=(10, 0))

        if tiene_permiso(self.usuario, "personas", "editar"):
            self.boton_editar = ctk.CTkButton(
                barra, text="Editar seleccionado", width=160, height=36,
                fg_color="transparent", border_width=1,
                border_color=config.COLOR_BORDO, text_color=config.COLOR_BORDO,
                hover_color=config.COLOR_GRIS_CLARO,
                state="disabled", command=self._editar_seleccionado,
            )
            self.boton_editar.pack(side="right", padx=(10, 0))

        if tiene_permiso(self.usuario, "personas", "crear"):
            ctk.CTkButton(
                barra, text="+ Nueva persona", width=150, height=36,
                fg_color=config.COLOR_BORDO, hover_color=config.COLOR_BORDO_OSCURO,
                command=self._nueva_persona,
            ).pack(side="right")

    # ----------------------------------------------------------------
    def buscar(self):
        texto = self.entrada_busqueda.get().strip() or None

        rol = self.combo_rol.get()
        rol = None if rol == "Todos los roles" else rol

        estado_texto = self.combo_estado.get()
        estado = {"Activos": True, "Inactivos": False, "Todos": None}[estado_texto]

        personas = listar_personas(texto_busqueda=texto, rol=rol, estado=estado)
        self._cargar_filas(personas)

    def _limpiar_filtros(self):
        self.entrada_busqueda.delete(0, "end")
        self.combo_rol.set("Todos los roles")
        self.combo_estado.set("Activos")
        self.buscar()

    def _cargar_filas(self, personas):
        self.tabla.delete(*self.tabla.get_children())
        for persona in personas:
            self.tabla.insert(
                "", "end", iid=str(persona["id"]),
                values=(
                    persona["apellido"], persona["nombre"], persona["dni"] or "-",
                    persona["rol"], persona["email"] or "-", persona["telefono"] or "-",
                    "Activo" if persona["activo"] else "Inactivo",
                )
            )
        self.label_contador.configure(text=f"{len(personas)} persona(s) encontrada(s)")
        self._al_seleccionar_fila(None)

    # ----------------------------------------------------------------
    def _al_seleccionar_fila(self, evento):
        seleccion = self.tabla.selection()
        if not seleccion:
            self.persona_seleccionada_id = None
            self.persona_seleccionada_activa = None
        else:
            self.persona_seleccionada_id = int(seleccion[0])
            persona = obtener_persona(self.persona_seleccionada_id)
            self.persona_seleccionada_activa = bool(persona["activo"]) if persona else None

        hay_seleccion = self.persona_seleccionada_id is not None
        if hasattr(self, "boton_editar"):
            self.boton_editar.configure(state="normal" if hay_seleccion else "disabled")
        if hasattr(self, "boton_estado"):
            self.boton_estado.configure(state="normal" if hay_seleccion else "disabled")
            if hay_seleccion:
                texto_boton = "Dar de baja" if self.persona_seleccionada_activa else "Reactivar"
                color = config.COLOR_ALERTA if self.persona_seleccionada_activa else config.COLOR_EXITO
                self.boton_estado.configure(text=texto_boton, fg_color=color)

    # ----------------------------------------------------------------
    def _nueva_persona(self):
        FormularioPersona(self, self.usuario, id_persona=None, al_guardar=self.buscar)

    def _editar_seleccionado(self):
        if self.persona_seleccionada_id is not None:
            FormularioPersona(self, self.usuario, id_persona=self.persona_seleccionada_id, al_guardar=self.buscar)

    def _alternar_estado_seleccionado(self):
        if self.persona_seleccionada_id is None:
            return

        persona = obtener_persona(self.persona_seleccionada_id)
        nombre_completo = f"{persona['nombre']} {persona['apellido']}"
        va_a_activar = not self.persona_seleccionada_activa

        accion_texto = "reactivar" if va_a_activar else "dar de baja a"
        confirmar = messagebox.askyesno(
            "Confirmar acción",
            f"¿Seguro que querés {accion_texto} a '{nombre_completo}'?",
        )

        if confirmar:
            cambiar_estado_persona(self.persona_seleccionada_id, va_a_activar, self.usuario["id"])
            self.buscar()


# ==================================================================
# FORMULARIO (ventana emergente) DE ALTA / EDICIÓN DE PERSONA
# ==================================================================

class FormularioPersona(ctk.CTkToplevel):
    def __init__(self, parent, usuario, id_persona=None, al_guardar=None):
        super().__init__(parent)
        self.usuario = usuario
        self.id_persona = id_persona
        self.al_guardar = al_guardar
        self.es_edicion = id_persona is not None

        self.title("Editar persona" if self.es_edicion else "Nueva persona")
        self.geometry("460x600")
        self.resizable(False, False)
        self.configure(fg_color=config.COLOR_FONDO)

        self.transient(parent)
        self.after(150, self._activar_bloqueo)

        self._construir_formulario()

        if self.es_edicion:
            self._cargar_datos_existentes()

    def _activar_bloqueo(self):
        try:
            self.grab_set()
        except Exception:
            pass

    # ----------------------------------------------------------------
    def _construir_formulario(self):
        contenedor = ctk.CTkScrollableFrame(self, fg_color=config.COLOR_FONDO)
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        titulo = "Editar persona" if self.es_edicion else "Nueva persona"
        ctk.CTkLabel(
            contenedor, text=titulo,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_SUBTITULO, "bold"),
            text_color=config.COLOR_TEXTO,
        ).pack(anchor="w", pady=(0, 15))

        self.entrada_nombre = self._agregar_campo(contenedor, "Nombre *")
        self.entrada_apellido = self._agregar_campo(contenedor, "Apellido *")
        self.entrada_dni = self._agregar_campo(contenedor, "DNI")

        ctk.CTkLabel(contenedor, text="Rol *", text_color=config.COLOR_TEXTO,
                     font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO)).pack(anchor="w", pady=(8, 2))
        self.combo_rol = ctk.CTkComboBox(contenedor, values=ROLES_DISPONIBLES, width=400)
        self.combo_rol.set(ROLES_DISPONIBLES[0])
        self.combo_rol.pack(anchor="w")

        self.entrada_email = self._agregar_campo(contenedor, "Email")
        self.entrada_telefono = self._agregar_campo(contenedor, "Teléfono")
        self.entrada_fecha_ingreso = self._agregar_campo(contenedor, "Fecha de ingreso (AAAA-MM-DD)")

        ctk.CTkLabel(contenedor, text="Observaciones", text_color=config.COLOR_TEXTO,
                     font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO)).pack(anchor="w", pady=(8, 2))
        self.texto_observaciones = ctk.CTkTextbox(contenedor, width=400, height=70)
        self.texto_observaciones.pack(anchor="w")

        self.label_error = ctk.CTkLabel(
            contenedor, text="", text_color=config.COLOR_ALERTA,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO), wraplength=400, justify="left",
        )
        self.label_error.pack(anchor="w", pady=(10, 5))

        botones = ctk.CTkFrame(contenedor, fg_color="transparent")
        botones.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            botones, text="Cancelar", width=120,
            fg_color="transparent", border_width=1,
            border_color=config.COLOR_GRIS, text_color=config.COLOR_TEXTO,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            botones, text="Guardar", width=150,
            fg_color=config.COLOR_BORDO, hover_color=config.COLOR_BORDO_OSCURO,
            command=self._guardar,
        ).pack(side="right")

    def _agregar_campo(self, parent, etiqueta):
        ctk.CTkLabel(parent, text=etiqueta, text_color=config.COLOR_TEXTO,
                     font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO)).pack(anchor="w", pady=(8, 2))
        entrada = ctk.CTkEntry(parent, width=400, height=34)
        entrada.pack(anchor="w")
        return entrada

    # ----------------------------------------------------------------
    def _cargar_datos_existentes(self):
        persona = obtener_persona(self.id_persona)
        if persona is None:
            return

        self.entrada_nombre.insert(0, persona["nombre"])
        self.entrada_apellido.insert(0, persona["apellido"])
        if persona["dni"]:
            self.entrada_dni.insert(0, persona["dni"])
        self.combo_rol.set(persona["rol"])
        if persona["email"]:
            self.entrada_email.insert(0, persona["email"])
        if persona["telefono"]:
            self.entrada_telefono.insert(0, persona["telefono"])
        if persona["fecha_ingreso"]:
            self.entrada_fecha_ingreso.insert(0, persona["fecha_ingreso"])
        if persona["observaciones"]:
            self.texto_observaciones.insert("1.0", persona["observaciones"])

    # ----------------------------------------------------------------
    def _guardar(self):
        nombre = self.entrada_nombre.get().strip()
        apellido = self.entrada_apellido.get().strip()
        dni = self.entrada_dni.get().strip()
        fecha_ingreso = self.entrada_fecha_ingreso.get().strip()

        if not nombre or not apellido:
            self.label_error.configure(text="El nombre y el apellido son obligatorios.")
            return

        if dni and existe_dni(dni, id_persona_excluir=self.id_persona):
            self.label_error.configure(text=f"Ya existe otra persona registrada con el DNI '{dni}'.")
            return

        if fecha_ingreso and not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha_ingreso):
            self.label_error.configure(text="La fecha debe tener el formato AAAA-MM-DD (ej: 2025-03-14).")
            return

        email = self.entrada_email.get().strip()
        if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            self.label_error.configure(text="El email no tiene un formato válido.")
            return

        datos = {
            "nombre": nombre,
            "apellido": apellido,
            "dni": dni,
            "rol": self.combo_rol.get(),
            "email": email,
            "telefono": self.entrada_telefono.get(),
            "fecha_ingreso": fecha_ingreso,
            "observaciones": self.texto_observaciones.get("1.0", "end").strip(),
        }

        if self.es_edicion:
            actualizar_persona(self.id_persona, datos, self.usuario["id"])
        else:
            crear_persona(datos, self.usuario["id"])

        if self.al_guardar:
            self.al_guardar()

        self.destroy()