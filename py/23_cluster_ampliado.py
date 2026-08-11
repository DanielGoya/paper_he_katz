"""Las variables nuevas, usadas de las dos maneras: caracterizando y agrupando.

CAPA A. Las variables nuevas describen los conglomerados de la UAM sin tocar la
partición. Es lo que ellos pueden pegar en el capítulo 3 sin rehacer nada, y para los
cuatro países, porque las tres primeras salen de la MIP.

CAPA B. Las variables nuevas entran a la matriz de distancias y se vuelve a agrupar. Se
reporta cuánto cambia la partición al agregar una variable a la vez y todas juntas.

POR QUÉ LAS DOS. El pedido de Gabriela —«incorporar algunas variables más»— se lee como
la capa B. Pero agregar columnas a un agrupamiento de Ward sobre variables estandarizadas
no es gratis: con siete variables cada una aporta un séptimo de la distancia, con once
aporta un onceavo. Un cambio de partición puede venir de la información nueva o de la
dilución del peso de las viejas, y la única forma de distinguirlo es reportar las dos
capas y el índice de Rand variable por variable.

DEPENDE DE. `20_replica_hclust.py` (que la partición se reproduzca es el requisito) y
`22_variables_nuevas.py`.

SALIDAS. Tablas T_I1 a T_I5 y figuras F_I1 y F_I2 en `$OUT`.
"""

from __future__ import annotations

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import rutas

VARIABLES_UAM = [
    "x_prod_trabajo", "x_capital_trabajo", "x_remunera_prom", "x_demanda_externa",
    "x_balanza_com", "x_ingreso_interno", "x_oferta_externa",
]

NUEVAS = {
    "x_intens_energ": "Intensidad energética",
    "x_digital": "Digitalización",
    "x_encadena": "Encadenamiento hacia atrás",
    "x_tam_empresa": "Tamaño medio de empresa",
}

K_UAM = {1: 4, 2: 2}
ANIO = {1: 2003, 2: 2023}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Calibri", "DejaVu Sans"],
    "figure.dpi": 130,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def estandarizar(x: pd.DataFrame) -> pd.DataFrame:
    return (x - x.mean()) / x.std(ddof=1)


def agrupar(z: pd.DataFrame, k: int) -> np.ndarray:
    from scipy.cluster.hierarchy import fcluster, linkage
    enlace = linkage(z.to_numpy(dtype=float), method="ward", metric="euclidean")
    return fcluster(enlace, t=k, criterion="maxclust")


def indices_rand(a, b) -> tuple[float, float]:
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    _, ia = np.unique(a, return_inverse=True)
    _, ib = np.unique(b, return_inverse=True)
    t = np.zeros((ia.max() + 1, ib.max() + 1), dtype=np.int64)
    np.add.at(t, (ia, ib), 1)
    c2 = lambda x: x * (x - 1) // 2
    sij, si, sj, tot = c2(t).sum(), c2(t.sum(1)).sum(), c2(t.sum(0)).sum(), c2(n)
    rand = (tot + 2 * sij - si - sj) / tot
    esp, mx = si * sj / tot, 0.5 * (si + sj)
    return float(rand), float((sij - esp) / (mx - esp) if mx != esp else 1.0)


def cargar(periodo: int) -> pd.DataFrame:
    rep = pd.read_csv(rutas.exigir(rutas.INTER / f"uam_replica_p{periodo}.csv",
                                   "la réplica; correr antes 20_replica_hclust.py"),
                      index_col=0)
    nue = pd.read_csv(rutas.exigir(rutas.INTER / f"variables_nuevas_p{periodo}.csv",
                                   "las variables nuevas; correr antes 22_variables_nuevas.py"),
                      index_col=0)
    return rep.join(nue[list(NUEVAS) + ["x_digital_amplio", "x_encadena_adelante"]])


def main() -> int:
    rutas.preparar_directorios()
    tablas, resumen_b = {}, []

    for periodo in (1, 2):
        anio = ANIO[periodo]
        d = cargar(periodo)
        print(f"\n{'=' * 66}\nPERÍODO {periodo} ({anio}) — {len(d)} actividades clasificadas\n{'=' * 66}")

        faltan = d[list(NUEVAS)].isna().sum()
        if faltan.any():
            print("Actividades sin dato:", ", ".join(
                f"{k} = {v}" for k, v in faltan.items() if v))
            for col in list(NUEVAS):
                if d[col].isna().any():
                    for r in d[d[col].isna()].itertuples():
                        print(f"    {col}: {r.desc}")

        # ------------------------------------------------------------------
        # CAPA A — caracterización de los conglomerados de la UAM
        # ------------------------------------------------------------------
        print("\n--- CAPA A: los conglomerados de la UAM, descritos con las variables nuevas ---")
        g = d.groupby("cluster")
        capa_a = pd.DataFrame({
            "n": g.size(),
            "empleo_%": 100 * g["empleo"].sum() / d["empleo"].sum(),
            "VA_%": 100 * g["valor_agrega"].sum() / d["valor_agrega"].sum(),
            "expo_%": 100 * g["expo"].sum() / d["expo"].sum(),
            "productividad": (g["valor_agrega"].sum() / g["empleo"].sum())
                             / (d["valor_agrega"].sum() / d["empleo"].sum()) * 100,
        })
        # Ponderadas por VBP (energía, digital) y por empleo (tamaño), que es como se leen.
        for col in ("x_intens_energ", "x_digital"):
            capa_a[col] = 100 * g.apply(
                lambda x, c=col: (x[c] * x["vbp"]).sum() / x["vbp"].sum(), include_groups=False)
        capa_a["x_encadena"] = g.apply(
            lambda x: (x["x_encadena"] * x["vbp"]).sum() / x["vbp"].sum(), include_groups=False)
        capa_a["x_tam_empresa"] = g.apply(
            lambda x: (x["x_tam_empresa"] * x["empleo"]).sum()
            / x.loc[x["x_tam_empresa"].notna(), "empleo"].sum(), include_groups=False)
        capa_a.index.name = "conglomerado"
        print(capa_a.round(2).to_string())
        tablas[f"T_I1 caracterizacion de conglomerados {anio}"] = capa_a.reset_index()

        # ------------------------------------------------------------------
        # Correlaciones: ¿las variables nuevas son información nueva?
        # ------------------------------------------------------------------
        print("\n--- Correlación de cada variable nueva con las siete de la UAM ---")
        corr = d[VARIABLES_UAM + list(NUEVAS)].corr(method="spearman")
        sub = corr.loc[list(NUEVAS), VARIABLES_UAM]
        print(sub.round(2).to_string())
        peor = sub.abs().max(axis=1)
        for v in NUEVAS:
            con = sub.loc[v].abs().idxmax()
            print(f"  {v:16s} máxima |rho| = {peor[v]:.2f} con {con}")
        tablas[f"T_I2 correlaciones variables nuevas {anio}"] = corr.reset_index()

        # Asimetría: el problema que ya tiene el ejercicio con x_balanza_com.
        asim = d[VARIABLES_UAM + list(NUEVAS)].skew().sort_values(ascending=False)
        print("\n--- Asimetría (las variables muy sesgadas dominan la distancia euclidiana) ---")
        print("  " + " · ".join(f"{k}: {v:.1f}" for k, v in asim.head(5).items()))

        # ------------------------------------------------------------------
        # CAPA B — las variables nuevas entran al agrupamiento
        # ------------------------------------------------------------------
        print("\n--- CAPA B: cuánto cambia la partición al agregar cada variable ---")
        k = K_UAM[periodo]
        original = d["cluster"].to_numpy()
        filas = []
        combinaciones = [("(sólo las 7 de la UAM)", [])] + \
                        [(NUEVAS[v], [v]) for v in NUEVAS] + \
                        [("las 4 juntas", list(NUEVAS))]

        for etiqueta, extra in combinaciones:
            cols = VARIABLES_UAM + extra
            dd = d[cols].dropna()
            z = estandarizar(dd)
            part = agrupar(z, k)
            rand, ari = indices_rand(original[d.index.isin(dd.index)], part)
            tam = np.bincount(part)[1:]
            filas.append({
                "especificación": etiqueta,
                "n variables": len(cols),
                "n actividades": len(dd),
                "Rand": rand,
                "Rand ajustado": ari,
                "tamaños": " / ".join(str(x) for x in sorted(tam, reverse=True)),
            })
            print(f"  {etiqueta:28s} p={len(cols):2d}  Rand {rand:.3f}  ARI {ari:.3f}  "
                  f"tamaños {filas[-1]['tamaños']}")
        capa_b = pd.DataFrame(filas)
        tablas[f"T_I3 sensibilidad de la particion {anio}"] = capa_b
        resumen_b.append((anio, capa_b))

        # ------------------------------------------------------------------
        # El placebo que separa información de dilución
        # ------------------------------------------------------------------
        # Pasar de 7 a 11 variables estandarizadas reparte la distancia entre más
        # dimensiones, y eso solo ya mueve la partición aunque las variables nuevas no
        # digan nada. La prueba: permutar las cuatro variables nuevas entre actividades
        # —se conserva su distribución marginal y se rompe su relación con el sector— y
        # ver cuánto cambia la partición por el puro efecto de agregar cuatro columnas.
        real = capa_b.loc[capa_b["especificación"] == "las 4 juntas", "Rand ajustado"].iloc[0]
        dd = d[VARIABLES_UAM + list(NUEVAS)].dropna()
        base_orig = original[d.index.isin(dd.index)]
        rng = np.random.default_rng(20260811)
        nulos = []
        for _ in range(200):
            perm = dd.copy()
            for v in NUEVAS:
                perm[v] = rng.permutation(perm[v].to_numpy())
            nulos.append(indices_rand(base_orig, agrupar(estandarizar(perm), k))[1])
        nulos = np.array(nulos)
        p = float((nulos <= real).mean())
        print(f"\n--- Placebo: ¿la partición cambia por información o por dilución? ({anio}) ---")
        print(f"  ARI observado con las 4 variables reales : {real:.3f}")
        print(f"  ARI con las 4 permutadas (200 réplicas)  : mediana {np.median(nulos):.3f}, "
              f"rango 5-95% [{np.percentile(nulos, 5):.3f}, {np.percentile(nulos, 95):.3f}]")
        print(f"  proporción de placebos que cambian tanto o más que las reales: {p:.1%}")
        veredicto = ("el cambio de partición NO se distingue de la pura dilución"
                     if p > 0.10 else
                     "el cambio de partición excede lo que produce la pura dilución")
        print(f"  → {veredicto}")
        tablas[f"T_I6 placebo dilucion {anio}"] = pd.DataFrame([{
            "anio": anio, "ARI observado": real,
            "ARI placebo mediana": float(np.median(nulos)),
            "ARI placebo p5": float(np.percentile(nulos, 5)),
            "ARI placebo p95": float(np.percentile(nulos, 95)),
            "proporcion placebos <= observado": p,
            "replicas": len(nulos), "veredicto": veredicto,
        }])

        # ------------------------------------------------------------------
        # Sensibilidad al corte, con las once variables
        # ------------------------------------------------------------------
        print(f"\n--- Sensibilidad al número de conglomerados, con las 11 variables ({anio}) ---")
        dd = d[VARIABLES_UAM + list(NUEVAS)].dropna()
        z = estandarizar(dd)
        filas_k = []
        for kk in range(2, 7):
            part = agrupar(z, kk)
            rand, ari = indices_rand(original[d.index.isin(dd.index)], part)
            tam = sorted(np.bincount(part)[1:], reverse=True)
            emp = d.loc[dd.index].groupby(part)["empleo"].sum()
            emp = (100 * emp / emp.sum()).round(1).sort_values(ascending=False).tolist()
            filas_k.append({"k": kk, "tamaños": " / ".join(map(str, tam)),
                            "empleo %": " / ".join(map(str, emp)),
                            "Rand vs UAM": rand, "ARI": ari})
            print(f"  k={kk}: tamaños {filas_k[-1]['tamaños']:24s} "
                  f"empleo % {filas_k[-1]['empleo %']}")
        tablas[f"T_I4 sensibilidad al corte {anio}"] = pd.DataFrame(filas_k)

        # ------------------------------------------------------------------
        # La partición con las once variables, actividad por actividad
        # ------------------------------------------------------------------
        salida = d[["desc", "cluster", "empleo", "valor_agrega", "expo"] + list(NUEVAS)].copy()
        salida["cluster_11var"] = pd.Series(agrupar(z, k), index=dd.index)
        tablas[f"T_I5 actividades con variables nuevas {anio}"] = salida.reset_index()

        if periodo == 2:
            figura_capa_a(d, anio)

    figura_capa_b(resumen_b)

    for nombre, t in tablas.items():
        destino = rutas.tabla(nombre)
        t.to_excel(destino, index=False)
    print(f"\n{len(tablas)} tablas escritas en {rutas.OUT}")
    return 0


def figura_capa_a(d: pd.DataFrame, anio: int) -> None:
    """Las cuatro variables nuevas, por conglomerado de la UAM."""
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6))
    clusters = sorted(d["cluster"].unique())
    colores = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
    for ax, (col, titulo) in zip(axes, NUEVAS.items()):
        datos = [d.loc[d["cluster"] == c, col].dropna() for c in clusters]
        bp = ax.boxplot(datos, patch_artist=True, widths=0.55,
                        medianprops=dict(color="black"), showfliers=False)
        for parche, color in zip(bp["boxes"], colores):
            parche.set_facecolor(color)
            parche.set_alpha(0.55)
        for i, (c, serie) in enumerate(zip(clusters, datos), start=1):
            ax.scatter(np.random.default_rng(c).normal(i, 0.06, len(serie)), serie,
                       s=9, color="black", alpha=0.45, zorder=3)
        ax.set_title(titulo, fontsize=10)
        ax.set_xticks(range(1, len(clusters) + 1))
        ax.set_xticklabels([f"C{c}" for c in clusters])
        if col in ("x_intens_energ", "x_digital"):
            ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        if col == "x_tam_empresa":
            ax.set_yscale("log")
    fig.suptitle(f"Las variables que faltaban, por conglomerado de la UAM ({anio})",
                 fontsize=11.5)
    fig.text(0.5, -0.04,
             "Intensidad energética y digitalización: consumo intermedio del grupo de productos "
             "sobre VBP, COU del Banco Central.\nTamaño de empresa: trabajadores por empresa, "
             "SII, en escala logarítmica. Encadenamiento: índice de Rasmussen hacia atrás.",
             ha="center", fontsize=7.5, color="#444444")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_I1 variables nuevas por conglomerado", ext),
                    bbox_inches="tight")
    plt.close(fig)


def figura_capa_b(resumen: list) -> None:
    """Cuánto cambia la partición al agregar cada variable."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for ax, (anio, t) in zip(axes, resumen):
        t = t[t["especificación"] != "(sólo las 7 de la UAM)"]
        y = np.arange(len(t))
        ax.barh(y, t["Rand ajustado"], color="#4C72B0", alpha=0.85, height=0.6)
        ax.set_yticks(y)
        ax.set_yticklabels(t["especificación"], fontsize=9)
        ax.invert_yaxis()
        ax.set_xlim(0, 1.02)
        ax.axvline(1.0, color="#C44E52", lw=1, ls="--")
        ax.set_title(f"{anio}", fontsize=11)
        ax.set_xlabel("Índice de Rand ajustado contra la partición de la UAM")
        for i, v in enumerate(t["Rand ajustado"]):
            ax.text(min(v + 0.015, 0.98), i, f"{v:.2f}", va="center", fontsize=8.5)
    fig.suptitle("Agregar una variable no cambia la partición por igual en los dos períodos",
                 fontsize=11.5)
    fig.text(0.5, -0.06,
             "Ward sobre distancia euclidiana en las siete variables de la UAM más la indicada, "
             "estandarizadas dentro del período.\nLa línea roja es la partición original: 1,0 "
             "significa que agregar la variable no movió a ningún sector de conglomerado.",
             ha="center", fontsize=7.5, color="#444444")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_I2 cuanto cambia la particion", ext), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
