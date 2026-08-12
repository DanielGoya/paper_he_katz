"""Bloque K.3 — el problema del cobre, buscado en los otros tres paises.

En Chile la UAM dejo el cobre fuera del ejercicio: una sola actividad con el
8,8 % del valor agregado, el 45,8 % de las exportaciones, el 0,56 % del empleo y
una productividad 15,7 veces la media. Excluirlo dejo sin clasificar el 19,1 %
del VA y el 48,5 % de las exportaciones.

Este script busca lo mismo en Argentina, Brasil y Mexico, por tres caminos:

  1. actividades atipicas por productividad y por concentracion de exportaciones;
  2. actividades que el propio algoritmo aisla, es decir conglomerados que
     reunen menos del 1 % del empleo;
  3. que pasa con la particion cuando se las excluye: si el problema se resuelve
     o se desplaza a la siguiente actividad extrema, como paso en Chile.

Salidas: T_K5 a T_K7 y F_K1 en datos/output.
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


def indicadores(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    prod_media = d['valor_agrega'].sum() / d['empleo'].sum()
    d['productividad'] = d['valor_agrega'] / d['empleo'] / prod_media
    d['% VA'] = 100 * d['valor_agrega'] / d['valor_agrega'].sum()
    d['% empleo'] = 100 * d['empleo'] / d['empleo'].sum()
    d['% exportaciones'] = 100 * d['expo'] / d['expo'].sum()
    d['masa salarial / VA'] = 100 * d['remunera'] / d['valor_agrega']
    return d


def herfindahl(x: pd.Series) -> float:
    s = x.clip(lower=0)
    if s.sum() <= 0:
        return np.nan
    p = s / s.sum()
    return float((p ** 2).sum() * 10000)


CHL2023 = (rutas.ALMACEN / 'CEPAL COU-MIP LAC' / 'CHL_COU_2023' /
           'CHI_2023_Cuadros_111x181-1.xlsx')


def chile_completa() -> pd.DataFrame:
    """Chile 2023 con las 111 actividades, incluidas las que la UAM excluyo.

    Sin esto la comparacion esta sesgada: el archivo de la UAM ya viene sin el
    cobre, asi que Chile aparece menos concentrado que los demas por construccion.
    No lleva empleo —el COU no lo publica— pero si todo lo demas.
    """
    d1 = pd.read_excel(CHL2023, sheet_name='1', header=None)
    aid = pd.to_numeric(d1.iloc[10, 2:], errors='coerce')
    acols = [j for j in range(2, d1.shape[1]) if not pd.isna(aid[j])]
    pid = pd.to_numeric(d1.iloc[:, 1], errors='coerce')
    prows = [i for i in range(13, d1.shape[0]) if not pd.isna(pid[i])]
    PROD = d1.iloc[prows, acols].apply(pd.to_numeric, errors='coerce').fillna(0).to_numpy()
    prods = pid[prows].astype(int).to_numpy()
    acts = aid[acols].astype(int).to_numpy()
    tot = PROD.sum(axis=1, keepdims=True)
    sh = np.divide(PROD, tot, out=np.zeros_like(PROD), where=tot > 0)

    d6 = pd.read_excel(CHL2023, sheet_name='6', header=None)
    p6 = pd.to_numeric(d6.iloc[:, 1], errors='coerce')
    r6 = [i for i in range(11, d6.shape[0]) if not pd.isna(p6[i])]
    i6 = p6[r6].astype(int).to_numpy()
    expo = pd.Series(pd.to_numeric(d6.iloc[r6, 9], errors='coerce').to_numpy(),
                     index=i6).reindex(prods).fillna(0).to_numpy()

    d23 = pd.read_excel(CHL2023, sheet_name='23', header=None)
    a23 = pd.to_numeric(d23.iloc[10, 3:], errors='coerce')
    c23 = [j for j in range(3, d23.shape[1]) if not pd.isna(a23[j])]
    ids = a23[c23].astype(int).to_numpy()
    val = lambda i: pd.Series(pd.to_numeric(d23.iloc[i, c23], errors='coerce').to_numpy(), index=ids)

    gl = pd.read_excel(CHL2023, sheet_name='Glosa', header=None)
    nom = pd.Series(gl.iloc[9:9 + 111, 2].to_numpy(),
                    index=pd.to_numeric(gl.iloc[9:9 + 111, 1]).astype(int))

    t = pd.DataFrame({'desc': nom, 'valor_agrega': val(15),
                      'remunera': val(19), 'expo': pd.Series(sh.T @ expo, index=acts)})
    clasif = set(pd.read_csv(INTER / 'uam_replica_p2.csv')['codigo_3dig'])
    t['% VA'] = 100 * t.valor_agrega / t.valor_agrega.sum()
    t['% exportaciones'] = 100 * t.expo / t.expo.sum()
    t['masa salarial / VA'] = 100 * t.remunera / t.valor_agrega
    t['clasificada por la UAM'] = [c in clasif for c in t.index]
    return t.reset_index(names='codigo')


def main():
    rutas.preparar_directorios()
    datos = pd.read_csv(rutas.exigir(INTER / 'cou_multipais.csv', 'la extraccion multipais'))
    datos['remunera'] = datos['remunera'].fillna(0.0)

    atipicas, panorama, desplaza = [], [], []

    for pais, anio in ORDEN:
        d = datos[(datos.pais == pais) & (datos.anio == anio)].reset_index(drop=True)
        if d.empty:
            continue
        d = indicadores(d)

        # ---- 1. las cinco actividades mas atipicas por productividad
        top_p = d.nlargest(5, 'productividad')
        top_x = d.nlargest(5, '% exportaciones')
        for etiqueta, sub in (('productividad', top_p), ('exportaciones', top_x)):
            s = sub.copy()
            s['criterio'] = etiqueta
            s['pais'] = pais
            s['anio'] = anio
            atipicas.append(s[['pais', 'anio', 'criterio', 'codigo', 'desc',
                               'productividad', '% VA', '% empleo',
                               '% exportaciones', 'masa salarial / VA']])

        # ---- 2. panorama de concentracion
        cl2 = uam.agrupar(uam.construir_variables(d, 'nivel'), uam.VARS_UAM, 2)
        tam2 = pd.Series(cl2).value_counts()
        emp2 = d.groupby(cl2)['empleo'].sum() / d['empleo'].sum()
        panorama.append({
            'pais': pais, 'anio': anio, 'n actividades': len(d),
            'productividad max / media': round(d['productividad'].max(), 1),
            'productividad p99 / p50': round(
                d['productividad'].quantile(.99) / d['productividad'].median(), 1),
            '% VA de la actividad mas productiva':
                round(d.loc[d['productividad'].idxmax(), '% VA'], 1),
            '% empleo de la actividad mas productiva':
                round(d.loc[d['productividad'].idxmax(), '% empleo'], 2),
            '% exportaciones de la mayor exportadora':
                round(d['% exportaciones'].max(), 1),
            '% exportaciones de las 3 mayores':
                round(d.nlargest(3, '% exportaciones')['% exportaciones'].sum(), 1),
            'Herfindahl exportaciones': round(herfindahl(d['expo']), 0),
            'k=2: n del grupo menor': int(tam2.min()),
            'k=2: % empleo del grupo mayor': round(100 * emp2.max(), 1),
        })

        # ---- 3. se resuelve o se desplaza: excluir las atipicas y volver a correr
        for m in (0, 1, 2, 3, 5):
            if m >= len(d) - 5:
                continue
            fuera = d.nlargest(m, 'productividad')['codigo'].tolist() if m else []
            g = d[~d['codigo'].isin(fuera)].reset_index(drop=True)
            g = indicadores(g)
            cl = uam.agrupar(uam.construir_variables(g, 'nivel'), uam.VARS_UAM, 4)
            emp = g.groupby(cl)['empleo'].sum() / g['empleo'].sum()
            tam = pd.Series(cl).value_counts().sort_values(ascending=False)
            desplaza.append({
                'pais': pais, 'anio': anio, 'actividades excluidas': m,
                '% VA excluido': round(100 - g['valor_agrega'].sum() /
                                       d['valor_agrega'].sum() * 100, 1),
                '% exportaciones excluidas': round(100 - g['expo'].sum() /
                                                   d['expo'].sum() * 100, 1),
                'tamanos k=4': '/'.join(map(str, tam.tolist())),
                '% empleo del mayor': round(100 * emp.max(), 1),
                'grupos con <1% del empleo': int((emp < .01).sum()),
                'productividad max / media (resto)': round(g['productividad'].max(), 1),
            })

    T_K5 = pd.concat(atipicas, ignore_index=True)
    T_K6 = pd.DataFrame(panorama)
    T_K7 = pd.DataFrame(desplaza)

    # ---- Chile con las 111 actividades, para que la comparacion sea pareja
    chl = chile_completa()
    fila = {
        'pais': 'Chile', 'anio': 2023, 'n actividades': len(chl),
        'productividad max / media': np.nan, 'productividad p99 / p50': np.nan,
        '% VA de la actividad mas productiva': np.nan,
        '% empleo de la actividad mas productiva': np.nan,
        '% exportaciones de la mayor exportadora': round(chl['% exportaciones'].max(), 1),
        '% exportaciones de las 3 mayores': round(
            chl.nlargest(3, '% exportaciones')['% exportaciones'].sum(), 1),
        'Herfindahl exportaciones': round(herfindahl(chl['expo']), 0),
        'k=2: n del grupo menor': np.nan, 'k=2: % empleo del grupo mayor': np.nan,
    }
    T_K6 = pd.concat([T_K6, pd.DataFrame([fila])], ignore_index=True)
    T_K6.loc[T_K6.index[-1], 'pais'] = 'Chile (COU completa, con cobre)'

    excl = chl[~chl['clasificada por la UAM']]
    print('\n== Chile 2023 con las 111 actividades (la UAM clasifica 101) ==')
    print(f'  mayor exportadora {chl["% exportaciones"].max():.1f} % · '
          f'Herfindahl {herfindahl(chl["expo"]):.0f}')
    print(f'  excluidas: {len(excl)} actividades, {excl["% VA"].sum():.1f} % del VA y '
          f'{excl["% exportaciones"].sum():.1f} % de las exportaciones')
    print(excl[['desc', '% VA', '% exportaciones', 'masa salarial / VA']]
          .round(2).to_string(index=False))

    print('\n== Concentracion y atipicos, pais por pais ==')
    print(T_K6.to_string(index=False))
    print('\n== Se resuelve o se desplaza (k=4, excluyendo las mas productivas) ==')
    print(T_K7.to_string(index=False))

    for nom, tab, hoja in (
            ('T_K5 actividades atipicas por pais', T_K5, 'atipicas'),
            ('T_K6 concentracion y valores extremos', T_K6, 'concentracion'),
            ('T_K7 efecto de excluir las actividades extremas', T_K7, 'exclusion'),
            ('T_K8 Chile 2023 con las 111 actividades', chl, 'chile_completa')):
        with pd.ExcelWriter(OUT / f'{HOY} {nom}.xlsx') as w:
            tab.to_excel(w, sheet_name=hoja, index=False)
    print(f'\nEscritas T_K5 a T_K8 en {OUT}')
    return T_K5, T_K6, T_K7, chl


if __name__ == '__main__':
    main()
