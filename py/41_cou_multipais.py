"""Bloque K.1 — extrae de las matrices insumo-producto de los cuatro paises las
siete magnitudes que necesita el ejercicio de conglomerados de la UAM.

Salida: datos/intermediate/cou_multipais.csv, con una fila por actividad y
columnas pais, anio, periodo, codigo, desc, vbp, valor_agrega, remunera,
empleo, fbcf, expo, impo.

Anios elegidos: los mas cercanos a los dos de Chile (2003 y 2023) entre los que
publican TODAS las magnitudes a nivel desagregado. Ver README del bloque.

    Chile      2003 (73 act.)  ·  2023 (111 act.)   COU del Banco Central
    Brasil     2003 (51 act.)  ·  2021 (68 act.)    TRU del IBGE
    Mexico     2008 (262 ram.) ·  2018 (262 ram.)   MIP del INEGI
    Argentina  1997 (124 act.) ·  ---               MIP del INDEC
    Argentina  2004 (143 act.) ·  2021 (107 act.)   COU del INDEC, especificacion reducida

Regla de asignacion producto -> actividad, para las tres magnitudes que la COU
publica por producto (exportaciones, importaciones, FBCF): se reparten entre las
actividades en proporcion a su participacion en la produccion de ese producto.
Validada contra el archivo de la UAM en 42_cluster_multipais.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import rutas

# Matrices insumo-producto de los cuatro paises. Viven en el almacen general, no
# en el proyecto: sirven a cualquier trabajo comparativo. Cada carpeta lleva su
# LEEME.md con procedencia y trampas.
CEPAL = rutas.ALMACEN / 'CEPAL COU-MIP LAC'
IBGE = rutas.ALMACEN / 'IBGE Contas Nacionais'
INTER = rutas.INTER

COLS = ['pais', 'anio', 'periodo', 'codigo', 'desc',
        'vbp', 'valor_agrega', 'remunera', 'empleo', 'fbcf', 'expo', 'impo']


def _num(x):
    return pd.to_numeric(x, errors='coerce')


def _txt(s):
    return s.map(lambda v: '' if pd.isna(v) else str(v).strip())


def repartir(valor_producto: np.ndarray, produccion: np.ndarray) -> np.ndarray:
    """Reparte una magnitud por producto entre actividades, segun produccion."""
    tot = produccion.sum(axis=1, keepdims=True)
    share = np.divide(produccion, tot, out=np.zeros_like(produccion), where=tot > 0)
    return share.T @ valor_producto


# ==========================================================================
# CHILE — COU del Banco Central. El insumo de la UAM ya esta replicado.
# ==========================================================================

def chile() -> pd.DataFrame:
    salida = []
    for per, f in ((1, 'uam_replica_p1.csv'), (2, 'uam_replica_p2.csv')):
        d = pd.read_csv(rutas.exigir(INTER / f, 'la replica de la UAM'))
        salida.append(pd.DataFrame({
            'pais': 'Chile', 'anio': d['anio'], 'periodo': per,
            'codigo': d['codigo_3dig'].astype(str), 'desc': d['desc'],
            'vbp': d['vbp'], 'valor_agrega': d['valor_agrega'],
            'remunera': d['remunera'], 'empleo': d['empleo'],
            'fbcf': d['fbcf'], 'expo': d['expo'], 'impo': d['impo'],
        }))
    return pd.concat(salida, ignore_index=True)


# ==========================================================================
# BRASIL — Tabelas de Recursos e Usos del IBGE
# ==========================================================================

def _filas_producto(etiquetas: pd.Series) -> list[int]:
    """Filas de producto de una hoja del IBGE: desde la 4 hasta el primer total.

    Sin este corte se cuela la fila 'Total do produto', que al reindexar aparece
    tanto en la matriz de produccion como en la de demanda y duplica el agregado.
    """
    filas = []
    for i in range(4, len(etiquetas)):
        t = etiquetas[i]
        if not t:
            continue
        if t.lower().startswith(('total', 'fonte', 'nota', '(1)', '(2)')):
            break
        filas.append(i)
    return filas


def _brasil_anio(nivel: int, anio: int, carpeta: str) -> pd.DataFrame:
    """Lee un anio de la TRU del IBGE.

    Hay dos formatos. En el de nivel 68 (2010 en adelante) la columna 0 lleva el
    codigo del producto y la 1 su glosa; en el de nivel 51 (serie 2000-2021) no
    hay codigos y la columna 0 es la glosa. Se detecta y se lee cualquiera.
    """
    t1 = f'{IBGE}/{carpeta}/{nivel}_tab1_{anio}.xls'
    t2 = f'{IBGE}/{carpeta}/{nivel}_tab2_{anio}.xls'

    dp = pd.read_excel(t1, sheet_name='producao', header=None)
    c0 = _txt(dp.iloc[:, 0])
    con_codigo = any(c0[i][:2].isdigit() for i in range(4, min(12, len(dp))))
    j_ini = 2 if con_codigo else 1              # primera columna de actividad

    cab = _txt(dp.iloc[3, :])
    acols = [j for j in range(j_ini, dp.shape[1])
             if cab[j] and not cab[j].startswith('Total')]
    prows = _filas_producto(c0)
    PROD = dp.iloc[prows, acols].apply(_num).fillna(0).to_numpy(dtype=float)
    productos = [c0[i] for i in prows]
    if con_codigo:
        actividades = [cab[j].split('\n')[0] for j in acols]
        desc_act = [' '.join(cab[j].split('\n')[1:]) for j in acols]
    else:
        actividades = [str(k + 1) for k in range(len(acols))]
        desc_act = [cab[j].replace('\n', ' ') for j in acols]

    def por_producto(path, hoja, fragmentos):
        """Suma las columnas cuyo encabezado contenga alguno de los fragmentos."""
        d = pd.read_excel(path, sheet_name=hoja, header=None)
        cb = _txt(d.iloc[3, :])
        cols = [j for j in range(1, d.shape[1])
                if any(f.lower() in cb[j].replace('\n', ' ').lower() for f in fragmentos)]
        if not cols:
            raise KeyError(f'{hoja}: {fragmentos}')
        e0 = _txt(d.iloc[:, 0])
        rows = _filas_producto(e0)
        val = d.iloc[rows, cols].apply(_num).fillna(0).to_numpy(dtype=float).sum(axis=1)
        return pd.Series(val, index=[e0[i] for i in rows])

    # 'Importação de bens' + 'de serviços'; se excluye el ajuste CIF/FOB.
    impo_p = por_producto(t1, 'importacao', ['importação de bens', 'importação de serviços'])
    expo_p = por_producto(t2, 'demanda', ['exportação de bens', 'exportação de serviços'])
    fbcf_p = por_producto(t2, 'demanda', ['capital fixo'])

    dv = pd.read_excel(t2, sheet_name='VA', header=None)
    vlab = _txt(dv.iloc[:, 0])

    def fila(pref):
        i = next(i for i in range(len(dv)) if vlab[i].startswith(pref))
        return _num(dv.iloc[i, 1:1 + len(acols)]).to_numpy(dtype=float)

    idx = pd.Index(productos)
    return pd.DataFrame({
        'pais': 'Brasil', 'anio': anio,
        'codigo': actividades, 'desc': desc_act,
        'vbp': fila('Valor da produ'),
        'valor_agrega': fila('Valor adicionado bruto'),
        'remunera': fila('Remunera'),
        'empleo': fila('Fator trabalho'),
        'fbcf': repartir(fbcf_p.reindex(idx).fillna(0).to_numpy(), PROD),
        'expo': repartir(expo_p.reindex(idx).fillna(0).to_numpy(), PROD),
        'impo': repartir(impo_p.reindex(idx).fillna(0).to_numpy(), PROD),
    })


def brasil() -> pd.DataFrame:
    a = _brasil_anio(51, 2003, 'nivel_51_2000_2021_xls')
    a['periodo'] = 1
    b = _brasil_anio(68, 2021, 'nivel_68_2010_2021_xls')
    b['periodo'] = 2
    return pd.concat([a, b], ignore_index=True)


# ==========================================================================
# MEXICO — MIP industria por industria del INEGI (nivel rama SCIAN)
# ==========================================================================

def _mexico_2018() -> pd.DataFrame:
    """MIP 2018, base 2018. Rotulos en la columna 0, con formato 'codigo - glosa'."""
    d = pd.read_excel(f'{CEPAL}/MEX_MIP_2018/MIP_46.xlsx', sheet_name=0, header=None)
    r5 = _txt(d.iloc[5, :])
    lab = _txt(d.iloc[:, 0])

    arows = [i for i in range(6, len(d))
             if lab[i][:4].isdigit() and lab[i][4:7] == ' - ']
    codigos = [lab[i][:4] for i in arows]
    descs = [lab[i][7:] for i in arows]

    def col_por(texto):
        for j in range(d.shape[1]):
            if texto.lower() in r5[j].lower():
                return j
        raise KeyError(texto)

    def fila_por(frag):
        for i in range(len(d)):
            if frag.lower() in lab[i].lower():
                return i
        raise KeyError(frag)

    def vec(frag):
        return _num(d.iloc[fila_por(frag), 3:3 + len(arows)]).to_numpy(dtype=float)

    return pd.DataFrame({
        'pais': 'Mexico', 'anio': 2018, 'codigo': codigos, 'desc': descs,
        'vbp': vec('P.1 - Producción'),
        'valor_agrega': vec('B.1bV - Valor agregado bruto'),
        'remunera': vec('D.1 - Remuneración de los asalariados'),
        'empleo': vec('PT - Puestos de trabajo'),
        'fbcf': _num(d.iloc[arows, col_por('Formación bruta de capital fijo')]).fillna(0).to_numpy(float),
        'expo': _num(d.iloc[arows, col_por('Exportaciones de bienes')]).fillna(0).to_numpy(float),
        'impo': np.abs(_num(d.iloc[arows, col_por('Importaciones de bienes')]).fillna(0).to_numpy(float)),
    })


def _mexico_2008() -> pd.DataFrame:
    """MIP 2008, base 2003. Codigo en la columna 1 y glosa en la 2."""
    d = pd.read_excel(f'{CEPAL}/MEX_MIP_2008/MEX_MIP_2008_814 x814_IxI_TOTAL_RAMA.XLSX',
                      sheet_name=0, header=None)
    c1, c2 = _txt(d.iloc[:, 1]), _txt(d.iloc[:, 2])
    arows = [i for i in range(8, len(d)) if len(c1[i]) == 4 and c1[i].isdigit()]
    codigos = [c1[i] for i in arows]
    descs = [c2[i] for i in arows]
    n = len(arows)

    # Las columnas de demanda intermedia arrancan despues del total (c5).
    acols = list(range(6, 6 + n))

    def col_por(texto):
        for j in range(d.shape[1]):
            cab = ' '.join(_txt(d.iloc[i, :])[j] for i in range(6, 9))
            if texto.lower() in cab.lower():
                return j
        raise KeyError(texto)

    def fila_por(frag):
        for i in range(len(d)):
            if frag.lower() in (c1[i] + ' ' + c2[i]).lower():
                return i
        raise KeyError(frag)

    def vec(frag):
        return _num(d.iloc[fila_por(frag), acols]).to_numpy(dtype=float)

    return pd.DataFrame({
        'pais': 'Mexico', 'anio': 2008, 'codigo': codigos, 'desc': descs,
        'vbp': vec('PRODUCCIÓN TOTAL POR ACTIVIDAD'),
        'valor_agrega': vec('VALOR AGREGADO BRUTO A PRECIOS BÁSICOS'),
        'remunera': vec('Total de Remuneración de asalariados'),
        'empleo': vec('Total de puestos de trabajo'),
        'fbcf': _num(d.iloc[arows, col_por('FORMACIÓN BRUTA DE CAPITAL FIJO')]).fillna(0).to_numpy(float),
        'expo': _num(d.iloc[arows, col_por('EXPORTACIONES')]).fillna(0).to_numpy(float),
        'impo': np.abs(_num(d.iloc[arows, col_por('IMPORTACIONES')]).fillna(0).to_numpy(float)),
    })


def mexico() -> pd.DataFrame:
    a = _mexico_2008()
    a['periodo'] = 1
    b = _mexico_2018()
    b['periodo'] = 2
    return pd.concat([a, b], ignore_index=True)


# ==========================================================================
# ARGENTINA — MIP 1997 del INDEC (la unica con empleo y remuneraciones)
# ==========================================================================

def argentina() -> pd.DataFrame:
    B = f'{CEPAL}/ARG_MIP_1997/ARG_MIP'

    sim = pd.read_excel(f'{B}/ARG_MIP_1997_SIMÉTRICA.xls', sheet_name=0, header=None)
    n_ord = _num(sim.iloc[:, 0])
    arows = [i for i in range(6, len(sim)) if not pd.isna(n_ord[i]) and 1 <= n_ord[i] <= 124]
    descs = _txt(sim.iloc[:, 1])
    codigos = [str(int(n_ord[i])) for i in arows]
    nombres = [descs[i] for i in arows]

    cab5, cab6 = _txt(sim.iloc[5, :]), _txt(sim.iloc[6, :])
    acols = [j for j in range(2, sim.shape[1])
             if cab5[j].isdigit() and 1 <= int(cab5[j]) <= 124]
    j_exp = next(j for j in range(sim.shape[1])
                 if cab5[j].startswith('EXPORTACIONES')) + 2   # BIENES, SERVICIOS, TOTAL
    j_fbcf = next(j for j in range(sim.shape[1])
                  if cab6[j].startswith('FORMACIÓN BRUTA DE CAPITAL FIJO'))

    INT = sim.iloc[arows, acols].apply(_num).fillna(0).to_numpy(dtype=float)
    expo = _num(sim.iloc[arows, j_exp]).to_numpy(dtype=float)
    fbcf = _num(sim.iloc[arows, j_fbcf]).to_numpy(dtype=float)

    lab0 = _txt(sim.iloc[:, 1])
    i_imp = next(i for i in range(len(sim)) if lab0[i].startswith('Más: Importaciones CIF'))
    i_tax = next(i for i in range(len(sim)) if lab0[i].startswith('Más: Impuestos netos'))
    impo = _num(sim.iloc[i_imp, acols]).fillna(0).to_numpy(dtype=float)
    tax = _num(sim.iloc[i_tax, acols]).fillna(0).to_numpy(dtype=float)

    ing = pd.read_excel(f'{B}/ARG_MIP_1997_INGRESO_TRABAJO.xls', sheet_name=0, header=None)
    ilab = _txt(ing.iloc[:, 0])

    def fila_ing(pref):
        i = next(i for i in range(len(ing)) if ilab[i].startswith(pref))
        return _num(ing.iloc[i, 1:125]).to_numpy(dtype=float)

    va = fila_ing('VALOR AGREGADO BRUTO')
    remun = fila_ing('Remuneración a los asalariados')
    empleo = fila_ing('Insumo de mano de obra')

    ci = INT.sum(axis=0) + impo + tax
    out = pd.DataFrame({
        'pais': 'Argentina', 'anio': 1997, 'periodo': 1,
        'codigo': codigos, 'desc': nombres,
        'vbp': va + ci, 'valor_agrega': va, 'remunera': remun, 'empleo': empleo,
        'fbcf': fbcf, 'expo': expo, 'impo': impo,
    })
    return out


# ==========================================================================

def main():
    partes = []
    for nombre, fn in (('Chile', chile), ('Brasil', brasil),
                       ('Mexico', mexico), ('Argentina', argentina)):
        try:
            d = fn()
            partes.append(d)
            print(f'{nombre:10s} ok  ' + ' · '.join(
                f'{a} n={len(g)}' for a, g in d.groupby('anio')))
        except Exception as e:                                   # noqa: BLE001
            print(f'{nombre:10s} FALLO: {type(e).__name__}: {e}')
            raise

    d = pd.concat(partes, ignore_index=True)[COLS]
    rutas.preparar_directorios()
    d.to_csv(INTER / 'cou_multipais.csv', index=False, encoding='utf-8')
    print(f'\nEscrito {INTER}/cou_multipais.csv  ({len(d)} filas)')


if __name__ == '__main__':
    main()
