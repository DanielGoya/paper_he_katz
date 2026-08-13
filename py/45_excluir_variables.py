"""Bloque K.4 — que queda del ejercicio de la UAM si se saca, de a una, cada
variable.

LA PREGUNTA (DG, 2026-08-13). El ejercicio de la UAM corre sobre siete
variables. Tres de ellas ya estan bajo sospecha —la FBCF por ocupado esta rota
(mide cuanto bien de capital PRODUCE el sector, no su intensidad de capital), la
balanza comercial entra en niveles y no es un ratio, y los dos coeficientes de
comercio son casi complementarios del ingreso interno—. Antes de proponer
reemplazos conviene saber cuanto sostiene cada una: se saca UNA y se vuelve a
correr, con las seis restantes.

QUE SE VARIA. Cuatro ejes, cruzados:

  pais y periodo   Chile 2003 y 2023, Brasil 2003 y 2021, Mexico 2008 y 2018.
                   Argentina 1997 se deja fuera por pedido explicito.
  conjunto         la COU completa, y el subconjunto que la UAM efectivamente
                   agrupa (ver mas abajo: para Chile se conoce; para los otros
                   dos hay que aproximarlo).
  especificacion   las siete variables, y las siete versiones con una menos.
  corte            k = 3 y k = 4.

EL METODO NO SE TOCA. Ward sobre distancia euclidiana, sin ponderar, con la
balanza en niveles y estandarizacion con desviacion muestral: exactamente la
especificacion de la UAM (`40_uam_metodo.py`), que reproduce su particion
chilena con Rand = 1,0000. Lo unico que cambia es el conjunto de columnas. Las
tres mejoras del proyecto —balanza normalizada, ponderacion por empleo,
logaritmos— quedan deliberadamente afuera: la pregunta es que sostiene el
ejercicio TAL COMO ESTA, no que pasaria con otro.

EL SUBCONJUNTO DE SECTORES, Y LO QUE NO SE SABE. La UAM excluye actividades del
ejercicio y no documento con que criterio. Para Chile se sabe CUALES: 11 de 73
en 2003 y 10 de 111 en 2023, que salen de comparar el insumo con los dos libros
de resultados. Para Brasil y Mexico no hay nada. Como el criterio no es
inferible, se usa un sustituto transparente y se mide contra el chileno:

    quedan fuera las actividades con max |z| > 3 en las siete variables,
    calculado sobre la COU completa.

En Chile 2003 esa regla saca 7 actividades y las 7 estan efectivamente fuera del
ejercicio de la UAM; en 2023 saca 8 y acierta 5. O sea: es precisa y conservadora
—lo que saca, la UAM tambien lo saca (2003) o casi (2023)—, pero se queda corta,
porque la UAM excluye ademas actividades que no son extremas en ninguna variable
(caucho, maquinaria, azucar). Sirve para tener en los tres paises un conjunto
recortado comparable; NO es una reconstruccion del criterio de la UAM. Por eso
Chile corre con los dos: el subconjunto real y el sustituto, y la diferencia
entre ambos es la medida de cuanto importa esa ignorancia.

DE DONDE SALEN LOS DATOS. Chile, del insumo de la UAM
(`Chile_datos_Aug08_26_v1.xlsx`, 73 + 111 actividades), porque es el unico
archivo chileno que trae la COU COMPLETA con empleo; `cou_multipais.csv` ya
viene recortado al subconjunto clasificado. Brasil y Mexico, de
`cou_multipais.csv` (`41_cou_multipais.py`), que si trae la lista completa.

SALIDA. Una sola planilla, `T_K10`, con seis hojas: `lectura`, `estabilidad`
(la tabla que se lee primero: ARI contra las siete, variable por variable),
`resumen`, `conglomerados`, `membresias` y `sectores`.

DEPENDE DE. `40_uam_metodo.py` y `41_cou_multipais.py`.
"""

from __future__ import annotations

import importlib.util
import os
from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('uam', os.path.join(AQUI, '40_uam_metodo.py'))
uam = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uam)

import rutas   # noqa: E402  (el modulo del metodo se carga por ruta: empieza con digito)

INTER = rutas.INTER
OUT = rutas.OUT
HOY = date.today().strftime('%Y.%m.%d')

# Argentina queda fuera: el pedido es Chile, Mexico y Brasil.
ORDEN = [('Chile', 2003), ('Chile', 2023),
         ('Brasil', 2003), ('Brasil', 2021),
         ('Mexico', 2008), ('Mexico', 2018)]

CORTES = (3, 4)

# Umbral del sustituto del criterio de exclusion. Ver el encabezado: 3 desviaciones
# en la mas extrema de las siete variables, sobre la COU completa.
UMBRAL_Z = 3.0

SET_COMPLETA = 'COU completa'
SET_UAM = 'subconjunto UAM (real)'
SET_PROXY = f'subconjunto proxy |z|>{UMBRAL_Z:.0f}'

# Que mide cada variable, en una linea, para que la hoja se lea sin volver al codigo.
GLOSA = {
    'x_prod_trabajo': 'productividad laboral (VA / ocupados)',
    'x_capital_trabajo': 'FBCF por ocupado (asignada por producto; la variable rota)',
    'x_remunera_prom': 'remuneracion media (remuneraciones / ocupados)',
    'x_demanda_externa': 'penetracion importadora (impo / VBP; el nombre esta invertido)',
    'x_balanza_com': 'balanza comercial EN NIVELES (expo - impo)',
    'x_ingreso_interno': 'participacion del VA en la produccion bruta (VA / VBP)',
    'x_oferta_externa': 'coeficiente exportador (expo / VBP; el nombre esta invertido)',
}


# ==========================================================================
# Carga: la COU completa de cada pais, mas el subconjunto real de Chile
# ==========================================================================

def cargar_chile() -> tuple[pd.DataFrame, dict[int, set]]:
    """Chile con las 73 y 111 actividades, y los codigos que la UAM si agrupa.

    El insumo de la UAM es la unica fuente chilena con la COU completa Y empleo:
    la COU del Banco Central no publica ocupados por actividad.
    """
    ins = pd.read_excel(rutas.exigir(rutas.D_UAM_INSUMO, 'el insumo de la UAM'))
    clasificados = {}
    for periodo in (1, 2):
        res = pd.read_excel(
            rutas.exigir(rutas.D_UAM_HCLUST[periodo], f'los resultados del periodo {periodo}'),
            sheet_name='sectores_cluster')
        clasificados[periodo] = set(res['codigo_3dig'])
    d = pd.DataFrame({
        'pais': 'Chile', 'anio': ins['anio'], 'periodo': ins['periodo'],
        'codigo': ins['codigo_3dig'].astype(str), 'desc': ins['desc'],
        'vbp': ins['vbp'], 'valor_agrega': ins['valor_agrega'],
        'remunera': ins['remunera'], 'empleo': ins['empleo'],
        'fbcf': ins['fbcf'], 'expo': ins['expo'], 'impo': ins['impo'],
    })
    # Los codigos vienen como enteros en los dos archivos; se comparan como texto.
    reales = {p: {str(c) for c in cods} for p, cods in clasificados.items()}
    return d, reales


def cargar_resto() -> pd.DataFrame:
    d = pd.read_csv(rutas.exigir(INTER / 'cou_multipais.csv', 'la extraccion multipais'))
    d['remunera'] = d['remunera'].fillna(0.0)
    d['codigo'] = d['codigo'].astype(str)
    return d[d.pais.isin(('Brasil', 'Mexico'))]


def extremas(d: pd.DataFrame) -> pd.Series:
    """max |z| de cada actividad en las siete variables, sobre el conjunto dado."""
    r = uam.construir_variables(d, balanza='nivel')
    z = uam.estandarizar(r, uam.VARS_UAM)
    return pd.Series(np.abs(z).max(axis=1), index=d.index)


# ==========================================================================
# Comparacion de particiones
# ==========================================================================

def cambian_de_grupo(a, b) -> float:
    """% de actividades que cambian de grupo, con el mejor emparejamiento posible.

    El ARI no dice cuantas unidades se mueven, y la numeracion de los grupos es
    arbitraria: hay que emparejar los grupos de las dos particiones antes de
    contar. Se resuelve como asignacion optima sobre la tabla de contingencia.
    """
    tab = pd.crosstab(pd.Series(np.asarray(a)), pd.Series(np.asarray(b))).to_numpy()
    fil, col = linear_sum_assignment(-tab)
    return float(100.0 * (1.0 - tab[fil, col].sum() / tab.sum()))


def empleo_que_cambia(w: np.ndarray, a, b) -> float:
    """% del empleo que cambia de grupo, con el mismo emparejamiento optimo.

    Las actividades no pesan lo mismo: una particion puede mover veinte ramas
    manufactureras diminutas y no mover nada que importe.
    """
    a, b = np.asarray(a), np.asarray(b)
    _, ia = np.unique(a, return_inverse=True)
    _, ib = np.unique(b, return_inverse=True)
    tab = np.zeros((ia.max() + 1, ib.max() + 1))
    np.add.at(tab, (ia, ib), w)
    fil, col = linear_sum_assignment(-tab)
    return float(100.0 * (1.0 - tab[fil, col].sum() / w.sum()))


def caracterizar(d: pd.DataFrame, cl: np.ndarray) -> pd.DataFrame:
    """Un renglon por conglomerado, con la lectura economica de siempre."""
    g = d.copy()
    g['cl'] = cl
    tot_emp, tot_va, tot_x = g['empleo'].sum(), g['valor_agrega'].sum(), g['expo'].sum()
    prod_media = tot_va / tot_emp
    filas = []
    for c, sub in g.groupby('cl'):
        filas.append({
            'conglomerado': int(c), 'n': len(sub),
            '% empleo': 100 * sub['empleo'].sum() / tot_emp,
            '% VA': 100 * sub['valor_agrega'].sum() / tot_va,
            '% exportaciones': 100 * sub['expo'].sum() / tot_x if tot_x else np.nan,
            'productividad (economia=100)':
                (sub['valor_agrega'].sum() / sub['empleo'].sum()) / prod_media * 100,
            'masa salarial / VA (%)':
                100 * sub['remunera'].sum() / sub['valor_agrega'].sum(),
            'actividad mayor': str(sub.sort_values('empleo', ascending=False)['desc'].iloc[0])[:60],
        })
    return pd.DataFrame(filas).sort_values('% empleo', ascending=False)


# ==========================================================================
# El ejercicio
# ==========================================================================

def conjuntos(pais: str, d: pd.DataFrame, reales: set | None) -> list[tuple[str, pd.DataFrame]]:
    """Los conjuntos de sectores sobre los que se corre este pais-periodo."""
    salida = [(SET_COMPLETA, d)]
    if reales is not None:
        salida.append((SET_UAM, d[d.codigo.isin(reales)].reset_index(drop=True)))
    fuera = extremas(d) > UMBRAL_Z
    salida.append((SET_PROXY, d[~fuera.to_numpy()].reset_index(drop=True)))
    return salida


def main():
    rutas.preparar_directorios()
    chl, reales_chl = cargar_chile()
    resto = cargar_resto()
    datos = pd.concat([chl, resto], ignore_index=True)

    resumen, conglom, membres, sectores = [], [], [], []

    for pais, anio in ORDEN:
        d0 = datos[(datos.pais == pais) & (datos.anio == anio)].reset_index(drop=True)
        if d0.empty:
            print(f'  AVISO: no hay datos de {pais} {anio}')
            continue
        periodo = int(d0['periodo'].iloc[0])
        reales = reales_chl.get(periodo) if pais == 'Chile' else None

        # ---- registro de que actividad entra a cada conjunto
        ext = extremas(d0)
        s = d0[['pais', 'anio', 'codigo', 'desc', 'empleo', 'valor_agrega', 'expo']].copy()
        s['% empleo'] = 100 * s['empleo'] / s['empleo'].sum()
        s['% VA'] = 100 * s['valor_agrega'] / s['valor_agrega'].sum()
        s['% exportaciones'] = 100 * s['expo'] / s['expo'].sum() if s['expo'].sum() else np.nan
        s['max |z| en las siete'] = ext.to_numpy()
        s['en el subconjunto UAM (real)'] = (
            d0.codigo.isin(reales) if reales is not None else np.nan)
        s['en el subconjunto proxy'] = (ext <= UMBRAL_Z).to_numpy()
        sectores.append(s.drop(columns=['empleo', 'valor_agrega', 'expo']))

        for nombre_set, d in conjuntos(pais, d0, reales):
            for k in CORTES:
                base = uam.agrupar(uam.construir_variables(d, 'nivel'), uam.VARS_UAM, k)
                memb = d[['pais', 'anio', 'codigo', 'desc']].copy()
                memb.insert(2, 'conjunto', nombre_set)
                memb['% empleo'] = 100 * d['empleo'] / d['empleo'].sum()
                memb['k'] = k
                memb['las siete'] = base

                for etiqueta, quitada in [('las siete', None)] + [(v, v) for v in uam.VARS_UAM]:
                    if quitada is None:
                        cl = base
                    else:
                        vs = [v for v in uam.VARS_UAM if v != quitada]
                        cl = uam.agrupar(uam.construir_variables(d, 'nivel'), vs, k)
                        memb[f'sin {quitada}'] = cl

                    emp = pd.Series(d['empleo'].to_numpy()).groupby(cl).sum()
                    emp = emp / emp.sum()
                    tam = pd.Series(cl).value_counts().sort_values(ascending=False)
                    car = caracterizar(d, cl)
                    resumen.append({
                        'pais': pais, 'anio': anio, 'conjunto': nombre_set,
                        'n actividades': len(d), 'k pedido': k,
                        'variable excluida': 'ninguna' if quitada is None else quitada,
                        'que mide la excluida': '' if quitada is None else GLOSA[quitada],
                        'grupos obtenidos': int(tam.size),
                        'tamanos': '/'.join(map(str, tam.tolist())),
                        '% empleo del mayor': round(100 * emp.max(), 1),
                        '% empleo del menor': round(100 * emp.min(), 2),
                        'grupos con <1% del empleo': int((emp < .01).sum()),
                        'actividades en esos grupos': int(
                            tam.reindex(emp[emp < .01].index).fillna(0).sum()),
                        'productividad del grupo mayor':
                            round(car.iloc[0]['productividad (economia=100)'], 0),
                        'productividad del grupo menor':
                            round(car.iloc[-1]['productividad (economia=100)'], 0),
                        'ARI contra las siete':
                            1.0 if quitada is None else round(uam.rand_ajustado(base, cl), 3),
                        'Rand contra las siete':
                            1.0 if quitada is None else round(uam.rand_simple(base, cl), 3),
                        '% actividades que cambian de grupo':
                            0.0 if quitada is None else round(cambian_de_grupo(base, cl), 1),
                        '% del empleo que cambia de grupo':
                            0.0 if quitada is None else round(
                                empleo_que_cambia(d['empleo'].to_numpy(), base, cl), 1),
                    })
                    car.insert(0, 'variable excluida', 'ninguna' if quitada is None else quitada)
                    car.insert(0, 'k', k)
                    car.insert(0, 'conjunto', nombre_set)
                    car.insert(0, 'anio', anio)
                    car.insert(0, 'pais', pais)
                    conglom.append(car)

                membres.append(memb)

        print(f'  {pais} {anio}: listo '
              f'({len(conjuntos(pais, d0, reales))} conjuntos x 8 especificaciones x 2 cortes)')

    T = pd.DataFrame(resumen)
    CONG = pd.concat(conglom, ignore_index=True)
    MEMB = pd.concat(membres, ignore_index=True)
    SECT = pd.concat(sectores, ignore_index=True)

    # ---- la hoja que se lee primero: ARI contra las siete, variable por variable
    est = (T[T['variable excluida'] != 'ninguna']
           .pivot_table(index=['pais', 'anio', 'conjunto', 'n actividades', 'k pedido'],
                        columns='variable excluida', values='ARI contra las siete')
           .reset_index())
    est.columns.name = None
    est = est.rename(columns={v: f'sin {v}' for v in uam.VARS_UAM})
    base_tam = (T[T['variable excluida'] == 'ninguna']
                [['pais', 'anio', 'conjunto', 'k pedido', 'tamanos']]
                .rename(columns={'tamanos': 'tamanos con las siete'}))
    est = est.merge(base_tam, on=['pais', 'anio', 'conjunto', 'k pedido'], how='left')
    est.insert(5, 'tamanos con las siete', est.pop('tamanos con las siete'))
    cols_sin = [f'sin {v}' for v in uam.VARS_UAM]
    est['ARI minimo'] = est[cols_sin].min(axis=1)
    est['variable mas decisiva'] = est[cols_sin].idxmin(axis=1).str.replace('sin ', '', regex=False)
    est['variables con ARI < 0,5'] = (est[cols_sin] < 0.5).sum(axis=1)
    est['variables con ARI > 0,9'] = (est[cols_sin] > 0.9).sum(axis=1)

    # ---- que tan bueno es el sustituto del criterio de exclusion, medido en Chile
    diag = []
    for anio in (2003, 2023):
        s = SECT[(SECT.pais == 'Chile') & (SECT.anio == anio)]
        real_fuera = ~s['en el subconjunto UAM (real)'].astype(bool)
        proxy_fuera = ~s['en el subconjunto proxy'].astype(bool)
        diag.append(
            f'  Chile {anio}: la UAM saca {int(real_fuera.sum())} de {len(s)} actividades; el '
            f'sustituto saca {int(proxy_fuera.sum())}, de las cuales '
            f'{int((real_fuera & proxy_fuera).sum())} estan efectivamente fuera del ejercicio '
            f'de la UAM.')

    lectura = pd.DataFrame({'nota': [
        'T_K10 - Que queda del ejercicio de la UAM si se saca, de a una, cada variable.',
        f'Generada el {HOY} por py/45_excluir_variables.py. Metodo: Ward sobre distancia '
        'euclidiana, sin ponderar, balanza en niveles, estandarizacion con desviacion '
        'muestral. Es exactamente la especificacion de la UAM; lo unico que cambia entre '
        'corridas es el conjunto de columnas y el de actividades.',
        '',
        'HOJAS. sintesis: cuanto sostiene cada variable, promediando las 28 corridas. '
        'estabilidad: la tabla que se lee primero, ARI contra la particion con las '
        'siete variables. resumen: un renglon por corrida, con tamanos y lectura economica. '
        'conglomerados: un renglon por conglomerado de cada corrida. membresias: en que grupo '
        'cae cada actividad en cada corrida. sectores: que actividad entra a cada conjunto.',
        '',
        'COMO SE LEE EL ARI. 1,000 = sacar esa variable no cambia nada, o sea la variable no '
        'sostiene la particion. Cerca de 0 = la particion la decidia esa variable sola. '
        'Negativo = la particion nueva coincide menos que dos particiones al azar.',
        '',
        'EL SUBCONJUNTO DE SECTORES. La UAM excluye actividades y no dijo con que criterio. '
        'Para Chile se sabe cuales (11 de 73 en 2003, 10 de 111 en 2023, por diferencia entre '
        'su insumo y sus dos libros de resultados). Para Brasil y Mexico no se sabe nada, asi '
        f'que se usa un sustituto: quedan fuera las actividades con max |z| > {UMBRAL_Z:.0f} en '
        'las siete variables. En Chile ese sustituto es preciso y corto (ver la hoja sectores '
        'y el encabezado del script). NO reconstruye el criterio de la UAM: da un conjunto '
        'recortado comparable entre los tres paises. Chile corre con los dos, y la distancia '
        'entre ambos mide cuanto importa esa ignorancia.',
        *diag,
        '',
        'LO QUE ESTA CORRIDA NO HACE. No aplica ninguna de las tres mejoras del proyecto '
        '(balanza normalizada, ponderacion por empleo, logaritmos): la pregunta es que '
        'sostiene el ejercicio tal como esta publicado. Tampoco reemplaza variables, solo las '
        'saca. Argentina 1997 queda fuera por pedido.',
    ]})

    # ---- sintesis: cuanto sostiene cada variable, en promedio, en cada pais
    sint = (T[T['variable excluida'] != 'ninguna']
            .pivot_table(index='variable excluida', columns='pais',
                         values='ARI contra las siete', aggfunc='mean'))
    sint['todos los paises'] = (T[T['variable excluida'] != 'ninguna']
                                .groupby('variable excluida')['ARI contra las siete'].mean())
    sint['veces que es la mas decisiva'] = (
        est['variable mas decisiva'].value_counts().reindex(sint.index).fillna(0).astype(int))
    sint['corridas con ARI > 0,9 (de 28)'] = (
        T[T['variable excluida'] != 'ninguna']
        .assign(alto=lambda x: x['ARI contra las siete'] > 0.9)
        .groupby('variable excluida')['alto'].sum())
    sint['que mide'] = [GLOSA[v] for v in sint.index]
    sint = sint.sort_values('todos los paises', ascending=False).reset_index()

    destino = OUT / f'{HOY} T_K10 sensibilidad a excluir cada variable.xlsx'
    with pd.ExcelWriter(destino) as w:
        lectura.to_excel(w, sheet_name='lectura', index=False)
        sint.round(3).to_excel(w, sheet_name='sintesis', index=False)
        est.round(3).to_excel(w, sheet_name='estabilidad', index=False)
        T.to_excel(w, sheet_name='resumen', index=False)
        CONG.round(2).to_excel(w, sheet_name='conglomerados', index=False)
        MEMB.to_excel(w, sheet_name='membresias', index=False)
        SECT.round(3).to_excel(w, sheet_name='sectores', index=False)

    print('\n== ARI contra la particion con las siete variables ==')
    print(est.round(3).to_string(index=False))
    print(f'\nEscrita {destino.name} en {OUT}')
    return T, est, CONG, MEMB, SECT


if __name__ == '__main__':
    main()
