"""Réplica del análisis de conglomerados de la UAM. Es el test de regresión del bloque I.

FUENTE. Las tres planillas que Gabriela Dutrénit envió el 2026-08-11, en
`$RAW/UAM_Dutrenit`: `Chile_datos_Aug08_26_v1.xlsx` (el insumo, 184 filas) y
`3a`/`3b_resultados_hclust_Chile_*_v1.xlsx` (los resultados de 2003 y 2023).
Dato recibido: no se editan.

QUÉ HACE. Reconstruye las siete variables desde los niveles del insumo, las
estandariza, y vuelve a correr el agrupamiento. Verifica dos cosas y aborta si
alguna falla:

  1. los puntajes z reconstruidos coinciden con los de la planilla;
  2. la partición reproducida coincide sector por sector con la de ellos.

POR QUÉ IMPORTA. Todo lo que viene después —agregar intensidad energética,
digitalización, encadenamientos y tamaño de empresa— se mide como distancia
respecto de esta partición. Si la réplica no es exacta, cualquier cambio que se
observe podría ser de la réplica y no de las variables nuevas.

EL MÉTODO NO VENÍA CON LOS ARCHIVOS. Se infirió: Ward sobre distancia euclidiana
en las siete variables estandarizadas con desviación MUESTRAL (ddof=1), sobre el
subconjunto de sectores clasificados, dentro de cada país y período. El corte es
k=4 en 2003 y k=2 en 2023. Lo único que sigue sin ser inferible de los archivos
es el criterio de exclusión de sectores; hay que pedírselo a la UAM.

ADVERTENCIA DE LECTURA. Los nombres `x_demanda_externa` y `x_oferta_externa`
están invertidos en el original: el primero es impo/VBP (penetración importadora,
o sea oferta externa) y el segundo expo/VBP (coeficiente exportador, o sea
demanda externa). Se conservan tal cual para que la réplica sea comparable, pero
no deben leerse por su nombre.

SALIDAS. `$INTER/uam_replica_p1.csv` y `_p2.csv` con niveles, puntajes z y
conglomerado por actividad; los consume 23_cluster_ampliado.py.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage

import rutas

# Las siete variables, en el orden en que aparecen en las planillas de la UAM.
# La definición es la reconstruida contra el insumo, no la que sugiere el nombre.
VARIABLES = {
    "x_prod_trabajo": ("valor_agrega", "empleo"),      # productividad laboral
    "x_capital_trabajo": ("fbcf", "empleo"),           # FBCF por ocupado: un flujo, no un acervo
    "x_remunera_prom": ("remunera", "empleo"),         # remuneración media
    "x_demanda_externa": ("impo", "vbp"),              # penetración importadora (nombre invertido)
    "x_balanza_com": (None, None),                     # (expo - impo) EN NIVEL: la única que no es ratio
    "x_ingreso_interno": ("valor_agrega", "vbp"),      # participación del VA en la producción bruta
    "x_oferta_externa": ("expo", "vbp"),               # coeficiente exportador (nombre invertido)
}

# Corte aplicado por la UAM en cada período.
K_UAM = {1: 4, 2: 2}

TOL_Z = 1e-9  # tolerancia de la reconstrucción de los puntajes z


def variables_en_nivel(d: pd.DataFrame) -> pd.DataFrame:
    """Las siete variables en nivel, antes de estandarizar."""
    out = pd.DataFrame(index=d.index)
    for v, (num, den) in VARIABLES.items():
        if v == "x_balanza_com":
            out[v] = d["expo"] - d["impo"]
        else:
            out[v] = d[num] / d[den]
    return out


def estandarizar(x: pd.DataFrame) -> pd.DataFrame:
    """Puntajes z con desviación MUESTRAL, como en R. numpy usa ddof=0 por defecto."""
    return (x - x.mean()) / x.std(ddof=1)


def indices_rand(a, b) -> tuple[float, float]:
    """Rand y Rand ajustado entre dos particiones. Invariantes a cómo se numeren.

    Se implementan acá en vez de importar sklearn para no sumar una dependencia
    pesada por dos fórmulas de conteo de pares.
    """
    a = np.asarray(a)
    b = np.asarray(b)
    n = len(a)
    _, ia = np.unique(a, return_inverse=True)
    _, ib = np.unique(b, return_inverse=True)
    tabla = np.zeros((ia.max() + 1, ib.max() + 1), dtype=np.int64)
    np.add.at(tabla, (ia, ib), 1)

    def c2(x):
        return x * (x - 1) // 2

    sum_ij = c2(tabla).sum()
    sum_i = c2(tabla.sum(axis=1)).sum()
    sum_j = c2(tabla.sum(axis=0)).sum()
    total = c2(n)

    rand = (total + 2 * sum_ij - sum_i - sum_j) / total
    esperado = sum_i * sum_j / total
    maximo = 0.5 * (sum_i + sum_j)
    ari = (sum_ij - esperado) / (maximo - esperado) if maximo != esperado else 1.0
    return float(rand), float(ari)


def agrupar(z: pd.DataFrame, k: int) -> np.ndarray:
    """Ward sobre distancia euclidiana, cortado en k conglomerados."""
    enlace = linkage(z.to_numpy(dtype=float), method="ward", metric="euclidean")
    return fcluster(enlace, t=k, criterion="maxclust")


def main() -> int:
    rutas.preparar_directorios()
    rutas.exigir(rutas.D_UAM_INSUMO, "el insumo de la UAM")

    insumo = pd.read_excel(rutas.D_UAM_INSUMO)
    fallas = []

    for periodo in (1, 2):
        archivo = rutas.exigir(
            rutas.D_UAM_HCLUST[periodo], f"los resultados del período {periodo}"
        )
        res = pd.read_excel(archivo, sheet_name="sectores_cluster")

        d = insumo[insumo["periodo"] == periodo].set_index("codigo_3dig").sort_index()
        anio = int(d["anio"].iloc[0])

        if (d["empleo"] <= 0).any() or (d["vbp"] <= 0).any():
            print(
                f"ERROR: hay actividades con empleo o VBP no positivo en el período "
                f"{periodo}; los ratios de las siete variables no están definidos.",
                file=sys.stderr,
            )
            return 459

        # El ejercicio corre sobre el subconjunto clasificado, no sobre la COU completa.
        clasificados = res.set_index("codigo_3dig").sort_index()
        niveles = variables_en_nivel(d).loc[clasificados.index]
        z = estandarizar(niveles)

        # --- verificación 1: los puntajes z ---------------------------------
        err = (z - clasificados[list(VARIABLES)]).abs().to_numpy().max()
        estado_z = "OK" if err < TOL_Z else "FALLA"
        if err >= TOL_Z:
            fallas.append(f"período {periodo}: los puntajes z no se reconstruyen (error {err:.3g})")

        # --- verificación 2: la partición -----------------------------------
        k = K_UAM[periodo]
        propio = agrupar(z, k)
        rand, ari = indices_rand(clasificados["cluster"].to_numpy(), propio)
        estado_p = "OK" if rand == 1.0 else "FALLA"
        if rand != 1.0:
            fallas.append(f"período {periodo}: la partición no se reproduce (Rand {rand:.4f})")

        excluidas = len(d) - len(clasificados)
        va_fuera = 1 - d.loc[clasificados.index, "valor_agrega"].sum() / d["valor_agrega"].sum()
        expo_fuera = 1 - d.loc[clasificados.index, "expo"].sum() / d["expo"].sum()

        print(f"--- Período {periodo} ({anio}) ---")
        print(f"  actividades en la COU        : {len(d)}")
        print(f"  clasificadas / excluidas     : {len(clasificados)} / {excluidas}")
        print(f"  VA y expo excluidos          : {va_fuera:.1%} y {expo_fuera:.1%}")
        print(f"  reconstrucción de los z      : {estado_z} (error máximo {err:.2e})")
        print(f"  partición con k={k}, Ward     : {estado_p} (Rand {rand:.4f}, ARI {ari:.4f})")
        tam = pd.Series(propio).value_counts().sort_index().tolist()
        print(f"  tamaños de los conglomerados : {tam}")

        salida = clasificados[["desc", "cluster"]].copy()
        salida = salida.join(niveles.add_prefix("n_")).join(z)
        salida["cluster_replica"] = propio
        salida["anio"] = anio
        salida["periodo"] = periodo
        for col in ("valor_agrega", "vbp", "remunera", "empleo", "fbcf", "expo", "impo"):
            salida[col] = d.loc[clasificados.index, col]
        destino = rutas.INTER / f"uam_replica_p{periodo}.csv"
        salida.to_csv(destino, encoding="utf-8", index=True)
        print(f"  guardado                     : {destino.name}")

    if fallas:
        print("\nLa réplica NO es exacta. No seguir con el bloque I:", file=sys.stderr)
        for f in fallas:
            print(f"  · {f}", file=sys.stderr)
        return 459

    print("\nRéplica exacta en los dos períodos. El bloque I puede medirse contra ella.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
