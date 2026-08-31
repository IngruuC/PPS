"""
PPS - CAETI (UAI)
Registro de auditoría.

Cada vez que un usuario hace login, crea, edita o elimina algo,
se llama a registrar_auditoria() para dejar constancia en la tabla 'auditoria'.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import conectar


def registrar_auditoria(id_usuario, accion, modulo, detalle=""):
    """
    Guarda un registro en la tabla de auditoría.

    Parámetros:
        id_usuario: id del usuario que realizó la acción (None si fue un intento de login fallido).
        accion: texto corto, por ejemplo 'ALTA', 'BAJA', 'MODIFICACION', 'LOGIN', 'LOGIN_FALLIDO'.
        modulo: 'inventario', 'personas', 'prestamos', 'seguridad' o 'sistema'.
        detalle: texto libre describiendo qué se hizo, por ejemplo
                 "Se eliminó el item 'Arduino UNO' (código ARD-001)".
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO auditoria (id_usuario, accion, modulo, detalle)
            VALUES (?, ?, ?, ?)
            """,
            (id_usuario, accion, modulo, detalle)
        )
        conexion.commit()
    finally:
        conexion.close()


def obtener_auditoria(filtro_usuario=None, filtro_modulo=None, filtro_accion=None, texto_busqueda=None):
    """
    Devuelve los registros de auditoría, con filtros opcionales.
    Se usa en la pantalla de Seguridad > Auditoría para el administrador.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        consulta = """
            SELECT auditoria.id, auditoria.accion, auditoria.modulo,
                   auditoria.detalle, auditoria.fecha_hora,
                   usuarios.nombre_usuario, usuarios.nombre_completo
            FROM auditoria
            LEFT JOIN usuarios ON auditoria.id_usuario = usuarios.id
            WHERE 1=1
        """
        parametros = []

        if filtro_usuario:
            consulta += " AND usuarios.nombre_usuario LIKE ?"
            parametros.append(f"%{filtro_usuario}%")

        if filtro_modulo:
            consulta += " AND auditoria.modulo = ?"
            parametros.append(filtro_modulo)

        if filtro_accion:
            consulta += " AND auditoria.accion = ?"
            parametros.append(filtro_accion)

        if texto_busqueda:
            consulta += " AND auditoria.detalle LIKE ?"
            parametros.append(f"%{texto_busqueda}%")

        consulta += " ORDER BY auditoria.fecha_hora DESC"

        cursor.execute(consulta, parametros)
        return cursor.fetchall()
    finally:
        conexion.close()