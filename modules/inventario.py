"""
PPS - CAETI (UAI)
Capa de datos del módulo Inventario.

Estas funciones se encargan de hablar con la base de datos.
La interfaz gráfica (parte 7 en adelante) va a llamar a estas funciones,
nunca va a escribir SQL directamente.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import conectar
from utils.auditoria import registrar_auditoria


# ----------------------------------------------------------------
# CATEGORÍAS
# ----------------------------------------------------------------

def listar_categorias():
    """Devuelve todas las categorías, ordenadas alfabéticamente."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre FROM categorias ORDER BY nombre")
        return cursor.fetchall()
    finally:
        conexion.close()


def crear_categoria(nombre):
    """Crea una nueva categoría (por ejemplo 'Electrónica', 'Robótica', etc.)."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre.strip(),))
        conexion.commit()
        return cursor.lastrowid
    finally:
        conexion.close()


def _sembrar_categorias_iniciales():
    """Si no hay ninguna categoría cargada, crea algunas típicas de un laboratorio de robótica."""
    categorias_base = ["Electrónica", "Robótica", "Herramientas", "Impresión 3D", "Informática", "Otros"]
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM categorias")
        if cursor.fetchone()["total"] == 0:
            for nombre in categorias_base:
                cursor.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
            conexion.commit()
    finally:
        conexion.close()


# ----------------------------------------------------------------
# ITEMS DEL INVENTARIO
# ----------------------------------------------------------------

def listar_items(texto_busqueda=None, id_categoria=None, estado=None):
    """
    Devuelve los items del inventario, aplicando filtros opcionales:
      - texto_busqueda: busca coincidencias en código, nombre, marca o modelo.
      - id_categoria: filtra por una categoría puntual.
      - estado: 'Operativo', 'En reparación' o 'Dado de baja'.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        consulta = """
            SELECT items.id, items.codigo, items.nombre, items.marca, items.modelo,
                   items.cantidad_total, items.cantidad_disponible, items.estado,
                   items.ubicacion, items.fecha_ingreso, items.observaciones,
                   categorias.nombre AS categoria, items.id_categoria
            FROM items
            LEFT JOIN categorias ON items.id_categoria = categorias.id
            WHERE 1=1
        """
        parametros = []

        if texto_busqueda:
            consulta += """ AND (items.codigo LIKE ? OR items.nombre LIKE ?
                                  OR items.marca LIKE ? OR items.modelo LIKE ?)"""
            comodin = f"%{texto_busqueda}%"
            parametros += [comodin, comodin, comodin, comodin]

        if id_categoria:
            consulta += " AND items.id_categoria = ?"
            parametros.append(id_categoria)

        if estado:
            consulta += " AND items.estado = ?"
            parametros.append(estado)

        consulta += " ORDER BY items.nombre"

        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()


def obtener_item(id_item):
    """Devuelve un item puntual por su id (se usa al abrir el formulario de edición)."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM items WHERE id = ?", (id_item,))
        return cursor.fetchone()
    finally:
        conexion.close()


def crear_item(datos, id_usuario):
    """
    Crea un nuevo item en el inventario.
    'datos' es un diccionario con: codigo, nombre, id_categoria, marca, modelo,
    cantidad_total, estado, ubicacion, fecha_ingreso, observaciones.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO items
                (codigo, nombre, id_categoria, marca, modelo,
                 cantidad_total, cantidad_disponible, estado, ubicacion,
                 fecha_ingreso, observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datos["codigo"].strip(),
                datos["nombre"].strip(),
                datos["id_categoria"],
                datos.get("marca", "").strip(),
                datos.get("modelo", "").strip(),
                datos["cantidad_total"],
                datos["cantidad_total"],  # al crearlo, todo está disponible
                datos["estado"],
                datos.get("ubicacion", "").strip(),
                datos.get("fecha_ingreso") or None,
                datos.get("observaciones", "").strip(),
            )
        )
        conexion.commit()
        id_nuevo = cursor.lastrowid

        registrar_auditoria(
            id_usuario, "ALTA", "inventario",
            f"Se dio de alta el item '{datos['nombre']}' (código {datos['codigo']})"
        )
        return id_nuevo
    finally:
        conexion.close()


def actualizar_item(id_item, datos, id_usuario):
    """Modifica un item existente. 'datos' tiene las mismas claves que en crear_item."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE items SET
                codigo = ?, nombre = ?, id_categoria = ?, marca = ?, modelo = ?,
                cantidad_total = ?, estado = ?, ubicacion = ?,
                fecha_ingreso = ?, observaciones = ?
            WHERE id = ?
            """,
            (
                datos["codigo"].strip(),
                datos["nombre"].strip(),
                datos["id_categoria"],
                datos.get("marca", "").strip(),
                datos.get("modelo", "").strip(),
                datos["cantidad_total"],
                datos["estado"],
                datos.get("ubicacion", "").strip(),
                datos.get("fecha_ingreso") or None,
                datos.get("observaciones", "").strip(),
                id_item,
            )
        )
        conexion.commit()

        registrar_auditoria(
            id_usuario, "MODIFICACION", "inventario",
            f"Se modificó el item '{datos['nombre']}' (código {datos['codigo']})"
        )
    finally:
        conexion.close()


def eliminar_item(id_item, id_usuario):
    """Elimina un item del inventario de forma definitiva."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        # Guardamos el nombre antes de borrar, para que quede claro en la auditoría
        cursor.execute("SELECT nombre, codigo FROM items WHERE id = ?", (id_item,))
        fila = cursor.fetchone()
        nombre_item = fila["nombre"] if fila else f"id {id_item}"
        codigo_item = fila["codigo"] if fila else "?"

        cursor.execute("DELETE FROM items WHERE id = ?", (id_item,))
        conexion.commit()

        registrar_auditoria(
            id_usuario, "BAJA", "inventario",
            f"Se eliminó el item '{nombre_item}' (código {codigo_item})"
        )
    finally:
        conexion.close()


def existe_codigo(codigo, id_item_excluir=None):
    """
    Chequea si un código ya está en uso por otro item (los códigos deben ser únicos).
    id_item_excluir se usa al editar, para no chocar contra el propio item.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        if id_item_excluir:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM items WHERE codigo = ? AND id != ?",
                (codigo.strip(), id_item_excluir)
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM items WHERE codigo = ?",
                (codigo.strip(),)
            )
        return cursor.fetchone()["total"] > 0
    finally:
        conexion.close()


# ==================================================================
# INTERFAZ GRÁFICA DEL MÓDULO INVENTARIO
# ==================================================================

import customtkinter as ctk
from tkinter import ttk, messagebox
from utils import config
from modules.auth import tiene_permiso


class InventarioFrame(ctk.CTkFrame):
    """
    Pantalla del módulo Inventario: filtros de búsqueda + tabla de items.
    Se inserta dentro del área de contenido de la Ventana Principal.
    """

    def __init__(self, parent, usuario):
        super().__init__(parent, fg_color=config.COLOR_FONDO)
        self.usuario = usuario
        self.item_seleccionado_id = None

        _sembrar_categorias_iniciales()  # crea categorías por defecto la primera vez

        self._configurar_estilo_tabla()
        self._construir_barra_filtros()
        self._construir_tabla()
        self._construir_barra_acciones()

        self.buscar()

    # ----------------------------------------------------------------
    def _configurar_estilo_tabla(self):
        """Estiliza la tabla (ttk.Treeview) para que combine con la paleta bordo/blanco/negro."""
        estilo = ttk.Style()
        estilo.theme_use("clam")

        estilo.configure(
            "Inventario.Treeview",
            background=config.COLOR_FONDO_TARJETA,
            fieldbackground=config.COLOR_FONDO_TARJETA,
            foreground=config.COLOR_TEXTO,
            rowheight=32,
            borderwidth=0,
            font=(config.FUENTE_PRINCIPAL, 11),
        )
        estilo.configure(
            "Inventario.Treeview.Heading",
            background=config.COLOR_BORDO,
            foreground=config.COLOR_TEXTO_CLARO,
            font=(config.FUENTE_PRINCIPAL, 11, "bold"),
            borderwidth=0,
        )
        estilo.map(
            "Inventario.Treeview",
            background=[("selected", config.COLOR_BORDO)],
            foreground=[("selected", config.COLOR_TEXTO_CLARO)],
        )

    # ----------------------------------------------------------------
    def _construir_barra_filtros(self):
        barra = ctk.CTkFrame(self, fg_color=config.COLOR_FONDO_TARJETA, corner_radius=8)
        barra.pack(fill="x", pady=(0, 15))

        self.entrada_busqueda = ctk.CTkEntry(
            barra, placeholder_text="Buscar por código, nombre, marca o modelo...",
            width=280, height=34,
        )
        self.entrada_busqueda.pack(side="left", padx=(15, 10), pady=12)
        self.entrada_busqueda.bind("<Return>", lambda evento: self.buscar())

        categorias = listar_categorias()
        opciones_categoria = ["Todas las categorías"] + [c["nombre"] for c in categorias]
        self._mapa_categorias = {c["nombre"]: c["id"] for c in categorias}

        self.combo_categoria = ctk.CTkComboBox(barra, values=opciones_categoria, width=180, height=34)
        self.combo_categoria.set("Todas las categorías")
        self.combo_categoria.pack(side="left", padx=(0, 10), pady=12)

        opciones_estado = ["Todos los estados", "Operativo", "En reparación", "Dado de baja"]
        self.combo_estado = ctk.CTkComboBox(barra, values=opciones_estado, width=160, height=34)
        self.combo_estado.set("Todos los estados")
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

        columnas = ("codigo", "nombre", "categoria", "cantidad", "disponible", "estado", "ubicacion")
        self.tabla = ttk.Treeview(
            contenedor_tabla, columns=columnas, show="headings",
            style="Inventario.Treeview", selectmode="browse",
        )

        encabezados = {
            "codigo": "Código", "nombre": "Nombre", "categoria": "Categoría",
            "cantidad": "Cant. Total", "disponible": "Disponible",
            "estado": "Estado", "ubicacion": "Ubicación",
        }
        anchos = {
            "codigo": 90, "nombre": 200, "categoria": 120,
            "cantidad": 90, "disponible": 90, "estado": 110, "ubicacion": 150,
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

        if tiene_permiso(self.usuario, "inventario", "eliminar"):
            self.boton_eliminar = ctk.CTkButton(
                barra, text="Eliminar seleccionado", width=170, height=36,
                fg_color=config.COLOR_ALERTA, hover_color=config.COLOR_BORDO_OSCURO,
                state="disabled", command=self._eliminar_seleccionado,
            )
            self.boton_eliminar.pack(side="right", padx=(10, 0))

        if tiene_permiso(self.usuario, "inventario", "editar"):
            self.boton_editar = ctk.CTkButton(
                barra, text="Editar seleccionado", width=160, height=36,
                fg_color="transparent", border_width=1,
                border_color=config.COLOR_BORDO, text_color=config.COLOR_BORDO,
                hover_color=config.COLOR_GRIS_CLARO,
                state="disabled", command=self._editar_seleccionado,
            )
            self.boton_editar.pack(side="right", padx=(10, 0))

        if tiene_permiso(self.usuario, "inventario", "crear"):
            ctk.CTkButton(
                barra, text="+ Nuevo item", width=140, height=36,
                fg_color=config.COLOR_BORDO, hover_color=config.COLOR_BORDO_OSCURO,
                command=self._nuevo_item,
            ).pack(side="right")

    # ----------------------------------------------------------------
    def buscar(self):
        """Aplica los filtros actuales y recarga la tabla."""
        texto = self.entrada_busqueda.get().strip() or None

        nombre_categoria = self.combo_categoria.get()
        id_categoria = self._mapa_categorias.get(nombre_categoria) if nombre_categoria != "Todas las categorías" else None

        estado = self.combo_estado.get()
        estado = None if estado == "Todos los estados" else estado

        items = listar_items(texto_busqueda=texto, id_categoria=id_categoria, estado=estado)
        self._cargar_filas(items)

    def _limpiar_filtros(self):
        self.entrada_busqueda.delete(0, "end")
        self.combo_categoria.set("Todas las categorías")
        self.combo_estado.set("Todos los estados")
        self.buscar()

    def _cargar_filas(self, items):
        self.tabla.delete(*self.tabla.get_children())
        for item in items:
            self.tabla.insert(
                "", "end", iid=str(item["id"]),
                values=(
                    item["codigo"], item["nombre"], item["categoria"] or "-",
                    item["cantidad_total"], item["cantidad_disponible"],
                    item["estado"], item["ubicacion"] or "-",
                )
            )
        self.label_contador.configure(text=f"{len(items)} ítem(s) encontrado(s)")
        self._al_seleccionar_fila(None)

    # ----------------------------------------------------------------
    def _al_seleccionar_fila(self, evento):
        seleccion = self.tabla.selection()
        self.item_seleccionado_id = int(seleccion[0]) if seleccion else None

        hay_seleccion = self.item_seleccionado_id is not None
        if hasattr(self, "boton_editar"):
            self.boton_editar.configure(state="normal" if hay_seleccion else "disabled")
        if hasattr(self, "boton_eliminar"):
            self.boton_eliminar.configure(state="normal" if hay_seleccion else "disabled")

    # ----------------------------------------------------------------
        # ----------------------------------------------------------------
    def _nuevo_item(self):
        FormularioItem(self, self.usuario, id_item=None, al_guardar=self.buscar)

    def _editar_seleccionado(self):
        if self.item_seleccionado_id is not None:
            FormularioItem(self, self.usuario, id_item=self.item_seleccionado_id, al_guardar=self.buscar)

    def _eliminar_seleccionado(self):
        if self.item_seleccionado_id is None:
            return

        item = obtener_item(self.item_seleccionado_id)
        nombre_item = item["nombre"] if item else "este item"
        codigo_item = item["codigo"] if item else ""

        confirmar = messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Seguro que querés eliminar el item:\n\n"
            f"'{nombre_item}' (código {codigo_item})\n\n"
            f"del inventario? Esta acción no se puede deshacer.",
            icon="warning",
        )

        if confirmar:
            eliminar_item(self.item_seleccionado_id, self.usuario["id"])
            self.item_seleccionado_id = None
            self.buscar()

# ==================================================================
# FORMULARIO (ventana emergente) DE ALTA / EDICIÓN DE ITEM
# ==================================================================

class FormularioItem(ctk.CTkToplevel):
    """
    Ventana emergente con el formulario para crear o editar un item.
    Si id_item es None, es un alta. Si tiene un valor, es una edición.
    'al_guardar' es una función que se llama al terminar, para refrescar la tabla.
    """

    def __init__(self, parent, usuario, id_item=None, al_guardar=None):
        super().__init__(parent)
        self.usuario = usuario
        self.id_item = id_item
        self.al_guardar = al_guardar
        self.es_edicion = id_item is not None

        self.title("Editar item" if self.es_edicion else "Nuevo item")
        self.geometry("480x640")
        self.resizable(False, False)
        self.configure(fg_color=config.COLOR_FONDO)

        # Hace que la ventana emergente bloquee la principal hasta que se cierre
        self.transient(parent)
        self.after(150, self._activar_bloqueo)

        self._construir_formulario()

        if self.es_edicion:
            self._cargar_datos_existentes()
            
    def _activar_bloqueo(self):
        """Activa el bloqueo de la ventana principal, ya con el formulario visible."""
        try:
            self.grab_set()
        except Exception:
            pass  # si por algún motivo falla, no interrumpe el uso del formulario

    # ----------------------------------------------------------------
    def _construir_formulario(self):
        contenedor = ctk.CTkScrollableFrame(self, fg_color=config.COLOR_FONDO)
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        titulo = "Editar item" if self.es_edicion else "Nuevo item"
        ctk.CTkLabel(
            contenedor, text=titulo,
            font=(config.FUENTE_PRINCIPAL, config.TAMANO_SUBTITULO, "bold"),
            text_color=config.COLOR_TEXTO,
        ).pack(anchor="w", pady=(0, 15))

        self.entrada_codigo = self._agregar_campo(contenedor, "Código *")
        self.entrada_nombre = self._agregar_campo(contenedor, "Nombre *")

        # Categoría
        ctk.CTkLabel(contenedor, text="Categoría", text_color=config.COLOR_TEXTO,
                     font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO)).pack(anchor="w", pady=(8, 2))
        categorias = listar_categorias()
        self._mapa_categorias = {c["nombre"]: c["id"] for c in categorias}
        nombres_categorias = list(self._mapa_categorias.keys()) or ["Otros"]
        self.combo_categoria = ctk.CTkComboBox(contenedor, values=nombres_categorias, width=400)
        self.combo_categoria.set(nombres_categorias[0])
        self.combo_categoria.pack(anchor="w")

        self.entrada_marca = self._agregar_campo(contenedor, "Marca")
        self.entrada_modelo = self._agregar_campo(contenedor, "Modelo")
        self.entrada_cantidad = self._agregar_campo(contenedor, "Cantidad total *")

        # Estado
        ctk.CTkLabel(contenedor, text="Estado", text_color=config.COLOR_TEXTO,
                     font=(config.FUENTE_PRINCIPAL, config.TAMANO_TEXTO_CHICO)).pack(anchor="w", pady=(8, 2))
        self.combo_estado = ctk.CTkComboBox(
            contenedor, values=["Operativo", "En reparación", "Dado de baja"], width=400
        )
        self.combo_estado.set("Operativo")
        self.combo_estado.pack(anchor="w")

        self.entrada_ubicacion = self._agregar_campo(contenedor, "Ubicación")
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
        """Si es edición, precarga los campos con los datos actuales del item."""
        item = obtener_item(self.id_item)
        if item is None:
            return

        self.entrada_codigo.insert(0, item["codigo"])
        self.entrada_nombre.insert(0, item["nombre"])

        if item["marca"]:
            self.entrada_marca.insert(0, item["marca"])
        if item["modelo"]:
            self.entrada_modelo.insert(0, item["modelo"])

        self.entrada_cantidad.insert(0, str(item["cantidad_total"]))
        self.combo_estado.set(item["estado"])

        if item["ubicacion"]:
            self.entrada_ubicacion.insert(0, item["ubicacion"])
        if item["fecha_ingreso"]:
            self.entrada_fecha_ingreso.insert(0, item["fecha_ingreso"])
        if item["observaciones"]:
            self.texto_observaciones.insert("1.0", item["observaciones"])

        # Seleccionar la categoría correcta en el combo
        for nombre_categoria, id_categoria in self._mapa_categorias.items():
            if id_categoria == item["id_categoria"]:
                self.combo_categoria.set(nombre_categoria)
                break

    # ----------------------------------------------------------------
    def _guardar(self):
        codigo = self.entrada_codigo.get().strip()
        nombre = self.entrada_nombre.get().strip()
        cantidad_texto = self.entrada_cantidad.get().strip()
        fecha_ingreso = self.entrada_fecha_ingreso.get().strip()

        # --- Validaciones ---
        if not codigo or not nombre:
            self.label_error.configure(text="El código y el nombre son obligatorios.")
            return

        if not cantidad_texto.isdigit() or int(cantidad_texto) <= 0:
            self.label_error.configure(text="La cantidad total debe ser un número entero mayor a 0.")
            return

        if existe_codigo(codigo, id_item_excluir=self.id_item):
            self.label_error.configure(text=f"Ya existe otro item con el código '{codigo}'.")
            return

        if fecha_ingreso:
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha_ingreso):
                self.label_error.configure(text="La fecha debe tener el formato AAAA-MM-DD (ej: 2025-03-14).")
                return

        nombre_categoria = self.combo_categoria.get()
        id_categoria = self._mapa_categorias.get(nombre_categoria)

        datos = {
            "codigo": codigo,
            "nombre": nombre,
            "id_categoria": id_categoria,
            "marca": self.entrada_marca.get(),
            "modelo": self.entrada_modelo.get(),
            "cantidad_total": int(cantidad_texto),
            "estado": self.combo_estado.get(),
            "ubicacion": self.entrada_ubicacion.get(),
            "fecha_ingreso": fecha_ingreso,
            "observaciones": self.texto_observaciones.get("1.0", "end").strip(),
        }

        if self.es_edicion:
            actualizar_item(self.id_item, datos, self.usuario["id"])
        else:
            crear_item(datos, self.usuario["id"])

        if self.al_guardar:
            self.al_guardar()  # refresca la tabla en la pantalla de atrás

        self.destroy()