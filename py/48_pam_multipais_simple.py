"""Bloque K.5, version simple — PAM con k = 4 en Argentina, Brasil y Mexico,
en el formato plano de T_I13 (una tabla, sin planilla con formato).

Reemplaza el formato elaborado de `47_pam_multipais.py` (T_K11, con bloques
coloreados por hoja) por el que se uso en T_I13 «PAM medoides contra Ward»: una
fila por corrida, escrita con `to_excel` sin mas formato, mas una hoja de
membresias. Un archivo POR PAIS, para no repetir la planilla de Chile —que ya
esta en T_I13/T_I27— y para poder abrir cada pais por separado.

MISMO METODO Y MISMOS DATOS que `47_pam_multipais.py`: dos especificaciones sin
logaritmos y sin ponderar, PAM Manhattan, k = 4, sobre la COU completa de cada
pais (ver el encabezado de ese script para el detalle). Aca solo cambia el
formato de salida.

SALIDA. Un archivo por pais: `T_K12 PAM k=4 <Pais>.xlsx`, con dos hojas,
`resumen` (una fila por especificacion) y `membresias` (una fila por
actividad y especificacion).

DEPENDE DE. `40_uam_metodo.py`, `41_cou_multipais.py`, `planilla_clusters.py`
y `26_pam_medoides.py`.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rutas  # noqa: E402
import planilla_clusters as pc  # noqa: E402


def _cargar_modulo(archivo: str, nombre: str):
    spec = importlib.util.spec_from_file_location(
        nombre, Path(__file__).resolve().parent / archivo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pam_mod = _cargar_modulo("26_pam_medoides.py", "pam_medoides")
uam = pc.uam

HOY = date.today().strftime("%Y.%m.%d")
K = 4

# Chile queda fuera: ya tiene T_I13 (comparacion) y T_I27 (planilla con k=4).
PAISES = [("Argentina", 1997), ("Brasil", 2003), ("Brasil", 2021),
         ("Mexico", 2008), ("Mexico", 2018)]

ESPECS = [
    ("A sin ajustes",
     dict(log=False, peso=False, balanza="nivel", sinfbcf=False, comercio=False)),
    ("B comercio ajustado",
     dict(log=False, peso=False, balanza="norm", sinfbcf=False, comercio=True)),
]


def cargar() -> pd.DataFrame:
    d = pd.read_csv(rutas.exigir(rutas.INTER / "cou_multipais.csv", "la extraccion multipais"))
    d["remunera"] = d["remunera"].fillna(0.0)
    d["codigo"] = d["codigo"].astype(str)
    return d


def extremas(d: pd.DataFrame) -> np.ndarray:
    """max |z| de cada actividad en las siete variables: sustituto del criterio
    de exclusion de la UAM (bloque K.4), usado solo para nombrar al analogo del
    cobre de cada pais."""
    r = uam.construir_variables(d, balanza="nivel")
    return np.abs(uam.estandarizar(r, uam.VARS_UAM)).max(axis=1)


def particionar(d: pd.DataFrame, k: int, **opc) -> tuple[np.ndarray, np.ndarray]:
    z, pesos = pc.matriz_z(d, **opc)
    D = pam_mod.matriz_distancias(z, "manhattan")
    _, et = pam_mod.pam(D, k, pesos)
    return pc.renumerar(et + 1, d["empleo"].to_numpy()), D


def ward(d: pd.DataFrame, k: int, **opc) -> np.ndarray:
    return pc.renumerar(pc.clasificar(d, k, **opc), d["empleo"].to_numpy())


def describir(d: pd.DataFrame, et: np.ndarray, tot: dict) -> pd.DataFrame:
    g = d.assign(_c=et).groupby("_c")
    t = pd.DataFrame({
        "n": g.size(),
        "empleo_%": 100 * g["empleo"].sum() / tot["empleo"],
        "VA_%": 100 * g["valor_agrega"].sum() / tot["valor_agrega"],
        "expo_%": 100 * g["expo"].sum() / tot["expo"] if tot["expo"] else np.nan,
    })
    t["productividad"] = 100 * (t["VA_%"] / t["empleo_%"])
    t["masa_salarial_VA_%"] = 100 * g["remunera"].sum() / g["valor_agrega"].sum()
    t.index.name = "conglomerado"
    return t


def procesar_pais(datos: pd.DataFrame, pais: str) -> None:
    filas, membres = [], []
    periodos = [(a, datos[(datos.pais == pais) & (datos.anio == a)].reset_index(drop=True))
               for p, a in PAISES if p == pais]

    for anio, d in periodos:
        if d.empty:
            print(f"  AVISO: no hay datos de {pais} {anio}")
            continue
        tot = d[["empleo", "valor_agrega", "expo"]].sum().to_dict()
        w_emp = d["empleo"].to_numpy(dtype=float)
        ext = extremas(d)
        i_ext, i_exp = int(np.argmax(ext)), int(np.argmax(d["expo"].to_numpy()))

        for nombre, opc in ESPECS:
            et, D = particionar(d, K, **opc)
            res = describir(d, et, tot)
            et_ward = ward(d, K, **opc)
            fila = {
                "pais": pais, "anio": anio, "especificacion": nombre,
                "algoritmo": "pam", "metrica": "manhattan", "unidades": len(d), "k": K,
                "tamanos (n)": " / ".join(str(x) for x in res["n"]),
                "empleo % por grupo": " / ".join(f"{x:.1f}" for x in res["empleo_%"]),
                "productividad por grupo": " / ".join(f"{x:.0f}" for x in res["productividad"]),
                "masa salarial/VA por grupo": " / ".join(
                    f"{x:.1f}" for x in res["masa_salarial_VA_%"]),
                "empleo % del mayor": float(res["empleo_%"].max()),
                "grupos con <1% del empleo": int((res["empleo_%"] < 1.0).sum()),
                "silueta ponderada": pam_mod.silueta(D, et, w_emp),
                "silueta sin ponderar": pam_mod.silueta(D, et, None),
                "eta2 log productividad": pam_mod.eta2_productividad(d, et, w_emp),
                "ARI vs Ward mismo k": uam.rand_ajustado(et, et_ward),
                "actividad extrema en": (
                    f"C{et[i_ext]} de {K}, {res.loc[et[i_ext], 'n']:.0f} actividades, "
                    f"{res.loc[et[i_ext], 'empleo_%']:.2f} % del empleo"),
                "mayor exportador en": (
                    f"C{et[i_exp]} de {K}, {res.loc[et[i_exp], 'n']:.0f} actividades, "
                    f"{res.loc[et[i_exp], 'expo_%']:.1f} % de las exportaciones"),
            }
            filas.append(fila)
            print(f"  {pais} {anio} {nombre:<22} tam {fila['tamanos (n)']:<22} "
                  f"prod {fila['productividad por grupo']:<26} "
                  f"sil {fila['silueta ponderada']:.2f} eta2 {fila['eta2 log productividad']:.3f}")

            m = d[["desc", "empleo", "valor_agrega", "expo"]].copy()
            m["conglomerado"] = et
            m["empleo_%"] = 100 * m["empleo"] / tot["empleo"]
            m["expo_%"] = 100 * m["expo"] / tot["expo"] if tot["expo"] else np.nan
            m["productividad"] = ((100 * m["valor_agrega"] / tot["valor_agrega"])
                                  / (m["empleo"] / tot["empleo"]))
            m["especificacion"] = f"{anio} · {nombre}"
            m.insert(0, "pais", pais)
            membres.append(m.reset_index(drop=True))

    if not filas:
        return
    resumen = pd.DataFrame(filas)
    memb = pd.concat(membres, ignore_index=True)
    destino = rutas.OUT / f"{HOY} T_K12 PAM k=4 {pais}.xlsx"
    with pd.ExcelWriter(destino) as w:
        resumen.to_excel(w, sheet_name="resumen", index=False)
        memb.to_excel(w, sheet_name="membresias", index=False)
    print(f"  escrito: {destino}\n")


def main() -> None:
    rutas.preparar_directorios()
    pam_mod.verificar()
    datos = cargar()
    for pais in ("Argentina", "Brasil", "Mexico"):
        procesar_pais(datos, pais)


if __name__ == "__main__":
    main()
