"""
PPS - CAETI (UAI)
Lógica de autenticación de usuarios.
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import conectar
from utils.security import verificar_password
from utils.auditoria import registrar_auditoria


def obtener_permisos_usuario(id_grupo):
    """Devuelve una lista de tuplas (modulo, accion) que puede realizar un grupo."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT permisos.modulo, permisos.accion
            FROM grupo_permisos
            JOIN permisos ON grupo_permisos.id_permiso = permisos.id
            WHERE grupo_permisos.id_grupo = ?
            """,
            (id_grupo,)
        )
        filas = cursor.fetchall()
        return [(fila["modulo"], fila["accion"]) for fila in filas]
    finally:
        conexion.close()


def autenticar_usuario(nombre_usuario, password):
    """
    Verifica las credenciales ingresadas.

    Devuelve:
        - Un diccionario con los datos del usuario y sus permisos si es correcto.
        - None si el usuario no existe, está inactivo o la contraseña es incorrecta.
    """
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT usuarios.id, usuarios.nombre_usuario, usuarios.password_hash,
                   usuarios.salt, usuarios.nombre_completo, usuarios.activo,
                   usuarios.id_grupo, grupos.nombre AS nombre_grupo
            FROM usuarios
            JOIN grupos ON usuarios.id_grupo = grupos.id
            WHERE usuarios.nombre_usuario = ?
            """,
            (nombre_usuario,)
        )
        fila = cursor.fetchone()

        # Usuario no existe
        if fila is None:
            registrar_auditoria(None, "LOGIN_FALLIDO", "sistema",
                                 f"Intento de login con usuario inexistente: '{nombre_usuario}'")
            return None

        # Usuario dado de baja
        if fila["activo"] == 0:
            registrar_auditoria(fila["id"], "LOGIN_FALLIDO", "sistema",
                                 f"Intento de login de usuario inactivo: '{nombre_usuario}'")
            return None

        # Contraseña incorrecta
        if not verificar_password(password, fila["password_hash"], fila["salt"]):
            registrar_auditoria(fila["id"], "LOGIN_FALLIDO", "sistema",
                                 f"Contraseña incorrecta para el usuario: '{nombre_usuario}'")
            return None

        # Login exitoso: actualizamos último acceso
        cursor.execute(
            "UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?",
            (datetime.now().isoformat(sep=" ", timespec="seconds"), fila["id"])
        )
        conexion.commit()

        registrar_auditoria(fila["id"], "LOGIN", "sistema",
                             f"Inicio de sesión exitoso: '{nombre_usuario}'")

        permisos = obtener_permisos_usuario(fila["id_grupo"])

        return {
            "id": fila["id"],
            "nombre_usuario": fila["nombre_usuario"],
            "nombre_completo": fila["nombre_completo"],
            "id_grupo": fila["id_grupo"],
            "nombre_grupo": fila["nombre_grupo"],
            "permisos": permisos,  # lista de (modulo, accion)
        }
    finally:
        conexion.close()


def tiene_permiso(usuario, modulo, accion):
    """Chequea si el usuario logueado tiene permiso para 'accion' dentro de 'modulo'."""
    if usuario is None:
        return False
    return (modulo, accion) in usuario["permisos"]