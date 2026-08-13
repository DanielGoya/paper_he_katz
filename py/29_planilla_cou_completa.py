"""Bloque I.8 — la misma planilla de nueve especificaciones, pero SIN EXCLUIR
ninguna actividad: las 73 de 2003 y las 111 de 2023 de la COU completa.

Gemela de `py/28_planilla_especificaciones.py`, con una sola diferencia de
fondo: el universo. `py/28` clasifica las 62 y 101 actividades que la UAM dejo
adentro, heredando un criterio de exclusion que **no conocemos** —el cobre, los
combustibles, los servicios de vivienda y otras—. Aca se clasifica todo, incluida
la hoja base: es el ejercicio de la UAM tal cual, corrido sobre la matriz entera.

Las actividades que la UAM excluyo van marcadas en rojo y cursiva, para poder
ver de un vistazo en que conglomerado cae cada una.

El formato de la planilla y las especificaciones viven en `planilla_clusters.py`,
compartidos con `py/28` y `py/31`.

Entrada:  datos/raw_local/UAM_Dutrenit/Chile_datos_Aug08_26_v1.xlsx  (el insumo)
          datos/intermediate/uam_replica_p{1,2}.csv  (solo para saber cuales excluyo)
Salida:   datos/output/2026.08.13 T_I23 clasificacion sin excluir sectores.xlsx
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rutas  # noqa: E402
import planilla_clusters as pc  # noqa: E402

K = 4
# El corte con que la UAM reporto cada periodo. La hoja base lo respeta; las
# ocho alternativas van todas con k = 4.
K_UAM = {1: 4, 2: 2}
SALIDA = rutas.OUT / "2026.08.13 T_I23 clasificacion sin excluir sectores.xlsx"

BASE = "1 UAM sin excluir"
DESC_BASE = ("La especificacion de la UAM intacta —siete variables en niveles, sin ponderar, "
             "balanza comercial en niveles— corrida sobre la COU COMPLETA, con las actividades "
             "que ellos excluyeron adentro. k = 4 en 2003 y k = 2 en 2023, los cortes que ellos "
             "reportan.")


def cargar(periodo: int) -> tuple[pd.DataFrame, set[str]]:
    """La COU completa del periodo, y el conjunto de codigos que la UAM excluyo."""
    d = pd.read_excel(rutas.exigir(rutas.D_UAM_INSUMO, "el insumo de la UAM"))
    d = d[d["periodo"] == periodo].copy()
    d["codigo_3dig"] = d["codigo_3dig"].astype(str)
    d = d.reset_index(drop=True)

    r = pd.read_csv(rutas.exigir(rutas.INTER / f"uam_replica_p{periodo}.csv",
                                 "la replica; correr antes 20_replica_hclust.py"))
    return d, set(d["codigo_3dig"]) - set(r["codigo_3dig"].astype(str))


def main() -> None:
    rutas.preparar_directorios()
    d1, ex1 = cargar(1)
    d2, ex2 = cargar(2)
    print(f"2003: {len(d1)} actividades, {len(ex1)} excluidas por la UAM")
    print(f"2023: {len(d2)} actividades, {len(ex2)} excluidas por la UAM")

    wb = Workbook()
    wb.remove(wb.active)
    resumen = []

    def agregar(nombre, k1, k2, opc, nota_k):
        bs, diag = [], []
        for p, d, ex, anio, k in ((1, d1, ex1, 2003, k1), (2, d2, ex2, 2023, k2)):
            cl = pc.renumerar(pc.clasificar(d, k, **opc), d["empleo"].to_numpy())
            b = pc.bloque(d, p, cl, ex)
            bs.append((b, f"Periodo {p} — {anio} ({len(d)} actividades)"))
            diag.append(pc.diagnostico(b, d))
        desc = pc.DESCRIPCION[nombre] if nombre in pc.DESCRIPCION else DESC_BASE
        notas = [
            (desc + " " + nota_k, "000000"),
            ("En rojo y cursiva, las actividades que la UAM excluyo de su ejercicio "
             "(11 en 2003, 10 en 2023).", pc.ROJO),
        ]
        pc.escribir_hoja(wb, nombre, notas, bs, con_marca=True)
        resumen.append((nombre, *diag[0], *diag[1]))

    # --- Hoja 1: la especificacion de la UAM sobre la COU completa ----------
    agregar(BASE, K_UAM[1], K_UAM[2],
            dict(log=False, peso=False, balanza="nivel", sinfbcf=False),
            f"k = {K_UAM[1]} en 2003 y k = {K_UAM[2]} en 2023; conglomerados numerados de "
            "mayor a menor empleo.")

    # --- Hojas 2 a 9 --------------------------------------------------------
    for nombre, opc in pc.ESPECIFICACIONES:
        agregar(nombre, K, K, opc,
                f"k = {K} en los dos periodos; conglomerados numerados de mayor a menor empleo.")

    # --- Hoja de lectura ----------------------------------------------------
    ws = wb.create_sheet("0 Lectura", 0)
    ws.cell(1, 1, "T_I23 — la clasificacion en nueve especificaciones, SIN EXCLUIR sectores"
            ).font = Font(bold=True, size=13)
    ws.cell(2, 1, "Las 73 actividades de 2003 y las 111 de 2023 de la COU completa, incluidas el "
                  "cobre y las demas que la UAM dejo fuera con un criterio que no conocemos. "
                  "Fuente: Chile_datos_Aug08_26_v1.xlsx. Gemela de T_I22, que clasifica solo las "
                  "62 y 101 que ellos dejaron adentro.").font = Font(italic=True, size=9)
    ws.cell(3, 1, "La columna 'grupos < 1 % del empleo' cuenta los conglomerados que la "
                  "especificacion gasta en actividades marginales: es el sintoma del problema "
                  "que la exclusion pretendia resolver.").font = Font(italic=True, size=9)
    enc = ["hoja", "tamanos 2003", "% empleo 2003", "grupos <1% 2003",
           "tamanos 2023", "% empleo 2023", "grupos <1% 2023", "", "que hace"]
    for j, h in enumerate(enc):
        c = ws.cell(5, 1 + j, h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="404040")
    for i, fila in enumerate(resumen):
        for j, v in enumerate(fila):
            ws.cell(6 + i, 1 + j, v)
        ws.cell(6 + i, 1).font = Font(bold=True)
        ws.cell(6 + i, 9, pc.DESCRIPCION.get(fila[0], DESC_BASE))
    for col, w in zip("ABCDEFGHI", (30, 20, 24, 15, 20, 24, 15, 3, 110)):
        ws.column_dimensions[col].width = w

    wb.save(SALIDA)
    print(f"\nescrito: {SALIDA}\n")
    for f in resumen:
        print(f"  {f[0]:<30} 2003 {f[1]:<18} [{f[2]:<22}] <1%: {f[3]}"
              f"   2023 {f[4]:<18} [{f[5]:<22}] <1%: {f[6]}")


if __name__ == "__main__":
    main()
