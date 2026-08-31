
import sqlite3
import os
import sys

# Aseguramos poder importar utils/security.py sin importar desde dónde se ejecute el programa
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.security import crear_password_hash

# Rutas base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "caeti.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")

# Módulos y acciones que va a tener el sistema de permisos
MODULOS = ["inventario", "personas", "prestamos", "seguridad"]
ACCIONES = ["ver", "crear", "editar", "eliminar", "exportar"]

# Usuario administrador por defecto (se debe cambiar la contraseña luego)
ADMIN_USUARIO = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_NOMBRE_COMPLETO = "Administrador del Sistema"


def conectar():
    """Devuelve una conexión a la base de datos SQLite con las FK activadas."""
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON;")
    conexion.row_factory = sqlite3.Row  # permite acceder a columnas por nombre
    return conexion


def _crear_tablas(conexion):
    """Ejecuta el archivo schema.sql para crear todas las tablas."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as archivo:
        script_sql = archivo.read()
    conexion.executescript(script_sql)


def _cargar_permisos(conexion):
    """Crea todos los permisos posibles (modulo + accion) si no existen."""
    cursor = conexion.cursor()
    for modulo in MODULOS:
        for accion in ACCIONES:
            cursor.execute(
                "INSERT OR IGNORE INTO permisos (modulo, accion) VALUES (?, ?)",
                (modulo, accion)
            )
    conexion.commit()


def _crear_grupo_administrador(conexion):
    """Crea el grupo Administrador y le asigna TODOS los permisos disponibles."""
    cursor = conexion.cursor()

    cursor.execute("SELECT id FROM grupos WHERE nombre = 'Administrador'")
    fila = cursor.fetchone()

    if fila is None:
        cursor.execute(
            "INSERT INTO grupos (nombre, descripcion) VALUES (?, ?)",
            ("Administrador", "Acceso total al sistema. Puede gestionar usuarios, grupos y permisos.")
        )
        id_grupo = cursor.lastrowid
    else:
        id_grupo = fila["id"]

    # Le asignamos todos los permisos existentes al grupo Administrador
    cursor.execute("SELECT id FROM permisos")
    permisos = cursor.fetchall()
    for permiso in permisos:
        cursor.execute(
            "INSERT OR IGNORE INTO grupo_permisos (id_grupo, id_permiso) VALUES (?, ?)",
            (id_grupo, permiso["id"])
        )

    conexion.commit()
    return id_grupo


def _crear_usuario_admin_por_defecto(conexion, id_grupo_admin):
    """Crea el usuario 'admin' con contraseña 'admin123' si todavía no existe ningún usuario."""
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
    total_usuarios = cursor.fetchone()["total"]

    if total_usuarios == 0:
        password_hash, salt = crear_password_hash(ADMIN_PASSWORD)
        cursor.execute(
            """
            INSERT INTO usuarios
                (nombre_usuario, password_hash, salt, nombre_completo, email, id_grupo, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (ADMIN_USUARIO, password_hash, salt, ADMIN_NOMBRE_COMPLETO, "", id_grupo_admin)
        )
        conexion.commit()
        print(f"[PPS] Usuario administrador creado -> usuario: '{ADMIN_USUARIO}' / contraseña: '{ADMIN_PASSWORD}'")
        print("[PPS] IMPORTANTE: cambiar esta contraseña desde el módulo de Seguridad apenas se ingrese.")


def inicializar_bd():
   
    es_primera_vez = not os.path.exists(DB_PATH)

    conexion = conectar()
    try:
        _crear_tablas(conexion)
        _cargar_permisos(conexion)
        id_grupo_admin = _crear_grupo_administrador(conexion)
        _crear_usuario_admin_por_defecto(conexion, id_grupo_admin)
    finally:
        conexion.close()

    if es_primera_vez:
        print(f"[PPS] Base de datos creada correctamente en: {DB_PATH}")


# Permite ejecutar este archivo solo (python db/database.py) para inicializar la BD a mano
if __name__ == "__main__":
    inicializar_bd()