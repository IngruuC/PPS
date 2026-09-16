"""
PPS - CAETI (UAI)
Script de carga de datos de demostración.

Pobla la base de datos con categorías, items, personas y préstamos
realistas de un laboratorio de robótica, para poder mostrar y probar
la aplicación sin cargar todo a mano.

Es idempotente: si la tabla 'items' ya tiene datos, no hace nada.

Uso:
    python -m db.seed_demo
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import inicializar_bd, conectar

CATEGORIAS = [
    "Microcontroladores",
    "Sensores",
    "Actuadores",
    "Componentes electrónicos",
    "Herramientas",
    "Kits educativos",
]

# (codigo, nombre, categoria, marca, modelo, cantidad_total, cantidad_disponible, estado, ubicacion)
ITEMS = [
    ("MCU-001", "Arduino UNO R3", "Microcontroladores", "Arduino", "UNO R3", 10, 7, "Operativo", "Armario A - Estante 1"),
    ("MCU-002", "ESP32 DevKit", "Microcontroladores", "Espressif", "ESP32-WROOM-32", 8, 8, "Operativo", "Armario A - Estante 1"),
    ("MCU-003", "Raspberry Pi 4", "Microcontroladores", "Raspberry Pi Foundation", "4 Model B - 4GB", 5, 4, "Operativo", "Armario A - Estante 2"),
    ("MCU-004", "Arduino Mega 2560", "Microcontroladores", "Arduino", "Mega 2560 R3", 4, 4, "Operativo", "Armario A - Estante 1"),
    ("SEN-001", "Sensor ultrasónico HC-SR04", "Sensores", "Generico", "HC-SR04", 15, 13, "Operativo", "Armario B - Estante 1"),
    ("SEN-002", "Sensor de temperatura DHT22", "Sensores", "Aosong", "DHT22", 12, 12, "Operativo", "Armario B - Estante 1"),
    ("SEN-003", "Sensor infrarrojo IR", "Sensores", "Generico", "TCRT5000", 10, 10, "Operativo", "Armario B - Estante 2"),
    ("ACT-001", "Servo SG90", "Actuadores", "Tower Pro", "SG90", 20, 20, "Operativo", "Armario B - Estante 3"),
    ("ACT-002", "Motor DC con reductora", "Actuadores", "Generico", "TT Motor", 12, 12, "Operativo", "Armario B - Estante 3"),
    ("ACT-003", "Motor paso a paso 28BYJ-48", "Actuadores", "Generico", "28BYJ-48", 6, 6, "En reparación", "Armario B - Estante 3"),
    ("CMP-001", "Protoboard 830 puntos", "Componentes electrónicos", "Generico", "MB-102", 25, 25, "Operativo", "Armario C - Estante 1"),
    ("CMP-002", "Kit de resistencias surtidas", "Componentes electrónicos", "Generico", "1/4W", 30, 30, "Operativo", "Armario C - Estante 1"),
    ("HER-001", "Multímetro digital", "Herramientas", "UNI-T", "UT39A", 6, 5, "Operativo", "Armario D - Estante 1"),
    ("HER-002", "Estación de soldadura", "Herramientas", "Weller", "WLC100", 3, 3, "Operativo", "Armario D - Estante 1"),
    ("KIT-001", "Kit LEGO Mindstorms", "Kits educativos", "LEGO", "EV3", 4, 4, "Operativo", "Armario A - Estante 3"),
]

# (nombre, apellido, dni, rol, email)
PERSONAS = [
    ("Martina", "Gómez", "40123456", "Pasante", "martina.gomez@alumnos.uai.edu.ar"),
    ("Lucas", "Fernández", "38456789", "Docente", "lucas.fernandez@uai.edu.ar"),
    ("Sofía", "Álvarez", "41987654", "Laboratorista", "sofia.alvarez@uai.edu.ar"),
    ("Nicolás", "Torres", "43210987", "Alumno", "nicolas.torres@alumnos.uai.edu.ar"),
    ("Camila", "Rodríguez", "42345678", "Alumno", "camila.rodriguez@alumnos.uai.edu.ar"),
]


def _seed(conexion):
    cursor = conexion.cursor()

    # Categorías
    ids_categoria = {}
    for nombre in CATEGORIAS:
        cursor.execute("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
        ids_categoria[nombre] = cursor.lastrowid

    # Items
    ids_item = {}
    for codigo, nombre, categoria, marca, modelo, cant_total, cant_disp, estado, ubicacion in ITEMS:
        cursor.execute(
            """
            INSERT INTO items
                (codigo, nombre, id_categoria, marca, modelo, cantidad_total,
                 cantidad_disponible, estado, ubicacion, fecha_ingreso)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                codigo, nombre, ids_categoria[categoria], marca, modelo,
                cant_total, cant_disp, estado, ubicacion,
                datetime.now().date().isoformat(),
            ),
        )
        ids_item[codigo] = cursor.lastrowid

    # Personas
    ids_persona = {}
    for nombre, apellido, dni, rol, email in PERSONAS:
        cursor.execute(
            """
            INSERT INTO personas (nombre, apellido, dni, rol, email, fecha_ingreso, activo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (nombre, apellido, dni, rol, email, datetime.now().date().isoformat()),
        )
        ids_persona[dni] = cursor.lastrowid

    # Usuario que queda como responsable del registro (si ya hay alguno cargado)
    cursor.execute("SELECT id FROM usuarios ORDER BY id LIMIT 1")
    fila_usuario = cursor.fetchone()
    id_usuario_registro = fila_usuario["id"] if fila_usuario else None

    ahora = datetime.now()

    # Préstamos: dos vigentes y uno ya devuelto
    cursor.execute(
        """
        INSERT INTO prestamos
            (id_item, id_persona, cantidad, fecha_retiro, fecha_devolucion_estimada,
             estado, id_usuario_registro, observaciones)
        VALUES (?, ?, ?, ?, ?, 'Prestado', ?, ?)
        """,
        (
            ids_item["MCU-001"], ids_persona["40123456"], 3,
            (ahora - timedelta(days=5)).isoformat(sep=" ", timespec="seconds"),
            (ahora + timedelta(days=10)).date().isoformat(),
            id_usuario_registro, "Proyecto de línea seguidora.",
        ),
    )
    cursor.execute(
        """
        INSERT INTO prestamos
            (id_item, id_persona, cantidad, fecha_retiro, fecha_devolucion_estimada,
             estado, id_usuario_registro, observaciones)
        VALUES (?, ?, ?, ?, ?, 'Prestado', ?, ?)
        """,
        (
            ids_item["SEN-001"], ids_persona["43210987"], 2,
            (ahora - timedelta(days=2)).isoformat(sep=" ", timespec="seconds"),
            (ahora + timedelta(days=13)).date().isoformat(),
            id_usuario_registro, "Trabajo práctico de sensores.",
        ),
    )
    cursor.execute(
        """
        INSERT INTO prestamos
            (id_item, id_persona, cantidad, fecha_retiro, fecha_devolucion_estimada,
             fecha_devolucion_real, estado, id_usuario_registro, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, 'Devuelto', ?, ?)
        """,
        (
            ids_item["ACT-001"], ids_persona["41987654"], 2,
            (ahora - timedelta(days=20)).isoformat(sep=" ", timespec="seconds"),
            (ahora - timedelta(days=6)).date().isoformat(),
            (ahora - timedelta(days=7)).isoformat(sep=" ", timespec="seconds"),
            id_usuario_registro, "Devuelto en buen estado.",
        ),
    )

    # Auditoría
    cursor.execute(
        """
        INSERT INTO auditoria (id_usuario, accion, modulo, detalle)
        VALUES (?, 'CARGA_DEMO', 'sistema', ?)
        """,
        (id_usuario_registro, "Carga de datos de demostración"),
    )


def seed_demo():
    inicializar_bd()

    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) AS total FROM items")
        if cursor.fetchone()["total"] > 0:
            print("[PPS] Ya existen datos cargados: no se aplica la carga de demostración.")
            return

        _seed(conexion)
        conexion.commit()
        print("[PPS] Datos de demostración cargados correctamente.")
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


if __name__ == "__main__":
    seed_demo()
