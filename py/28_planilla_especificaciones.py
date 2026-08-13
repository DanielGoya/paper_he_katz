"""Bloque I.7 — la clasificacion de la UAM y ocho especificaciones alternativas,
en una sola planilla con el formato de los libros 3a y 3b.

Una hoja por especificacion. Cada hoja lleva los dos periodos LADO A LADO, con
las cinco columnas de identificacion de `sectores_cluster` de la UAM
(pais, periodo, cluster, codigo_3dig, desc) y nada mas. Los conglomerados van
marcados por color de fila y separados por un borde grueso.

La hoja `1 UAM (base)` reproduce la clasificacion recibida: k = 4 en 2003 y
k = 2 en 2023, tal como vienen los libros 3a y 3b. Las ocho alternativas corren
todas con **k = 4** en los dos periodos, que es el corte que justifican el salto
de costes de Ward (bloque I.5) y el eta cuadrado (bloque I.6).

⚠ El universo son las 62 y 101 actividades que la UAM dejo adentro, o sea que
esta planilla HEREDA su criterio de exclusion, que no conocemos. `py/29` corre lo
mismo sobre la COU completa y `py/31` sobre la COU menos cuatro artefactos
contables, con el k recalculado en cada hoja.

El formato y las especificaciones viven en `planilla_clusters.py`.

Entrada:  datos/intermediate/uam_replica_p{1,2}.csv  (los produce py/20)
Salida:   datos/output/2026.08.13 T_I22 clasificacion en nueve especificaciones.xlsx
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
SALIDA = rutas.OUT / "2026.08.13 T_I22 clasificacion en nueve especificaciones.xlsx"

BASE = "1 UAM (base)"
DESC_BASE = ("Clasificacion recibida de la UAM (libros 3a y 3b). Siete variables en niveles, "
             "sin ponderar, balanza comercial en niveles. k = 4 en 2003 y k = 2 en 2023.")


def cargar(periodo: int) -> pd.DataFrame:
    d = pd.read_csv(rutas.exigir(rutas.INTER / f"uam_replica_p{periodo}.csv",
                                 f"la replica del periodo {periodo}"))
    d["codigo_3dig"] = d["codigo_3dig"].astype(str)
    return d


def main() -> None:
    rutas.preparar_directorios()
    d1, d2 = cargar(1), cargar(2)

    wb = Workbook()
    wb.remove(wb.active)

    def hoja(nombre, cl1, cl2, nota_k):
        bs = []
        for p, d, anio, cl in ((1, d1, 2003, cl1), (2, d2, 2023, cl2)):
            bs.append((pc.bloque(d, p, cl), f"Periodo {p} — {anio}"))
        desc = pc.DESCRIPCION[nombre] if nombre in pc.DESCRIPCION else DESC_BASE
        pc.escribir_hoja(wb, nombre, [(desc + " " + nota_k, "000000")], bs)

    # --- Hoja 1: la clasificacion recibida, sin recalcular nada -------------
    hoja(BASE, d1["cluster"].to_numpy(), d2["cluster"].to_numpy(),
         "Los numeros de conglomerado son los del archivo original.")
    resumen = [(BASE, str(d1["cluster"].nunique()), str(d2["cluster"].nunique()),
                "clasificacion recibida")]

    # --- Hojas 2 a 9: las especificaciones alternativas ---------------------
    for nombre, opc in pc.ESPECIFICACIONES:
        cl1 = pc.renumerar(pc.clasificar(d1, K, **opc), d1["empleo"].to_numpy())
        cl2 = pc.renumerar(pc.clasificar(d2, K, **opc), d2["empleo"].to_numpy())
        hoja(nombre, cl1, cl2,
             f"k = {K} en los dos periodos; conglomerados numerados de mayor a menor empleo.")
        ari1 = pc.uam.rand_ajustado(d1["cluster"], cl1)
        ari2 = pc.uam.rand_ajustado(d2["cluster"], cl2)
        resumen.append((nombre,
                        " / ".join(str(n) for n in pd.Series(cl1).value_counts().sort_index()),
                        " / ".join(str(n) for n in pd.Series(cl2).value_counts().sort_index()),
                        f"ARI contra la UAM: {ari1:.3f} (2003) · {ari2:.3f} (2023)"))

    # --- Hoja de lectura, al principio --------------------------------------
    ws = wb.create_sheet("0 Lectura", 0)
    ws.cell(1, 1, "T_I22 — la clasificacion en nueve especificaciones").font = Font(bold=True, size=13)
    ws.cell(2, 1, "62 actividades clasificadas en 2003 y 101 en 2023 (las que la UAM no excluyo). "
                  "Fuente: datos/intermediate/uam_replica_p{1,2}.csv, py/20.").font = Font(italic=True, size=9)
    for j, h in enumerate(["hoja", "tamanos 2003", "tamanos 2023", "nota"]):
        c = ws.cell(4, 1 + j, h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="404040")
    for i, fila in enumerate(resumen):
        for j, v in enumerate(fila):
            ws.cell(5 + i, 1 + j, v)
        ws.cell(5 + i, 1).font = Font(bold=True)
        ws.cell(5 + i, 6, pc.DESCRIPCION.get(fila[0], DESC_BASE))
    for col, w in zip("ABCDEF", (30, 18, 18, 42, 3, 110)):
        ws.column_dimensions[col].width = w

    wb.save(SALIDA)
    print(f"escrito: {SALIDA}")
    for f in resumen:
        print(f"  {f[0]:<30} 2003 {f[1]:<18} 2023 {f[2]:<18} {f[3]}")


if __name__ == "__main__":
    main()
