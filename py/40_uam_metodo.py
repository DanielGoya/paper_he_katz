"""Bloque K — el metodo de conglomerados de la UAM, como modulo reutilizable.

Reconstruye los criterios con que la UAM agrupo las actividades de Chile, para
poder aplicarlos tal cual a Argentina, Brasil y Mexico:

    Ward sobre distancia euclidiana, sobre las siete variables estandarizadas
    con desviacion muestral (ddof=1).

Las siete variables, con los nombres del archivo de la UAM:

    x_prod_trabajo      valor agregado / ocupados
    x_capital_trabajo   FBCF / ocupados            (FBCF asignada por producto)
    x_remunera_prom     remuneraciones / ocupados
    x_demanda_externa   importaciones / VBP        (el nombre esta invertido en el original)
    x_balanza_com       exportaciones - importaciones, EN NIVELES
    x_ingreso_interno   valor agregado / VBP
    x_oferta_externa    exportaciones / VBP        (el nombre esta invertido en el original)

Incorpora ademas las tres mejoras de especificacion decididas para Chile, que
son las que se prueban aca para los otros paises:

    balanza normalizada  (X-M)/(X+M) en vez de X-M en niveles
    ponderacion          por empleo, en momentos y en el criterio de Ward
    logaritmos           en productividad y remuneracion media

Y la reparametrizacion del bloque de comercio (2026-08-13, ver VARS_COMERCIO),
que reemplaza TRES columnas por DOS sin perder informacion.

Este archivo NO se ejecuta solo: lo importan 41, 42, 43, 45 y 46.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage

VARS_UAM = [
    'x_prod_trabajo',
    'x_capital_trabajo',
    'x_remunera_prom',
    'x_demanda_externa',
    'x_balanza_com',
    'x_ingreso_interno',
    'x_oferta_externa',
]

# Las cinco que salen SOLO del cuadro de oferta y utilizacion, sin necesidad de
# empleo ni de remuneraciones. Son las unicas disponibles para Argentina 2021.
VARS_COU = [
    'x_capital_trabajo_vbp',
    'x_demanda_externa',
    'x_balanza_com',
    'x_ingreso_interno',
    'x_oferta_externa',
]

# --------------------------------------------------------------------------
# La reparametrizacion del bloque de comercio (decidida el 2026-08-13)
# --------------------------------------------------------------------------
# Las siete de la UAM traen TRES columnas de comercio —impo/VBP, expo/VBP y la
# balanza— y con la balanza corregida la tercera es funcion EXACTA de las otras
# dos: con o = X/VBP y d = M/VBP, el VBP se cancela y
#
#     (X-M)/(X+M) == (o-d)/(o+d)          (verificado, error 2e-16)
#     (X-M)/VBP   == o - d                (exactamente lineal: R2 = 1,0000 y
#                                          tercer valor singular = 0)
#
# O sea el bloque tiene rango 2, no 3, pero se lleva 3/7 = 42,9 % de la inercia
# porque estandarizar iguala la varianza de cada columna: una direccion se cuenta
# dos veces. Eso explica que sacar los coeficientes de comercio mueva mas la
# particion que sacar la productividad (bloque K.4).
#
# La salida no es podar sino REPARAMETRIZAR: (o, d) -> (apertura, balanza) es
# biyectiva —o = a(1+b)/2, d = a(1-b)/2— asi que no se pierde nada, y separa los
# dos conceptos que hoy estan superpuestos:
#
#     x_apertura       (X+M)/VBP     cuanto comercia la actividad
#     x_balanza_norm   (X-M)/(X+M)   en que direccion, acotado en [-1, 1]
#
# Las dos son ratios, asi que la invariancia exacta a la desagregacion se
# conserva (se verifica con la prueba de clones en 46).
VARS_COMERCIO = [
    'x_prod_trabajo',
    'x_capital_trabajo',
    'x_remunera_prom',
    'x_ingreso_interno',
    'x_apertura',
    'x_balanza_norm',
]


# --------------------------------------------------------------------------
# Construccion de las variables
# --------------------------------------------------------------------------

def construir_variables(d: pd.DataFrame, balanza: str = 'nivel') -> pd.DataFrame:
    """Arma las siete variables de la UAM desde las magnitudes de la COU.

    `d` necesita: vbp, valor_agrega, remunera, empleo, fbcf, expo, impo.
    `balanza`: 'nivel' reproduce a la UAM; 'vbp' usa (X-M)/VBP; 'norm' usa
    (X-M)/(X+M), que es la que conserva la invariancia y ademas acota.
    """
    d = d.copy()
    emp = d['empleo'].replace(0, np.nan)
    vbp = d['vbp'].replace(0, np.nan)

    d['x_prod_trabajo'] = d['valor_agrega'] / emp
    d['x_capital_trabajo'] = d['fbcf'] / emp
    d['x_remunera_prom'] = d['remunera'] / emp
    d['x_demanda_externa'] = d['impo'] / vbp
    d['x_ingreso_interno'] = d['valor_agrega'] / vbp
    d['x_oferta_externa'] = d['expo'] / vbp

    # Variante de intensidad de capital que no necesita empleo, para la
    # especificacion reducida de Argentina 2021.
    d['x_capital_trabajo_vbp'] = d['fbcf'] / vbp

    # Reparametrizacion del bloque de comercio (ver VARS_COMERCIO). Se calculan
    # siempre: son columnas nuevas y no alteran ninguna especificacion previa.
    # Una actividad sin comercio en ninguna direccion tiene apertura 0 y no es ni
    # exportadora ni importadora: le corresponde el 0 de la balanza, no un NaN.
    tot_com = d['expo'] + d['impo']
    d['x_apertura'] = tot_com / vbp
    d['x_balanza_norm'] = np.where(tot_com > 0,
                                   (d['expo'] - d['impo']) / tot_com.where(tot_com > 0), 0.0)

    if balanza == 'nivel':
        d['x_balanza_com'] = d['expo'] - d['impo']
    elif balanza == 'vbp':
        d['x_balanza_com'] = (d['expo'] - d['impo']) / vbp
    elif balanza == 'norm':
        d['x_balanza_com'] = d['x_balanza_norm']
    else:
        raise ValueError(f'balanza desconocida: {balanza}')

    return d


def transformar_logs(d: pd.DataFrame, variables: list[str],
                     log1p_ratios: bool = True) -> pd.DataFrame:
    """Logaritma productividad y remuneracion media; log1p en los ratios con ceros.

    Las estrictamente positivas van en log. Las que tienen ceros pero no
    negativos van en log1p. Las que tienen negativos —FBCF por ocupado, que la
    COU asigna por producto— se dejan como estan: no admiten logaritmo.

    `x_balanza_norm` NUNCA se transforma: ya esta acotada en [-1, 1] y es
    aproximadamente simetrica, que es lo que el logaritmo vendria a arreglar.

    ⚠ `log1p_ratios=False` deja los ratios de comercio en nivel. Existe porque
    Chen y Roth (2024, QJE) muestran que log(1+y) no es invariante a las
    unidades: la constante 1 es arbitraria y afecta la particion. En un ratio el
    problema es mas debil que en una magnitud —no hay unidad que elegir— pero no
    desaparece, asi que la sensibilidad se mide y se reporta (46).
    """
    d = d.copy()
    for v in ('x_prod_trabajo', 'x_remunera_prom'):
        if v not in variables:
            continue
        s = d[v]
        pos = s[s > 0]
        if pos.empty:
            continue
        piso = pos.min() / 2.0
        d[v] = np.log(s.clip(lower=piso))
    if log1p_ratios:
        for v in ('x_demanda_externa', 'x_oferta_externa', 'x_apertura'):
            if v in variables and (d[v].dropna() >= 0).all():
                d[v] = np.log1p(d[v])
    return d


# --------------------------------------------------------------------------
# Estandarizacion y agrupamiento
# --------------------------------------------------------------------------

def estandarizar(d: pd.DataFrame, variables: list[str],
                 pesos: np.ndarray | None = None) -> np.ndarray:
    """Puntajes z. Sin pesos usa desviacion MUESTRAL (ddof=1), como la UAM."""
    x = d[variables].to_numpy(dtype=float)
    if pesos is None:
        mu = x.mean(axis=0)
        sd = x.std(axis=0, ddof=1)
    else:
        w = np.asarray(pesos, dtype=float)
        w = w / w.sum()
        mu = (w[:, None] * x).sum(axis=0)
        var = (w[:, None] * (x - mu) ** 2).sum(axis=0)
        # Correccion de sesgo analoga a ddof=1 para pesos de frecuencia.
        sd = np.sqrt(var / max(1e-12, 1.0 - (w ** 2).sum()))
    sd = np.where(sd == 0, 1.0, sd)
    return (x - mu) / sd


def ward_ponderado(z: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Ward aglomerativo con masas. Coste (Wa*Wb/(Wa+Wb))*||ca-cb||^2.

    scipy no admite pesos, asi que el aglomerativo va explicito. Con pesos
    enteros equivale a replicar cada observacion w veces.
    """
    n = z.shape[0]
    cent = z.astype(float).copy()
    masa = np.asarray(w, dtype=float).copy()
    activo = list(range(n))
    tam = {i: 1 for i in range(n)}
    hijos: dict[int, tuple[int, int]] = {}
    prox = n
    Z = np.zeros((n - 1, 4))

    for paso in range(n - 1):
        mejor = None
        for ii, a in enumerate(activo):
            for b in activo[ii + 1:]:
                dif = cent[a] - cent[b]
                coste = (masa[a] * masa[b] / (masa[a] + masa[b])) * float(dif @ dif)
                if mejor is None or coste < mejor[0]:
                    mejor = (coste, a, b)
        coste, a, b = mejor
        mn = masa[a] + masa[b]
        nuevo = (masa[a] * cent[a] + masa[b] * cent[b]) / mn
        cent = np.vstack([cent, nuevo])
        masa = np.append(masa, mn)
        tam[prox] = tam[a] + tam[b]
        hijos[prox] = (a, b)
        Z[paso] = [a, b, np.sqrt(2.0 * coste), tam[prox]]
        activo.remove(a)
        activo.remove(b)
        activo.append(prox)
        prox += 1

    # scipy exige distancias monotonas para cortar por numero de grupos; el
    # coste de Ward ya lo es salvo empates numericos.
    Z[:, 2] = np.maximum.accumulate(Z[:, 2])
    return Z


def agrupar(d: pd.DataFrame, variables: list[str], k: int,
            pesos: np.ndarray | None = None) -> np.ndarray:
    """Devuelve la particion en k grupos. Sin pesos es exactamente la UAM."""
    x = d[variables].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        malas = [v for i, v in enumerate(variables) if not np.isfinite(x[:, i]).all()]
        # Un solo dato faltante vuelve NaN toda la matriz de distancias y el corte
        # devuelve tantos grupos como observaciones, en silencio. Mejor que falle.
        raise ValueError(f'variables con valores no finitos: {malas}')
    z = estandarizar(d, variables, pesos)
    if pesos is None:
        Z = linkage(z, method='ward', metric='euclidean')
    else:
        Z = ward_ponderado(z, np.asarray(pesos, dtype=float))
    return fcluster(Z, t=k, criterion='maxclust')


# --------------------------------------------------------------------------
# Comparacion de particiones
# --------------------------------------------------------------------------

def rand_ajustado(a, b) -> float:
    """Indice de Rand ajustado, sin dependencias de sklearn."""
    a = pd.Series(np.asarray(a))
    b = pd.Series(np.asarray(b))
    tab = pd.crosstab(a, b).to_numpy(dtype=float)
    n = tab.sum()
    if n < 2:
        return float('nan')

    def c2(x):
        return x * (x - 1.0) / 2.0

    suma_ij = c2(tab).sum()
    suma_i = c2(tab.sum(axis=1)).sum()
    suma_j = c2(tab.sum(axis=0)).sum()
    esperado = suma_i * suma_j / c2(n)
    maximo = (suma_i + suma_j) / 2.0
    if maximo == esperado:
        return 1.0
    return float((suma_ij - esperado) / (maximo - esperado))


def rand_simple(a, b) -> float:
    """Indice de Rand sin ajustar, que es el que reporta la UAM."""
    a = np.asarray(a)
    b = np.asarray(b)
    n = len(a)
    ia = a[:, None] == a[None, :]
    ib = b[:, None] == b[None, :]
    iu = np.triu_indices(n, k=1)
    return float((ia[iu] == ib[iu]).mean())
