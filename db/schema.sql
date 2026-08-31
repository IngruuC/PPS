-- ============================================================
-- PPS - CAETI (UAI) - Esquema de Base de Datos (SQLite)
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- SEGURIDAD: grupos, permisos, usuarios
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS grupos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL UNIQUE,
    descripcion     TEXT,
    fecha_creacion  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permisos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo          TEXT NOT NULL,
    accion          TEXT NOT NULL,
    UNIQUE(modulo, accion)
);

CREATE TABLE IF NOT EXISTS grupo_permisos (
    id_grupo    INTEGER NOT NULL,
    id_permiso  INTEGER NOT NULL,
    PRIMARY KEY (id_grupo, id_permiso),
    FOREIGN KEY (id_grupo)   REFERENCES grupos(id)   ON DELETE CASCADE,
    FOREIGN KEY (id_permiso) REFERENCES permisos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usuarios (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_usuario    TEXT NOT NULL UNIQUE,
    password_hash     TEXT NOT NULL,
    salt              TEXT NOT NULL,
    nombre_completo   TEXT NOT NULL,
    email             TEXT,
    id_grupo          INTEGER NOT NULL,
    activo            INTEGER NOT NULL DEFAULT 1,
    fecha_creacion    DATETIME DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso     DATETIME,
    FOREIGN KEY (id_grupo) REFERENCES grupos(id)
);

-- ------------------------------------------------------------
-- PERSONAS (pasantes, laboratoristas, docentes, etc.)
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS personas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    apellido        TEXT NOT NULL,
    dni             TEXT,
    rol             TEXT NOT NULL,
    email           TEXT,
    telefono        TEXT,
    fecha_ingreso   DATE,
    activo          INTEGER NOT NULL DEFAULT 1,
    observaciones   TEXT,
    id_usuario      INTEGER,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- INVENTARIO: categorías e items
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS categorias (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS items (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                TEXT NOT NULL UNIQUE,
    nombre                TEXT NOT NULL,
    id_categoria          INTEGER,
    marca                 TEXT,
    modelo                TEXT,
    cantidad_total         INTEGER NOT NULL DEFAULT 1,
    cantidad_disponible    INTEGER NOT NULL DEFAULT 1,
    estado                TEXT NOT NULL DEFAULT 'Operativo',
    ubicacion             TEXT,
    fecha_ingreso         DATE,
    observaciones         TEXT,
    FOREIGN KEY (id_categoria) REFERENCES categorias(id)
);

-- ------------------------------------------------------------
-- PRÉSTAMOS: quién retiró qué item y si lo devolvió
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS prestamos (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_item                   INTEGER NOT NULL,
    id_persona                INTEGER NOT NULL,
    cantidad                  INTEGER NOT NULL DEFAULT 1,
    fecha_retiro              DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_devolucion_estimada DATE,
    fecha_devolucion_real     DATETIME,
    estado                    TEXT NOT NULL DEFAULT 'Prestado',
    id_usuario_registro       INTEGER,
    observaciones             TEXT,
    FOREIGN KEY (id_item) REFERENCES items(id),
    FOREIGN KEY (id_persona) REFERENCES personas(id),
    FOREIGN KEY (id_usuario_registro) REFERENCES usuarios(id)
);

-- ------------------------------------------------------------
-- AUDITORÍA: registro de todas las acciones del sistema
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS auditoria (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario  INTEGER,
    accion      TEXT NOT NULL,
    modulo      TEXT NOT NULL,
    detalle     TEXT,
    fecha_hora  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id)
);