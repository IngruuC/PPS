# Sistema de Gestión CAETI – Stock de Laboratorio de Robótica

## Qué es

Aplicación de escritorio para gestionar el inventario, las personas y los
préstamos del laboratorio de robótica del CAETI (UAI). Permite controlar
qué equipamiento hay, quién lo retiró y cuándo debe devolverse, con un
sistema de usuarios y permisos por grupo.

## Requisitos

- Python 3.12 o superior.
- tkinter del sistema (no se instala vía pip):
  - macOS (Homebrew): `brew install python-tk`
  - Debian/Ubuntu: `sudo apt install python3-tk`

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

En el primer inicio, si todavía no hay ningún usuario cargado, la
aplicación muestra una pantalla para crear la cuenta de administrador
antes de habilitar el login.

## Datos de demostración

Para cargar categorías, items, personas y préstamos de ejemplo:

```bash
python -m db.seed_demo
```

El script es idempotente: si ya hay datos cargados, no hace ningún cambio.

## Estructura del proyecto

```
main.py           punto de entrada (login y ventana principal)
db/               conexión a SQLite, esquema y carga de datos demo
modules/          lógica de cada módulo (auth, inventario, personas, préstamos)
utils/            configuración visual, seguridad y auditoría
assets/           logo y recursos gráficos
```

## Módulos

- **Inventario**: alta, baja y consulta de items y categorías del laboratorio.
- **Personas**: registro de pasantes, docentes, laboratoristas y alumnos.
- **Préstamos**: retiro y devolución de items, con historial por persona.
- **Seguridad**: usuarios, grupos, permisos y auditoría de acciones.

## Estado del proyecto

Demo inicial. Pendiente: definir integración con sistemas externos (API REST)
según requerimientos.
