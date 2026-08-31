"""
PPS - CAETI (UAI)
Módulo Préstamos: registra qué persona retiró qué item, y su devolución.

Al crear un préstamo, se descuenta cantidad_disponible del item.
Al marcarlo como devuelto, se repone esa cantidad.
Los préstamos no se eliminan (quedan como historial), solo cambian de estado.
"""

import sys
import os
import re
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import conectar
from utils.auditoria import registrar_auditoria


# ----------------------------------------------------------------
# CAPA DE DATOS
# ----------------------------------------------------------------

def listar_prestamos(texto_busqueda=None, estado=None):
    """
    Devuelve los préstamos, con filtros opcionales:
      - texto_busqueda: busca en nombre del item o nombre/apellido de la persona.
      - estado: 'Prestado', 'Devuelto' o None (todos).
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        consulta = """
            SELECT prestamos.id, prestamos.cantidad, prestamos.fecha_retiro,
                   prestamos.fecha_devolucion_estimada, prestamos.fecha_devolucion_real,
                   prestamos.estado, prestamos.observaciones,
                   prestamos.id_item, prestamos.id_persona,
                   items.codigo AS item_codigo, items.nombre AS item_nombre,
                   personas.nombre AS persona_nombre, personas.apellido AS persona_apellido
            FROM prestamos
            JOIN items ON prestamos.id_item = items.id
            JOIN personas ON prestamos.id_persona = personas.id
            WHERE 1=1
        """
        parametros = []

        if texto_busqueda:
            consulta += """ AND (items.nombre LIKE ? OR items.codigo LIKE ?
                                  OR personas.nombre LIKE ? OR personas.apellido LIKE ?)"""
            comodin = f"%{texto_busqueda}%"
            parametros += [comodin, comodin, comodin, comodin]

        if estado:
            consulta += " AND prestamos.estado = ?"
            parametros.append(estado)

        consulta += " ORDER BY prestamos.fecha_retiro DESC"

        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()


def obtener_prestamo(id_prestamo):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM prestamos WHERE id = ?", (id_prestamo,))
        return cursor.fetchone()
    finally:
        conexion.close()


def listar_items_disponibles():
    """Devuelve los items que tienen al menos 1 unidad disponible para prestar."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT id, codigo, nombre, cantidad_disponible
            FROM items
            WHERE cantidad_disponible > 0 AND estado = 'Operativo'
            ORDER BY nombre
            """
        )
        return cursor.fetchall()
    finally:
        conexion.close()


def listar_personas_activas():
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id, nombre, apellido FROM personas WHERE activo = 1 ORDER BY apellido, nombre"
        )
        return cursor.fetchall()
    finally:
        conexion.close()


def crear_prestamo(id_item, id_persona, cantidad, fecha_devolucion_estimada, observaciones, id_usuario):
    """
    Registra un nuevo préstamo y descuenta la cantidad disponible del item.
    Devuelve (True, "") si salió bien, o (False, "mensaje de error") si no.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        cursor.execute("SELECT nombre, cantidad_disponible FROM items WHERE id = ?", (id_item,))
        item = cursor.fetchone()
        if item is None:
            return False, "El item seleccionado ya no existe."
        if item["cantidad_disponible"] < cantidad:
            return False, f"Solo hay {item['cantidad_disponible']} unidad(es) disponible(s) de este item."

        cursor.execute("SELECT nombre, apellido FROM personas WHERE id = ?", (id_persona,))
        persona = cursor.fetchone()
        if persona is None:
            return False, "La persona seleccionada ya no existe."

        cursor.execute(
            """
            INSERT INTO prestamos
                (id_item, id_persona, cantidad, fecha_devolucion_estimada,
                 estado, id_usuario_registro, observaciones)
            VALUES (?, ?, ?, ?, 'Prestado', ?, ?)
            """,
            (id_item, id_persona, cantidad, fecha_devolucion_estimada or None,
             id_usuario, observaciones.strip())
        )

        cursor.execute(
            "UPDATE items SET cantidad_disponible = cantidad_disponible - ? WHERE id = ?",
            (cantidad, id_item)
        )

        conexion.commit()

        registrar_auditoria(
            id_usuario, "ALTA", "prestamos",
            f"Préstamo registrado: '{item['nombre']}' (x{cantidad}) a {persona['nombre']} {persona['apellido']}"
        )
        return True, ""
    finally:
        conexion.close()


def marcar_devuelto(id_prestamo, id_usuario):
    """Marca un préstamo como devuelto y repone la cantidad disponible del item."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT prestamos.cantidad, prestamos.id_item, items.nombre AS item_nombre,
                   personas.nombre AS persona_nombre, personas.apellido AS persona_apellido
            FROM prestamos
            JOIN items ON prestamos.id_item = items.id
            JOIN personas ON prestamos.id_persona = personas.id
            WHERE prestamos.id = ?
            """,
            (id_prestamo,)
        )
        fila = cursor.fetchone()
        if fila is None:
            return

        cursor.execute(
            """
            UPDATE prestamos SET estado = 'Devuelto', fecha_devolucion_real = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(sep=" ", timespec="seconds"), id_prestamo)
        )

        cursor.execute(
            "UPDATE items SET cantidad_disponible = cantidad_disponible + ? WHERE id = ?",
            (fila["cantidad"], fila["id_item"])
        )

        conexion.commit()

        registrar_auditoria(
            id_usuario, "MODIFICACION", "prestamos",
            f"Devolución registrada: '{fila['item_nombre']}' (x{fila['cantidad']}) "
            f"de {fila['persona_nombre']} {fila['persona_apellido']}"
        )
    finally:
        conexion.close()


# ==================================================================
# INTERFAZ GRÁFICA DEL MÓDULO PRÉSTAMOS
# ==================================================================

import customtkinter as ctk
from tkinter import ttk, messagebox
from utils import config
from modules.auth import tiene_permiso


class PrestamosFrame(ctk.CTkFrame):
    def __init__(self, parent, usuario):
        super().__init__(parent, fg_color=config.COLOR_FONDO)
        self.usuario = usuario
        self.prestamo_seleccionado_id = None
        self.prestamo_seleccionado_estado = None

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
            "Prestamos.Treeview",
            background=config.COLOR_FONDO_TARJETA,
            fieldbackground=config.COLOR_FONDO_TARJETA,
            foreground=config.COLOR_TEXTO,
            rowheight=32, borderwidth=0,
            font=(config.FUENTE_PRINCIPAL, 11),
        )
        estilo.configure(
            "Prestamos.Treeview.Heading",
            background=config.COLOR_BORDO, foreground=config.COLOR_TEXTO_CLARO,
            font=(config.FUENTE_PRINCIPAL, 11, "bold"), borderwidth=0,
        )
        estilo.map(
            "Prestamos.Treeview",
            background=[("selected", config.COLOR_BORDO)],
            foreground=[("selected", config.COLOR_TEXTO_CLARO)],
        )

    # ----------------------------------------------------------------
    def _construir_barra_filtros(self):
        barra = ctk.CTkFrame(self, fg_color=config.COLOR_FONDO_TARJETA, corner_radius=8)
        barra.pack(fill="x", pady=(0, 15))

        self.entrada_busqueda = ctk.CTkEntry(
            barra, placeholder_text="Buscar por item o persona...",
            width=280, height=34,
        )
        self.entrada_busqueda.pack(side="left", padx=(15, 10), pady=12)
        self.entrada_busqueda.bind("<Return>", lambda evento: self.buscar())

        self.combo_estado = ctk.CTkComboBox(
            barra, values=["Todos", "Prestado", "Devuelto"], width=140, height=34
        )
        self.combo_estado.set("Prestado")
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

        columnas = ("item", "persona", "cantidad", "fecha_retiro", "fecha_estimada", "fecha_real", "estado")
        self.tabla = ttk.Treeview(
            contenedor_tabla, columns=columnas, show="headings",
            style="Prestamos.Treeview", selectmode="browse",
        )

        encabezados = {
            "item": "Item", "persona": "Persona", "cantidad": "Cant.",
            "fecha_retiro": "Fecha retiro", "fecha_estimada": "Dev. estimada",
            "fecha_real": "Dev. real", "estado": "Estado",
        }
        anchos = {
            "item": 170, "persona": 150, "cantidad": 60,
            "fecha_retiro": 120, "fecha_estimada": 110, "fecha_real": 120, "estado": 90,
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

        if tiene_permiso(self.usuario, "prestamos", "editar"):
            self.boton_devolver = ctk.CTkButton(
                barra, text="Marcar como devuelto", width=180, height=36,
                fg_color=config.COLOR_EXITO, hover_color=config.COLOR_BORDO_OSCURO,
                state="disabled", command=self._marcar_devuelto_seleccionado,
            )
            self.boton_devolver.pack(side="right", padx=(10, 0))

        if tiene_permiso(self.usuario, "prestamos", "crear"):
            ctk.CTkButton(
                barra, text="+ Nuevo préstamo", width=160, height=36,
                fg_color=config.COLOR_BORDO, hover_color=config.COLOR_BORDO_OSCURO,
                command=self._nuevo_prestamo,
            ).pack(side="right")

    # ----------------------------------------------------------------
    def buscar(self):
        texto = self.entrada_busqueda.get().strip() or None
        estado_texto = self.combo_estado.get()
        estado = None if estado_texto == "Todos" else estado_texto

        prestamos = listar_prestamos(texto_busqueda=texto, estado=estado)
        self._cargar_filas(prestamos)

    def _limpiar_filtros(self):
        self.entrada_busqueda.delete(0, "end")
        self.combo_estado.set("Prestado")
        self.buscar()

    def _cargar_filas(self, prestamos):
        self.tabla.delete(*self.tabla.get_children())
        for prestamo in prestamos:
            self.tabla.insert(
                "", "end", iid=str(prestamo["id"]),
                values=(
                    f"{prestamo['item_codigo']} - {prestamo['item_nombre']}",
                    f"{prestamo['persona_apellido']}, {prestamo['persona_nombre']}",
                    prestamo["cantidad"],
                    (prestamo["fecha_retiro"] or "-")[:16],
                    prestamo["fecha_devolucion_estimada"] or "-",
                    (prestamo["fecha_devolucion_real"] or "-")[:16] if prestamo["fecha_devolucion_real"] else "-",
                    prestamo["estado"],
                )
            )
        self.label_contador.configure(text=f"{len(prestamos)} préstamo(s) encontrado(s)")
        self._al_seleccionar_fila(None)

    # ----------------------------------------------------------------
    def _al_seleccionar_fila(self, evento):
        seleccion = self.tabla.selection()
        if not seleccion:
            self.prestamo_seleccionado_id = None
            self.prestamo_seleccionado_estado = None
        else:
            self.prestamo_seleccionado_id = int(seleccion[0])
            prestamo = obtener_prestamo(self.prestamo_seleccionado_id)
            self.prestamo_seleccionado_estado = prestamo["estado"] if prestamo else None

        if hasattr(self, "boton_devolver"):
            puede_devolver = (
                self.prestamo_seleccionado_id is not None
                and self.prestamo_seleccionado_estado == "Prestado"
            )
            self.boton_devolver.configure(state="normal" if puede_devolver else "disabled")

    # ----------------------------------------------------------------
    def _nuevo_prestamo(self):
        FormularioPrestamo(self, self.usuario, al_guardar=self.buscar)

    def _marcar_devuelto_seleccionado(self):
        if self.prestamo_seleccionado_id is None:
            return

        confirmar = messagebox.askyesno(
            "Confirmar devolución",
            "¿Confirmás que este item fue devuelto?\nSe repondrá la cantidad disponible en el inventario.",
        )
        if confirmar:
            marcar_devuelto(self.prestamo_seleccionado_id, self.usuario["id"])
            self.buscar()


# ==================================================================
# FORMULARIO (ventana emergente) DE NUEVO PRÉSTAMO
# ==================================================================

class FormularioPrestamo(ctk.CTkToplevel):
    def __init__(self, parent, usuario, al_guardar=None):
        super().__init__(parent)
        self.usuario = usuario
        self.al_guardar = al_guardar

        self.title("Nuevo préstamo")
        self.geometry("460x520")
        self.resizable(False, False)
        self.configure(fg_color=config.COLOR_FONDO)

        self.transient(parent)
        self.after(150, self._activar_bloqueo)

        self._construir_formulario()

    def _activar_bloqueo(self):
        try:
            self.grab_set()
        except Exception:
            pass

    # ----------------------------------------------------------------
    def _construir_formulario(self):
        contenedor = ctk.CTkScrollableFrame(self, fg_color=config.COLOR_FONDO)
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            contenedor, text="Nuevo préstamo",
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_SUBTITULO, "bold"),
            text_color=config.COLOR_TEXTO,
        ).pack(anchor="w", pady=(0, 15))

        # Item
        ctk.CTkLabel(contenedor, text="Item *", text_color=config.COLOR_TEXTO,
                     font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO)).pack(anchor="w", pady=(8, 2))
        items = listar_items_disponibles()
        self._mapa_items = {f"{i['codigo']} - {i['nombre']} (disp: {i['cantidad_disponible']})": i["id"] for i in items}
        opciones_items = list(self._mapa_items.keys()) or ["No hay items disponibles"]
        self.combo_item = ctk.CTkComboBox(contenedor, values=opciones_items, width=400)
        self.combo_item.set(opciones_items[0])
        self.combo_item.pack(anchor="w")

        # Persona
        ctk.CTkLabel(contenedor, text="Persona *", text_color=config.COLOR_TEXTO,
                     font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO)).pack(anchor="w", pady=(8, 2))
        personas = listar_personas_activas()
        self._mapa_personas = {f"{p['apellido']}, {p['nombre']}": p["id"] for p in personas}
        opciones_personas = list(self._mapa_personas.keys()) or ["No hay personas activas"]
        self.combo_persona = ctk.CTkComboBox(contenedor, values=opciones_personas, width=400)
        self.combo_persona.set(opciones_personas[0])
        self.combo_persona.pack(anchor="w")

        self.entrada_cantidad = self._agregar_campo(contenedor, "Cantidad *")
        self.entrada_cantidad.insert(0, "1")

        self.entrada_fecha_estimada = self._agregar_campo(contenedor, "Fecha de devolución estimada (AAAA-MM-DD)")

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
            botones, text="Registrar préstamo", width=170,
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
    def _guardar(self):
        nombre_item = self.combo_item.get()
        nombre_persona = self.combo_persona.get()
        cantidad_texto = self.entrada_cantidad.get().strip()
        fecha_estimada = self.entrada_fecha_estimada.get().strip()

        if nombre_item not in self._mapa_items:
            self.label_error.configure(text="Tenés que seleccionar un item válido.")
            return
        if nombre_persona not in self._mapa_personas:
            self.label_error.configure(text="Tenés que seleccionar una persona válida.")
            return
        if not cantidad_texto.isdigit() or int(cantidad_texto) <= 0:
            self.label_error.configure(text="La cantidad debe ser un número entero mayor a 0.")
            return
        if fecha_estimada and not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha_estimada):
            self.label_error.configure(text="La fecha debe tener el formato AAAA-MM-DD (ej: 2025-03-14).")
            return

        id_item = self._mapa_items[nombre_item]
        id_persona = self._mapa_personas[nombre_persona]
        cantidad = int(cantidad_texto)
        observaciones = self.texto_observaciones.get("1.0", "end").strip()

        exito, mensaje_error = crear_prestamo(
            id_item, id_persona, cantidad, fecha_estimada, observaciones, self.usuario["id"]
        )

        if not exito:
            self.label_error.configure(text=mensaje_error)
            return

        if self.al_guardar:
            self.al_guardar()

        self.destroy()