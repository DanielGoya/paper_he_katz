"""Resolución de rutas de la capa de conglomerados. Gemelo de `config/rutas.do`.

ÚNICO archivo de `py/` con rutas absolutas, igual que el .do lo es para Stata.
Es el equivalente de anclas.yaml del gestor: lo único que cambia entre los tres PCs.

Regla del proyecto: los datos se LEEN del almacén general y NO se copian al repo;
las salidas se ESCRIBEN al árbol de artefactos, fuera del repo.

Si un ancla falta, `exigir()` se cae con mensaje claro. Nunca se adivina.
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Anclas de esta instalación
# ---------------------------------------------------------------------------
A_DROPBOX = Path("D:/Dropbox")
A_REPOS = Path("D:/repos")

# ---------------------------------------------------------------------------
# 2. Raíces derivadas
# ---------------------------------------------------------------------------
REPO = A_REPOS / "paper_he_katz"
ALMACEN = A_DROPBOX / "Recursos" / "Datos"            # datos de terceros, compartidos
ARTEF = A_DROPBOX / "Trabajo" / "Paper HE Katz"       # árbol de artefactos del proyecto

RAW = ARTEF / "datos" / "raw_local"
INTER = ARTEF / "datos" / "intermediate"
OUT = ARTEF / "datos" / "output"
SCRATCH = ARTEF / "datos" / "scratch"

CONFIG = REPO / "config"
DOCS = A_DROPBOX / "Obsidian" / "Trabajo" / "paper-he-katz"

# ---------------------------------------------------------------------------
# 3. Punteros a las bases (referenciar, nunca copiar)
# ---------------------------------------------------------------------------
# Planillas de la UAM: dato recibido el 2026-08-11, no se editan nunca.
D_UAM = RAW / "UAM_Dutrenit"
D_UAM_INSUMO = D_UAM / "Chile_datos_Aug08_26_v1.xlsx"
D_UAM_HCLUST = {
    1: D_UAM / "3a_resultados_hclust_Chile_1_v1.xlsx",   # 2003, 73 actividades
    2: D_UAM / "3b_resultados_hclust_Chile_2_v1.xlsx",   # 2023, 111 actividades
}

# Estadísticas de Empresas del SII, 2005-2024. `PUB_TRAM_ACT` es la actividad a
# seis dígitos CIIU4.CL por trece tramos de venta: es la que da tamaño medio de
# empresa a nivel de las actividades de la COU. `PUB_TRAM_RUBR` sólo llega a las
# 21 secciones y es la que usa src/08_productividad_sii.do.
D_SII = ALMACEN / "SII" / "2026.08.10 Estadisticas de empresas"
D_SII_ACT = D_SII / "PUB_TRAM_ACT.csv"
D_SII_RUBR = D_SII / "PUB_TRAM_RUBR.csv"

# Cuadros de Oferta y Utilización y Matriz Insumo-Producto del Banco Central.
# Compilación de referencia 2018 para 2023 (111 actividades) y 2003 para 2003 (73).
D_BCCH = ALMACEN / "Banco Central de Chile"

# Registro de Emisiones y Transferencias de Contaminantes (MMA), y Balance
# Nacional de Energía (Ministerio de Energía): validación física de la
# intensidad energética de la MIP. Sólo Chile.
D_RETC = ALMACEN / "RETC"
D_BNE = ALMACEN / "Balance Nacional de Energia"

# Concordancias de nomenclatura, versionadas en el repo para que sean auditables
# y corregibles a mano sin tocar código.
D_CONC_COU_CIIU = CONFIG / "concordancia_cou_ciiu4cl.csv"

# ---------------------------------------------------------------------------
# 4. Convención de salidas: tablas con fecha, figuras sin ella
# ---------------------------------------------------------------------------
FECHA = "2026.08.11"


def tabla(nombre: str) -> Path:
    """Ruta de una tabla de salida: `$OUT/AAAA.MM.DD T_I1 descripcion.xlsx`."""
    return OUT / f"{FECHA} {nombre}.xlsx"


def figura(nombre: str, ext: str) -> Path:
    """Ruta de una figura de salida: `$OUT/F_I1 descripcion.png` (y .pdf)."""
    return OUT / f"{nombre}.{ext}"


# ---------------------------------------------------------------------------
# 5. Utilidades comunes
# ---------------------------------------------------------------------------
def exigir(ruta: Path, que: str) -> Path:
    """Verificación fail-fast: parar acá y no más adelante."""
    if not ruta.exists():
        print(f"ERROR: no se encuentra {que} en:\n  {ruta}", file=sys.stderr)
        print("Revisar las anclas A_DROPBOX / A_REPOS en py/rutas.py.", file=sys.stderr)
        raise SystemExit(601)
    return ruta


def hay(ruta: Path) -> bool:
    """Igual que `exigir`, pero para bloques que se saltan limpiamente si falta la fuente."""
    return ruta.exists()


def normalizar(texto: str) -> str:
    """Texto comparable entre nomenclaturas: sin tildes, sin puntuación, en minúsculas.

    Se usa para calzar descripciones de actividad entre la COU del Banco Central,
    la planilla de la UAM y los rubros del SII, donde el mismo sector aparece
    escrito de tres formas distintas.
    """
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = "".join(c if c.isalnum() or c.isspace() else " " for c in t)
    return " ".join(t.split())


def preparar_directorios() -> None:
    for d in (INTER, OUT, SCRATCH):
        d.mkdir(parents=True, exist_ok=True)
