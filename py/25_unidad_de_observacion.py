"""La unidad de observación del agrupamiento: agregar la manufactura, o ponderar.

EL PROBLEMA. El `hclust` de la UAM trata a cada actividad de la COU como una
observación con el mismo peso. En 2023 la manufactura son 39 de las 101
actividades clasificadas —38,6 % de las observaciones— y 7,5 % del empleo
clasificado. La partición no la decide sólo la estructura productiva: la decide
también el nivel de desagregación con que el Banco Central abre cada rama. El
mismo defecto hace incomparables 2003 (73 actividades) y 2023 (111).

DOS ARREGLOS. (1) AGREGAR: llevar la manufactura a 8 grupos —o a uno— para que
su número de observaciones se parezca a su peso económico. Es el ejercicio que
ya estaba hecho y que este archivo reconstruye. (2) PONDERAR: dejar las 101
actividades y darle a cada una un peso proporcional a su tamaño.

CÓMO SE PONDERA. Tres piezas, no una:
  1. la estandarización, con media y desviación PONDERADAS;
  2. el criterio de fusión de Ward, con las masas de los conglomerados
     reemplazadas por la suma de pesos: coste = (W_A·W_B/(W_A+W_B))·||c_A−c_B||²;
  3. la lectura, que ya se hacía en porcentaje del empleo.
Ward con pesos de frecuencia es idéntico a replicar cada observación w veces.
scipy no admite pesos, así que el agrupamiento se implementa directo: con 101
observaciones el aglomerativo ingenuo es instantáneo. Con w = 1 tiene que
devolver la partición de la UAM, y eso se verifica antes de seguir.

LA PRUEBA QUE DECIDE. Partir una actividad en tres pedazos idénticos no cambia
la economía, sólo la nomenclatura. Se mide cuánto se mueve la partición en ese
experimento: sin ponderar, mucho; ponderando y con la balanza comercial
normalizada por VBP, nada.

DEPENDE DE. `20_replica_hclust.py` (la réplica exacta es el punto de partida).

SALIDAS. T_I9 (resumen de especificaciones), T_I10 y T_I11 (membresías de 2023
y 2003) y F_I4 en `$OUT`.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import rutas

VARIABLES = [
    "x_prod_trabajo", "x_capital_trabajo", "x_remunera_prom", "x_demanda_externa",
    "x_balanza_com", "x_ingreso_interno", "x_oferta_externa",
]
SUMABLES = ["valor_agrega", "vbp", "remunera", "empleo", "fbcf", "expo", "impo"]
ANIO = {1: 2003, 2: 2023}

# ---------------------------------------------------------------------------
# La manufactura en ocho grupos. El corte sigue las divisiones CIIU tal como las
# abre cada COU: no es una agregación inventada, es el nivel inmediatamente
# superior de la propia nomenclatura.
# ---------------------------------------------------------------------------
MANUF = {
    2: {  # COU base 2018, 39 actividades manufactureras clasificadas
        "MANUF Alimentos": [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
        "MANUF Bebidas": [30, 31, 32, 33],
        "MANUF Textil, vestuario, cuero y calzado": [35, 36, 37, 38],
        "MANUF Madera, celulosa, papel e imprentas": [39, 40, 41, 42, 43, 44],
        "MANUF Química": [46, 47, 48, 49, 50],
        "MANUF Plástico y minerales no metálicos": [52, 53, 54, 55],
        "MANUF Metálicas básicas y productos metálicos": [56, 57, 58],
        "MANUF Muebles, otras manufacturas y reparación": [62, 63],
    },
    1: {  # COU base 2003, 30 actividades manufactureras clasificadas
        "MANUF Alimentos": [11, 12, 13, 14, 15, 16, 17, 18, 20],
        "MANUF Bebidas": [21, 22, 23, 24],
        "MANUF Textil, vestuario, cuero y calzado": [26, 27, 28, 29],
        "MANUF Madera, celulosa, papel e imprentas": [30, 31, 32],
        "MANUF Química": [34, 35],
        "MANUF Plástico y minerales no metálicos": [37, 38, 39],
        "MANUF Metálicas básicas y productos metálicos": [40, 41, 42],
        "MANUF Muebles y otras manufacturas": [46, 47],
    },
}

# Cuatro maneras defendibles de llevar la manufactura de 2023 a ocho grupos. Todas
# respetan las divisiones CIIU; lo que cambia es dónde se ponen las costuras. Sirven
# para medir cuánto del resultado agregado depende del criterio y no de los datos.
AGRUPACIONES_ALT = {
    "a) alimentos · bebidas · textil · madera-papel · química · plástico-minerales · "
    "metálicas · muebles-otras": MANUF[2],
    "b) madera con muebles, papel aparte, química con plástico": {
        "MANUF Alimentos": [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
        "MANUF Bebidas": [30, 31, 32, 33],
        "MANUF Textil, vestuario, cuero y calzado": [35, 36, 37, 38],
        "MANUF Madera y muebles": [39, 40, 62],
        "MANUF Papel, celulosa e imprentas": [41, 42, 43, 44],
        "MANUF Química y plástico": [46, 47, 48, 49, 50, 52],
        "MANUF Minerales no metálicos": [53, 54, 55],
        "MANUF Metálicas, productos metálicos y otras": [56, 57, 58, 63],
    },
    "c) madera con celulosa, muebles con metálicas": {
        "MANUF Alimentos": [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
        "MANUF Bebidas": [30, 31, 32, 33],
        "MANUF Textil, vestuario, cuero y calzado": [35, 36, 37, 38],
        "MANUF Madera y celulosa": [39, 40, 41],
        "MANUF Papel e imprentas": [42, 43, 44],
        "MANUF Química y plástico": [46, 47, 48, 49, 50, 52],
        "MANUF Minerales no metálicos": [53, 54, 55],
        "MANUF Metálicas, muebles y otras": [56, 57, 58, 62, 63],
    },
    "d) textil separado de cuero-calzado, química con minerales": {
        "MANUF Alimentos": [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
        "MANUF Bebidas": [30, 31, 32, 33],
        "MANUF Textil y vestuario": [35, 36],
        "MANUF Cuero y calzado": [37, 38],
        "MANUF Madera": [39, 40],
        "MANUF Papel, celulosa e imprentas": [41, 42, 43, 44],
        "MANUF Química, plástico y minerales no metálicos": [46, 47, 48, 49, 50, 52, 53, 54, 55],
        "MANUF Metálicas, muebles y otras": [56, 57, 58, 62, 63],
    },
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Calibri", "DejaVu Sans"],
    "figure.dpi": 130,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


# ---------------------------------------------------------------------------
# Variables, estandarización y agrupamiento — las tres con peso
# ---------------------------------------------------------------------------
def variables_en_nivel(d: pd.DataFrame, balanza_normalizada: bool = False) -> pd.DataFrame:
    """Las siete variables de la UAM, recalculadas desde los niveles.

    `balanza_normalizada` reemplaza (expo − impo) EN NIVEL por (expo − impo)/VBP.
    Es la única de las siete que no es un ratio, y por eso la única que cambia de
    valor cuando una actividad se parte en pedazos.
    """
    out = pd.DataFrame(index=d.index)
    out["x_prod_trabajo"] = d["valor_agrega"] / d["empleo"]
    out["x_capital_trabajo"] = d["fbcf"] / d["empleo"]
    out["x_remunera_prom"] = d["remunera"] / d["empleo"]
    out["x_demanda_externa"] = d["impo"] / d["vbp"]
    out["x_balanza_com"] = ((d["expo"] - d["impo"]) / d["vbp"] if balanza_normalizada
                            else d["expo"] - d["impo"])
    out["x_ingreso_interno"] = d["valor_agrega"] / d["vbp"]
    out["x_oferta_externa"] = d["expo"] / d["vbp"]
    return out


def estandarizar(x: pd.DataFrame, w: np.ndarray | None = None) -> pd.DataFrame:
    """Puntajes z. Sin peso, desviación muestral (como en R). Con peso, momentos
    ponderados: si no se pondera también acá, la métrica sigue calibrada sobre la
    dispersión de las actividades chicas."""
    if w is None:
        return (x - x.mean()) / x.std(ddof=1)
    w = np.asarray(w, dtype=float)
    w = w / w.sum()
    m = (x.mul(w, axis=0)).sum()
    v = (((x - m) ** 2).mul(w, axis=0)).sum()
    return (x - m) / np.sqrt(v)


def ward_ponderado(z: np.ndarray, w: np.ndarray, k: int) -> np.ndarray:
    """Ward de mínima varianza con pesos de frecuencia, cortado en k grupos.

    Coste de fusionar A y B: (W_A·W_B/(W_A+W_B))·||c_A−c_B||²; el centroide
    resultante es la media ponderada. Con w = 1 es exactamente el Ward de scipy.
    Las etiquetas se numeran por masa descendente para que los cuadros se lean
    igual entre especificaciones.
    """
    n = len(z)
    cent = np.asarray(z, dtype=float).copy()
    masa = np.asarray(w, dtype=float).copy()
    miembros = [{i} for i in range(n)]
    vivos = list(range(n))

    while len(vivos) > k:
        mejor, par = np.inf, None
        for ii, a in enumerate(vivos):
            for b in vivos[ii + 1:]:
                dif = cent[a] - cent[b]
                coste = (masa[a] * masa[b] / (masa[a] + masa[b])) * float(dif @ dif)
                if coste < mejor:
                    mejor, par = coste, (a, b)
        a, b = par
        cent[a] = (masa[a] * cent[a] + masa[b] * cent[b]) / (masa[a] + masa[b])
        masa[a] += masa[b]
        miembros[a] |= miembros[b]
        vivos.remove(b)

    etiqueta = np.zeros(n, dtype=int)
    for nuevo, a in enumerate(sorted(vivos, key=lambda x: -masa[x]), start=1):
        for i in miembros[a]:
            etiqueta[i] = nuevo
    return etiqueta


def indices_rand(a, b) -> tuple[float, float]:
    a, b = np.asarray(a), np.asarray(b)
    n = len(a)
    _, ia = np.unique(a, return_inverse=True)
    _, ib = np.unique(b, return_inverse=True)
    t = np.zeros((ia.max() + 1, ib.max() + 1), dtype=np.int64)
    np.add.at(t, (ia, ib), 1)
    c2 = lambda x: x * (x - 1) // 2
    sij, si, sj, tot = c2(t).sum(), c2(t.sum(1)).sum(), c2(t.sum(0)).sum(), c2(n)
    esp, mx = si * sj / tot, 0.5 * (si + sj)
    return (float((tot + 2 * sij - si - sj) / tot),
            float((sij - esp) / (mx - esp) if mx != esp else 1.0))


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
def cargar(periodo: int) -> tuple[pd.DataFrame, dict]:
    """La réplica (actividades clasificadas) y los totales de la COU completa.

    Los porcentajes y el índice de productividad se calculan contra la ECONOMÍA
    ENTERA, incluidas las actividades excluidas del agrupamiento; es la base con
    que están escritos los cuadros de la nota de lectura de las planillas.
    """
    d = pd.read_csv(rutas.exigir(rutas.INTER / f"uam_replica_p{periodo}.csv",
                                 "la réplica; correr antes 20_replica_hclust.py"),
                    index_col=0)
    d.index = d.index.astype(str)
    insumo = pd.read_excel(rutas.exigir(rutas.D_UAM_INSUMO, "el insumo de la UAM"))
    tot = insumo[insumo["periodo"] == periodo][SUMABLES].sum().to_dict()
    return d, tot


def agregar_manufactura(d: pd.DataFrame, mapa: dict, en_uno: bool) -> pd.DataFrame:
    """Colapsa la manufactura sumando NIVELES y recalculando después los ratios.

    Sumar los ratios sería incorrecto: la productividad de un grupo es el cociente
    de las sumas, no la suma de los cocientes.
    """
    clave = pd.Series(d.index, index=d.index)
    for nombre, codigos in mapa.items():
        presentes = [str(c) for c in codigos if str(c) in d.index]
        clave.loc[presentes] = "MANUF (toda)" if en_uno else nombre

    g = d.groupby(clave)
    agg = g[SUMABLES].sum()
    agg["n_actividades"] = g.size()
    agg["desc"] = [sub["desc"].iloc[0] if len(sub) == 1 else k
                   for k, sub in d.groupby(clave)]
    agg.index.name = "clave"
    return agg


def niveles_de(base: pd.DataFrame, balanza_normalizada: bool = False) -> pd.DataFrame:
    return variables_en_nivel(base, balanza_normalizada)


# ---------------------------------------------------------------------------
# Descripción de una partición
# ---------------------------------------------------------------------------
def describir(d: pd.DataFrame, etiquetas, tot: dict) -> pd.DataFrame:
    g = d.assign(_c=etiquetas).groupby("_c")
    t = pd.DataFrame({
        "n": g.size(),
        "empleo_%": 100 * g["empleo"].sum() / tot["empleo"],
        "VA_%": 100 * g["valor_agrega"].sum() / tot["valor_agrega"],
        "expo_%": 100 * g["expo"].sum() / tot["expo"],
    })
    t["productividad"] = 100 * (t["VA_%"] / t["empleo_%"])
    t["masa_salarial_VA_%"] = 100 * g["remunera"].sum() / g["valor_agrega"].sum()
    t.index.name = "conglomerado"
    return t


def membresias(d: pd.DataFrame, etiquetas, tot: dict, spec: str) -> pd.DataFrame:
    out = d[["desc", "empleo", "valor_agrega", "expo"]].copy()
    out["conglomerado"] = etiquetas
    out["empleo_%"] = 100 * out["empleo"] / tot["empleo"]
    out["expo_%"] = 100 * out["expo"] / tot["expo"]
    out["productividad"] = (100 * (out["valor_agrega"] / tot["valor_agrega"])
                            / (out["empleo"] / tot["empleo"]))
    out["n_actividades"] = d["n_actividades"] if "n_actividades" in d.columns else 1
    out["especificacion"] = spec
    return out.reset_index()


def imprimir(titulo: str, resumen: pd.DataFrame, d: pd.DataFrame, etiquetas) -> None:
    print(f"\n{'-' * 78}\n{titulo}\n{'-' * 78}")
    print(resumen.round(1).to_string())
    dd = d.assign(_c=etiquetas)
    for c in sorted(pd.unique(etiquetas)):
        sub = dd[dd["_c"] == c].sort_values("empleo", ascending=False)
        print(f"\n  C{c} ({len(sub)} unidades):")
        for _, r in sub.iterrows():
            print(f"      {r['desc'][:62]:64s} {r['empleo']:>10,.0f}")


# ---------------------------------------------------------------------------
def main() -> int:
    rutas.preparar_directorios()
    filas, membres, para_figura = [], [], {}

    for periodo in (2, 1):
        anio = ANIO[periodo]
        d, tot = cargar(periodo)
        mapa = MANUF[periodo]
        manuf = [str(c) for cod in mapa.values() for c in cod if str(c) in d.index]
        print(f"\n{'=' * 78}\nPERÍODO {periodo} ({anio}) — {len(d)} actividades clasificadas")
        print(f"Manufactura: {len(manuf)} actividades = {100*len(manuf)/len(d):.1f} % de las "
              f"observaciones y {100*d.loc[manuf,'empleo'].sum()/tot['empleo']:.1f} % del "
              f"empleo de la economía\n{'=' * 78}")

        uno = np.ones(len(d))
        k_uam = 4 if periodo == 1 else 2

        # Control: con peso unitario el Ward propio tiene que dar la partición de la UAM.
        ctrl = ward_ponderado(estandarizar(niveles_de(d)).to_numpy(), uno, k_uam)
        rand_ctrl = indices_rand(d["cluster"].to_numpy(), ctrl)[0]
        print(f"Control: Ward propio con peso unitario contra la UAM → Rand {rand_ctrl:.4f} "
              f"{'OK' if rand_ctrl == 1.0 else 'FALLA'}")
        if rand_ctrl != 1.0:
            print("  El agrupamiento ponderado no reproduce el original con w=1. Parar acá.")
            return 459

        d8 = agregar_manufactura(d, mapa, en_uno=False)
        d1 = agregar_manufactura(d, mapa, en_uno=True)
        w_emp, w_va = d["empleo"].to_numpy(), d["valor_agrega"].to_numpy()

        # (etiqueta, base, peso, k, balanza normalizada, mostrar en detalle)
        especificaciones = (
            [(f"UAM, {len(d)} actividades, k={k}", d, uno, k, False, k == k_uam)
             for k in (2, 3, 4, 5)]
            + [(f"Manufactura en 8 grupos, {len(d8)} unidades, k={k}", d8,
                np.ones(len(d8)), k, False, k == 4) for k in (2, 3, 4, 5)]
            + [(f"Manufactura en 1 grupo, {len(d1)} unidades, k={k}", d1,
                np.ones(len(d1)), k, False, k == 4) for k in (3, 4)]
            + [(f"Ponderado por empleo, {len(d)} actividades, k={k}", d, w_emp, k, False, k == 4)
               for k in (2, 3, 4, 5)]
            + [(f"Ponderado por VA, {len(d)} actividades, k={k}", d, w_va, k, False, False)
               for k in (3, 4)]
            + [(f"Ponderado por raíz del empleo, {len(d)} actividades, k={k}", d,
                np.sqrt(w_emp), k, False, False) for k in (3, 4)]
            + [(f"Ponderado por empleo + balanza/VBP, {len(d)} actividades, k={k}", d,
                w_emp, k, True, k == 4) for k in (3, 4)]
        )

        for nombre, base, peso, k, bal, detalle in especificaciones:
            hay_peso = not np.allclose(peso, peso[0])
            zz = estandarizar(niveles_de(base, bal), peso if hay_peso else None)
            et = ward_ponderado(zz.to_numpy(), peso, k)
            res = describir(base, et, tot)
            if len(base) == len(d):
                rand, ari = indices_rand(base["cluster"].to_numpy(), et)
            else:
                rand, ari = np.nan, np.nan
            filas.append({
                "anio": anio, "especificacion": nombre, "unidades": len(base), "k": k,
                "tamaños (n unidades)": " / ".join(str(x) for x in res["n"].tolist()),
                "empleo % por grupo": " / ".join(f"{x:.1f}" for x in res["empleo_%"]),
                "VA % por grupo": " / ".join(f"{x:.1f}" for x in res["VA_%"]),
                "expo % por grupo": " / ".join(f"{x:.1f}" for x in res["expo_%"]),
                "productividad por grupo": " / ".join(f"{x:.0f}" for x in res["productividad"]),
                "masa salarial/VA por grupo": " / ".join(
                    f"{x:.1f}" for x in res["masa_salarial_VA_%"]),
                "Rand vs UAM": rand, "ARI vs UAM": ari,
            })
            print(f"  {nombre:58s} tam {filas[-1]['tamaños (n unidades)']:20s} "
                  f"prod {filas[-1]['productividad por grupo']}")

            if detalle:
                imprimir(f"{anio} · {nombre}", res, base, et)
                membres.append(membresias(base, et, tot, f"{anio} · {nombre}"))
                if periodo == 2:
                    para_figura[nombre] = (res, base, et)

        # -------------------------------------------------------------------
        # ¿Cuánto del resultado agregado lo decide el criterio de agrupación?
        # -------------------------------------------------------------------
        if periodo == 2:
            print(f"\n--- Cuatro maneras de llevar la manufactura a 8 grupos, k=4 ({anio}) ---")
            fuera = [i for i in d.index if i not in
                     {str(c) for cod in mapa.values() for c in cod}]
            particiones = {}
            for etiq, alt in AGRUPACIONES_ALT.items():
                da = agregar_manufactura(d, alt, en_uno=False)
                et = ward_ponderado(estandarizar(niveles_de(da)).to_numpy(),
                                    np.ones(len(da)), 4)
                res = describir(da, et, tot)
                particiones[etiq] = pd.Series(et, index=da.index).loc[fuera]
                print(f"  {etiq[:58]:60s} n {list(res['n'])} "
                      f"prod {[round(x) for x in res['productividad']]}")
                filas.append({
                    "anio": anio, "especificacion": f"[agrupación alternativa] {etiq}",
                    "unidades": len(da), "k": 4,
                    "tamaños (n unidades)": " / ".join(str(x) for x in res["n"]),
                    "empleo % por grupo": " / ".join(f"{x:.1f}" for x in res["empleo_%"]),
                    "productividad por grupo": " / ".join(
                        f"{x:.0f}" for x in res["productividad"]),
                })
            claves = list(particiones)
            print(f"  ARI entre variantes, sobre las {len(fuera)} actividades NO "
                  f"manufactureras (las que ninguna agrupación toca):")
            for i, a in enumerate(claves):
                for b in claves[i + 1:]:
                    ari = indices_rand(particiones[a].to_numpy(), particiones[b].to_numpy())[1]
                    print(f"      {a[:2]} vs {b[:2]}: {ari:.3f}")
                    filas.append({"anio": anio,
                                  "especificacion": f"[ARI entre agrupaciones] {a[:2]} vs {b[:2]}",
                                  "unidades": len(fuera), "k": 4, "ARI vs UAM": ari})

        # -------------------------------------------------------------------
        # Con la COU completa: ¿ponderar hace innecesario excluir sectores?
        # -------------------------------------------------------------------
        # La exclusión del cobre y los otros nueve es un arreglo contra los
        # outliers. Ponderar es otro: una actividad de 0,56 % del empleo ya no
        # puede definir un conglomerado por sí sola, esté donde esté en el
        # espacio de las variables.
        insumo = pd.read_excel(rutas.D_UAM_INSUMO)
        full = insumo[insumo["periodo"] == periodo].set_index("codigo_3dig").sort_index()
        full.index = full.index.astype(str)
        zf_sin = estandarizar(niveles_de(full))
        wf = full["empleo"].to_numpy()
        zf_con = estandarizar(niveles_de(full, True), wf)
        print(f"\n--- COU completa ({len(full)} actividades), con los excluidos adentro "
              f"({anio}) ---")
        clave_cobre = [i for i in full.index
                       if "cobre" in rutas.normalizar(str(full.loc[i, "desc"]))]
        for etiq, zz, ww in (("sin ponderar", zf_sin, np.ones(len(full))),
                             ("ponderando + balanza/VBP", zf_con, wf)):
            for k in (2, 4):
                et = ward_ponderado(zz.to_numpy(), ww, k)
                res = describir(full, et, tot)
                s = pd.Series(et, index=full.index)
                donde = (f"C{s.loc[clave_cobre[0]]} de {k}, con "
                         f"{(s == s.loc[clave_cobre[0]]).sum()} actividades"
                         if clave_cobre else "s/d")
                print(f"    {etiq:26s} k={k}: n {list(res['n'])} "
                      f"emp% {[round(x, 1) for x in res['empleo_%']]} "
                      f"prod {[round(x) for x in res['productividad']]} · cobre en {donde}")
                filas.append({
                    "anio": anio, "especificacion": f"[COU completa] {etiq}, k={k}",
                    "unidades": len(full), "k": k,
                    "tamaños (n unidades)": " / ".join(str(x) for x in res["n"]),
                    "empleo % por grupo": " / ".join(f"{x:.1f}" for x in res["empleo_%"]),
                    "productividad por grupo": " / ".join(
                        f"{x:.0f}" for x in res["productividad"]),
                    "donde queda el cobre": donde,
                })

        # -------------------------------------------------------------------
        # La prueba de invariancia: partir en clones no cambia la economía
        # -------------------------------------------------------------------
        grandes = d["empleo"].nlargest(5).index
        clones = []
        for i, r in d.iterrows():
            veces = 3 if i in grandes else 1
            for j in range(veces):
                s = r.copy()
                for col in SUMABLES:
                    s[col] = r[col] / veces
                s.name = f"{i}_{j}"
                clones.append(s)
        dc = pd.DataFrame(clones)
        prim = [f"{i}_0" for i in d.index]
        print(f"\n--- Invariancia: las 5 actividades de más empleo partidas en 3 clones "
              f"idénticos ({anio}) ---")
        print(f"    {', '.join(d.loc[grandes, 'desc'])}")
        for k in (2, 4):
            pruebas = {
                "sin ponderar": (uno, np.ones(len(dc)), False),
                "ponderando por empleo": (w_emp, dc["empleo"].to_numpy(), False),
                "ponderando + balanza/VBP": (w_emp, dc["empleo"].to_numpy(), True),
            }
            fila = {"anio": anio, "especificacion": f"[invariancia a clonar] k={k}",
                    "unidades": len(dc), "k": k}
            for etiq, (wo, wc, bal) in pruebas.items():
                hay = not np.allclose(wo, wo[0])
                a = ward_ponderado(
                    estandarizar(niveles_de(d, bal), wo if hay else None).to_numpy(), wo, k)
                b = ward_ponderado(
                    estandarizar(niveles_de(dc, bal), wc if hay else None).to_numpy(), wc, k)
                ari = indices_rand(a, pd.Series(b, index=dc.index).loc[prim].to_numpy())[1]
                fila[f"ARI {etiq}"] = ari
                print(f"    k={k}  {etiq:26s} ARI {ari:.3f}")
            filas.append(fila)

    resumen = pd.DataFrame(filas)
    resumen.to_excel(rutas.tabla("T_I9 unidad de observacion agregar o ponderar"), index=False)
    memb = pd.concat(membres, ignore_index=True)
    for anio, nombre in ((2023, "T_I10 membresias por especificacion 2023"),
                         (2003, "T_I11 membresias por especificacion 2003")):
        memb[memb["especificacion"].str.startswith(str(anio))].to_excel(
            rutas.tabla(nombre), index=False)

    figura(para_figura)
    print(f"\nTablas y figura escritas en {rutas.OUT}")
    return 0


def figura(para_figura: dict) -> None:
    """Empleo y productividad de cada conglomerado, en las cuatro especificaciones."""
    orden = [k for k in para_figura if k.startswith(("UAM", "Manufactura en 8",
                                                     "Ponderado por empleo,"))]
    orden += [k for k in para_figura if k.startswith("Ponderado por empleo +")]
    if not orden:
        return
    fig, axes = plt.subplots(1, len(orden), figsize=(3.4 * len(orden), 4.0), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, nombre in zip(axes, orden):
        res, _, _ = para_figura[nombre]
        ax.bar(range(len(res)), res["productividad"], color="#4C72B0", alpha=0.85)
        for i, (p, e) in enumerate(zip(res["productividad"], res["empleo_%"])):
            ax.text(i, p + 6, f"{e:.0f} %", ha="center", fontsize=8)
        ax.axhline(100, color="#C44E52", lw=1, ls="--")
        ax.set_xticks(range(len(res)))
        ax.set_xticklabels([f"C{c}" for c in res.index])
        ax.set_title("\n".join(nombre.split(", ")[:2]), fontsize=9)
    axes[0].set_ylabel("VA por ocupado, economía = 100")
    fig.suptitle("Qué conglomerados aparecen según cómo se defina la unidad de observación "
                 "(2023)", fontsize=11.5)
    fig.text(0.5, -0.05,
             "Sobre cada barra, el porcentaje del empleo de la economía que reúne el "
             "conglomerado. Línea roja: la media de la economía.\nWard sobre distancia "
             "euclidiana en las siete variables de la UAM estandarizadas; en las columnas "
             "ponderadas, momentos y masas ponderados por el empleo.",
             ha="center", fontsize=7.5, color="#444444")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_I4 unidad de observacion", ext), bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
