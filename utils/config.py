"""
PPS - CAETI (UAI)
Configuración general: paleta de colores institucional, fuentes y rutas de recursos.

Todos los módulos de la interfaz importan estos valores desde acá,
para que la app tenga siempre la misma identidad visual.
"""

import os

# ------------------------------------------------------------
# RUTAS
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_uai.png")

# ------------------------------------------------------------
# PALETA DE COLORES - CAETI / UAI (bordo, blanco, negro)
# ------------------------------------------------------------
COLOR_BORDO = "#6E2A32"          # color principal: headers, sidebar, botones
COLOR_BORDO_OSCURO = "#4A1B21"   # hover, texto sobre fondo claro
COLOR_FONDO = "#F7F6F4"          # fondo general de las pantallas
COLOR_FONDO_TARJETA = "#FFFFFF"  # fondo de tarjetas/tablas
COLOR_TEXTO = "#242424"          # texto principal
COLOR_TEXTO_CLARO = "#FFFFFF"    # texto sobre fondos oscuros (bordo)
COLOR_GRIS = "#8A8A8A"           # bordes, texto secundario/deshabilitado
COLOR_GRIS_CLARO = "#D9D7D4"     # separadores, bordes suaves
COLOR_ALERTA = "#9C3B3B"         # botones de eliminar / errores
COLOR_EXITO = "#5C7A5C"          # confirmaciones / éxito

# ------------------------------------------------------------
# TIPOGRAFÍA
# ------------------------------------------------------------
FUENTE_PRINCIPAL = "Segoe UI"
TAMANO_TITULO = 22
TAMANO_SUBTITULO = 16
TAMANO_TEXTO = 13
TAMANO_TEXTO_CHICO = 11

# ------------------------------------------------------------
# DATOS INSTITUCIONALES
# ------------------------------------------------------------
NOMBRE_APP = "Sistema de Gestión CAETI"
SUBTITULO_APP = "Universidad Abierta Interamericana"