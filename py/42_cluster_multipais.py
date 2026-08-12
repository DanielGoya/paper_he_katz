"""Bloque K.2 — aplica a Argentina, Brasil y Mexico los criterios con que la UAM
agrupo las actividades de Chile, y compara.

Corre tres especificaciones sobre cada pais y periodo:

  UAM        las siete variables, sin ponderar, balanza en niveles. Es la que
             reproduce exactamente la particion chilena (Rand = 1,0000).
  mejorada   balanza normalizada (X-M)/(X+M), ponderacion por empleo y
             logaritmos en productividad y remuneracion media.
  reducida   las cinco variables que salen solo de la COU, sin empleo ni
             remuneraciones. Es lo unico que admite la COU argentina reciente.

Salidas: T_K1 a T_K5 y F_K1 en datos/output.
"""

from __future__ import annotations

import importlib.util
import os
from datetime import date

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('uam', os.path.join(AQUI, '40_uam_metodo.py'))
uam = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uam)

import rutas   # noqa: E402  (el modulo del metodo se carga por ruta: empieza con digito)

INTER = rutas.INTER
OUT = rutas.OUT
# rutas.FECHA marca el lote del bloque I (2026.08.11). El bloque K es su propio
# lote: se fecha aparte para no renombrar las tablas ya escritas.
HOY = date.today().strftime('%Y.%m.%d')

ORDEN = [('Chile', 2003), ('Chile', 2023), ('Brasil', 2003), ('Brasil', 2021),
         ('Mexico', 2008), ('Mexico', 2018), ('Argentina', 1997)]


def cargar() -> pd.DataFrame:
    d = pd.read_csv(rutas.exigir(INTER / 'cou_multipais.csv', 'la extraccion multipais'))
    # Una actividad sin remuneraciones declaradas rompe el logaritmo y no aporta
    # informacion; se conserva con remuneracion cero, que es lo que dice la fuente.
    d['remunera'] = d['remunera'].fillna(0.0)
    return d


# --------------------------------------------------------------------------
# Validacion: la receta de extraccion contra el archivo de la UAM
# --------------------------------------------------------------------------

def validar_chile() -> pd.DataFrame:
    """Compara la particion desde la COU publicada con la de la UAM."""
    filas = []
    for per, f, k in ((1, 'uam_replica_p1.csv', 4), (2, 'uam_replica_p2.csv', 2)):
        d = pd.read_csv(INTER / f)
        r = uam.construir_variables(d, balanza='nivel')
        cl = uam.agrupar(r, uam.VARS_UAM, k)
        filas.append({
            'periodo': per, 'anio': int(d['anio'].iloc[0]), 'n': len(d), 'k': k,
            'Rand': round(uam.rand_simple(cl, d['cluster']), 4),
            'Rand ajustado': round(uam.rand_ajustado(cl, d['cluster']), 4),
            'tamanos UAM': '/'.join(map(str, sorted(
                d['cluster'].value_counts().tolist(), reverse=True))),
            'tamanos replica': '/'.join(map(str, sorted(
                pd.Series(cl).value_counts().tolist(), reverse=True))),
        })
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# Caracterizacion de una particion
# --------------------------------------------------------------------------

def caracterizar(d: pd.DataFrame, cl: np.ndarray, etiqueta: str) -> pd.DataFrame:
    d = d.copy()
    d['cl'] = cl
    tot_emp = d['empleo'].sum()
    tot_va = d['valor_agrega'].sum()
    tot_x = d['expo'].sum()
    prod_media = tot_va / tot_emp
    filas = []
    for c, g in d.groupby('cl'):
        prod = (g['valor_agrega'].sum() / g['empleo'].sum()) / prod_media * 100
        filas.append({
            'especificacion': etiqueta, 'conglomerado': int(c), 'n': len(g),
            '% empleo': 100 * g['empleo'].sum() / tot_emp,
            '% VA': 100 * g['valor_agrega'].sum() / tot_va,
            '% exportaciones': 100 * g['expo'].sum() / tot_x if tot_x else np.nan,
            'productividad (economia=100)': prod,
            'masa salarial / VA (%)': 100 * g['remunera'].sum() / g['valor_agrega'].sum(),
            'actividad mayor': g.sort_values('empleo', ascending=False)['desc'].iloc[0][:52],
        })
    out = pd.DataFrame(filas).sort_values('% empleo', ascending=False)
    return out


# --------------------------------------------------------------------------
# Las tres especificaciones
# --------------------------------------------------------------------------

def particion(d: pd.DataFrame, spec: str, k: int) -> np.ndarray:
    if spec == 'UAM':
        r = uam.construir_variables(d, balanza='nivel')
        return uam.agrupar(r, uam.VARS_UAM, k)
    if spec == 'mejorada':
        r = uam.construir_variables(d, balanza='norm')
        r = uam.transformar_logs(r, uam.VARS_UAM)
        return uam.agrupar(r, uam.VARS_UAM, k, pesos=d['empleo'].to_numpy(float))
    if spec == 'reducida':
        r = uam.construir_variables(d, balanza='norm')
        return uam.agrupar(r, uam.VARS_COU, k)
    raise ValueError(spec)


def main():
    rutas.preparar_directorios()
    datos = cargar()

    # ---- T_K2: validacion del metodo y de la receta
    val = validar_chile()
    print('\n== Validacion sobre Chile (metodo de la UAM, insumo de la UAM) ==')
    print(val.to_string(index=False))

    # ---- T_K1: la especificacion de la UAM, pais por pais
    caracts, resumen = [], []
    for pais, anio in ORDEN:
        d = datos[(datos.pais == pais) & (datos.anio == anio)].reset_index(drop=True)
        if d.empty:
            continue
        for k in (2, 3, 4):
            cl = particion(d, 'UAM', k)
            c = caracterizar(d, cl, f'UAM k={k}')
            c.insert(0, 'anio', anio)
            c.insert(0, 'pais', pais)
            caracts.append(c)
            tam = sorted(pd.Series(cl).value_counts().tolist(), reverse=True)
            emp = (pd.DataFrame({'cl': cl, 'e': d['empleo']})
                   .groupby('cl').e.sum().sort_values(ascending=False))
            resumen.append({
                'pais': pais, 'anio': anio, 'n actividades': len(d), 'k': k,
                'tamanos': '/'.join(map(str, tam)),
                '% empleo del mayor': round(100 * emp.iloc[0] / emp.sum(), 1),
                'grupos con <1% del empleo': int((100 * emp / emp.sum() < 1).sum()),
                'actividades en esos grupos': int(sum(
                    tam[i] for i, v in enumerate(emp.values) if 100 * v / emp.sum() < 1)),
            })
    T_K1 = pd.concat(caracts, ignore_index=True)
    T_K3 = pd.DataFrame(resumen)

    print('\n== Como se reparte el empleo con la especificacion de la UAM ==')
    print(T_K3.to_string(index=False))

    # ---- T_K4: la especificacion mejorada, k=4
    mej = []
    for pais, anio in ORDEN:
        d = datos[(datos.pais == pais) & (datos.anio == anio)].reset_index(drop=True)
        if d.empty:
            continue
        cl_u = particion(d, 'UAM', 4)
        cl_m = particion(d, 'mejorada', 4)
        c = caracterizar(d, cl_m, 'mejorada k=4')
        c.insert(0, 'anio', anio)
        c.insert(0, 'pais', pais)
        mej.append(c)
        print(f'  {pais} {anio}: ARI UAM vs mejorada (k=4) = '
              f'{uam.rand_ajustado(cl_u, cl_m):.3f}')
    T_K4 = pd.concat(mej, ignore_index=True)

    with pd.ExcelWriter(OUT / f'{HOY} T_K1 conglomerados por pais especificacion UAM.xlsx') as w:
        T_K1.to_excel(w, sheet_name='caracterizacion', index=False)
    with pd.ExcelWriter(OUT / f'{HOY} T_K2 validacion del metodo sobre Chile.xlsx') as w:
        val.to_excel(w, sheet_name='validacion', index=False)
    with pd.ExcelWriter(OUT / f'{HOY} T_K3 reparto del empleo entre conglomerados.xlsx') as w:
        T_K3.to_excel(w, sheet_name='reparto', index=False)
    with pd.ExcelWriter(OUT / f'{HOY} T_K4 conglomerados con la especificacion mejorada.xlsx') as w:
        T_K4.to_excel(w, sheet_name='mejorada', index=False)

    print(f'\nEscritas T_K1 a T_K4 en {OUT}')
    return T_K1, T_K3, T_K4


if __name__ == '__main__':
    main()
