"""Bloque I.5 — abrir el procedimiento de Ward: la secuencia de fusiones, paso a paso.

LA PREGUNTA (DG, 2026-08-13). El agrupamiento entra al capitulo como una caja
negra: se dice "Ward sobre distancia euclidiana" y aparece una particion. Este
script la abre. Ward es aglomerativo: empieza con cada actividad en su propio
grupo y en cada paso fusiona EL PAR MAS BARATO, con el coste

    coste(A, B) = (W_A * W_B / (W_A + W_B)) * || c_A - c_B ||^2

donde c es el centroide del grupo en las variables estandarizadas y W su masa
(el numero de actividades en la version sin ponderar; el empleo en la ponderada).
Con n actividades hay exactamente n-1 pasos, y este script los escribe todos.

QUE PERMITE VER, que no se ve en la particion final:

  1. EL ORDEN. Que se fusiona temprano (lo parecido) y que se fusiona tarde (lo
     que el algoritmo junta sin ganas, ya sobre el final). Las fusiones de los
     ultimos pasos son las que definen la particion en 2, 3 o 4 grupos: son
     literalmente las unicas decisiones que el capitulo reporta.
  2. EL CRITERIO PARA ELEGIR k, que era el pendiente 4 de la auditoria del
     2026-08-12. El coste de cada fusion crece de forma monotona; donde SALTA
     esta el numero de grupos que los datos sostienen. Se reporta como R^2 —la
     fraccion de la inercia total que la particion explica— y como el salto
     relativo entre fusiones consecutivas.
  3. POR QUE se fusiona cada par. El coste se descompone exactamente por
     variable: la contribucion de la variable j es (c_Aj - c_Bj)^2 sobre la suma
     de las siete. Asi se ve si una fusion la manda la productividad, la balanza
     comercial o la remuneracion media.

  4. LA IDENTIDAD QUE CIERRA. La suma de los costes de las n-1 fusiones es
     exactamente la inercia total de la nube. O sea: Ward reparte una torta
     fija, y cada corte del dendrograma es una forma de decidir cuanta de esa
     torta queda sin explicar. Se verifica numericamente.

MODO DEMO (`--demo`). Reconstruye a mano un ejemplo chico —las 8 actividades de
mas empleo, 2 variables— imprimiendo en cada paso la matriz de distancias
completa, el par elegido, la aritmetica del coste y el centroide nuevo. Es lo
que va al apendice metodologico: en 8 unidades y 2 variables el lector puede
rehacer la cuenta con una calculadora.

Salidas: T_I20, T_I21 y F_I8 en datos/output.
"""

from __future__ import annotations

import argparse
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
HOY = date.today().strftime('%Y.%m.%d')

# Las dos especificaciones que el capitulo contrasta.
ESPECIFICACIONES = {
    'UAM': dict(balanza='nivel', logs=False, ponderar=False),
    'mejorada': dict(balanza='norm', logs=True, ponderar=True),
}

PERIODOS = {1: ('uam_replica_p1.csv', 2003), 2: ('uam_replica_p2.csv', 2023)}


# --------------------------------------------------------------------------
# 1. El aglomerativo, con historial
# --------------------------------------------------------------------------

def ward_trazado(z: np.ndarray, w: np.ndarray, etiquetas: list[str],
                 variables: list[str]) -> tuple[np.ndarray, pd.DataFrame]:
    """Ward aglomerativo con masas, devolviendo ademas el detalle de cada paso.

    Es el mismo algoritmo de `40_uam_metodo.ward_ponderado` —y el script lo
    verifica contra el, paso por paso— pero anotando en cada fusion: quienes se
    fusionan, con que masa, a que coste, y como se reparte ese coste entre las
    variables.
    """
    n = z.shape[0]
    p = z.shape[1]
    cent = z.astype(float).copy()
    masa = np.asarray(w, dtype=float).copy()
    masa_total = masa.sum()
    activo = list(range(n))
    tam = {i: 1 for i in range(n)}
    # Etiqueta legible de cada nodo: la actividad si es hoja; si no, la actividad
    # de mas peso que contiene, que es la que el lector reconoce.
    nombre = {i: etiquetas[i] for i in range(n)}
    lider = {i: i for i in range(n)}
    prox = n
    Z = np.zeros((n - 1, 4))
    filas = []

    for paso in range(n - 1):
        mejor = None
        for ii, a in enumerate(activo):
            for b in activo[ii + 1:]:
                dif = cent[a] - cent[b]
                coste = (masa[a] * masa[b] / (masa[a] + masa[b])) * float(dif @ dif)
                if mejor is None or coste < mejor[0]:
                    mejor = (coste, a, b)
        coste, a, b = mejor

        # Que se fusiona con que: por convencion, A es el de mas masa.
        if masa[a] < masa[b]:
            a, b = b, a
        dif = cent[a] - cent[b]
        contrib = dif ** 2
        d2 = float(contrib.sum())
        mn = masa[a] + masa[b]
        nuevo = (masa[a] * cent[a] + masa[b] * cent[b]) / mn

        fila = {
            'paso': paso + 1,
            'grupos tras la fusion': n - paso - 1,
            'A': nombre[a], 'n_A': tam[a], 'peso_A (%)': 100 * masa[a] / masa_total,
            'B': nombre[b], 'n_B': tam[b], 'peso_B (%)': 100 * masa[b] / masa_total,
            'distancia^2 entre centroides': d2,
            'coste de Ward': coste,
        }
        for j, v in enumerate(variables):
            fila[f'contrib {v} (%)'] = 100 * contrib[j] / d2 if d2 > 0 else np.nan
        orden = np.argsort(-contrib)
        fila['variable dominante'] = variables[int(orden[0])]
        fila['contrib dominante (%)'] = 100 * contrib[orden[0]] / d2 if d2 > 0 else np.nan
        filas.append(fila)

        cent = np.vstack([cent, nuevo])
        masa = np.append(masa, mn)
        tam[prox] = tam[a] + tam[b]
        lider[prox] = lider[a] if masa[a] >= masa[b] else lider[b]
        nombre[prox] = f'[{tam[prox]} act.] {etiquetas[lider[prox]]}'
        Z[paso] = [a, b, np.sqrt(2.0 * coste), tam[prox]]
        activo.remove(a)
        activo.remove(b)
        activo.append(prox)
        prox += 1

    Z[:, 2] = np.maximum.accumulate(Z[:, 2])
    hist = pd.DataFrame(filas)

    # --- la identidad: los n-1 costes suman la inercia total de la nube
    centro = (masa[:n, None] * z).sum(axis=0) / masa_total
    inercia = float((masa[:n] * ((z - centro) ** 2).sum(axis=1)).sum())
    hist['coste acumulado'] = hist['coste de Ward'].cumsum()
    hist['inercia sin explicar (%)'] = 100 * hist['coste acumulado'] / inercia
    hist['R2 de la particion'] = 1 - hist['coste acumulado'] / inercia
    hist['salto vs. fusion anterior'] = (
        hist['coste de Ward'] / hist['coste de Ward'].shift(1))
    hist.attrs['inercia'] = inercia
    hist.attrs['p'] = p
    return Z, hist


# --------------------------------------------------------------------------
# 2. Preparacion de una corrida
# --------------------------------------------------------------------------

def preparar(periodo: int, spec: str):
    archivo, anio = PERIODOS[periodo]
    d = pd.read_csv(rutas.exigir(INTER / archivo, 'la replica de la planilla UAM'))
    cfg = ESPECIFICACIONES[spec]
    r = uam.construir_variables(d, balanza=cfg['balanza'])
    if cfg['logs']:
        r = uam.transformar_logs(r, uam.VARS_UAM)
    w = d['empleo'].to_numpy(float) if cfg['ponderar'] else np.ones(len(d))
    z = uam.estandarizar(r, uam.VARS_UAM, w if cfg['ponderar'] else None)
    return d, anio, z, w


def verificar(z, w, Z_traza, ponderado: bool) -> str:
    """Dos controles, porque un algoritmo reescrito hay que atarlo al que ya paso auditoria."""
    Z_ref = uam.ward_ponderado(z, w)
    igual = np.allclose(Z_traza[:, 2:], Z_ref[:, 2:], rtol=0, atol=1e-9)
    msg = f'traza vs. 40_uam_metodo: alturas identicas = {igual}'
    if not ponderado:
        from scipy.cluster.hierarchy import fcluster, linkage
        Z_sp = linkage(z, method='ward', metric='euclidean')
        coinciden = all(
            uam.rand_simple(fcluster(Z_traza, t=k, criterion='maxclust'),
                            fcluster(Z_sp, t=k, criterion='maxclust')) == 1.0
            for k in range(2, 9))
        msg += f' | traza vs. scipy (k=2..8): particiones identicas = {coinciden}'
    return msg


# --------------------------------------------------------------------------
# 3. El modo demo: ocho actividades, dos variables, la cuenta a la vista
# --------------------------------------------------------------------------

def demo(periodo: int = 2, m: int = 8) -> pd.DataFrame:
    """Reconstruye Ward a mano sobre un subconjunto chico, imprimiendo todo.

    Dos variables (productividad y remuneracion media, en logaritmos) y las `m`
    actividades de mas empleo. Con dos variables la nube se dibuja en un plano y
    cada paso se rehace con calculadora, que es de lo que se trata.
    """
    d, anio, _, _ = preparar(periodo, 'mejorada')
    d = d.nlargest(m, 'empleo').reset_index(drop=True)
    r = uam.construir_variables(d, balanza='norm')
    r = uam.transformar_logs(r, uam.VARS_UAM)
    vs = ['x_prod_trabajo', 'x_remunera_prom']
    w = d['empleo'].to_numpy(float) / 1000.0        # masas en miles de ocupados
    z = uam.estandarizar(r, vs, w)

    print(f'\n{"=" * 78}\nDEMO: Ward ponderado a mano. Chile {anio}, las {m} actividades de '
          f'mas empleo,\ndos variables estandarizadas (log productividad, log remuneracion '
          f'media),\nmasas en miles de ocupados.\n{"=" * 78}\n')
    tab = pd.DataFrame({
        'actividad': [t[:44] for t in d['desc']],
        'masa (miles ocup.)': w.round(1),
        'z prod': z[:, 0].round(3),
        'z remun': z[:, 1].round(3),
    })
    print(tab.to_string(index=False))

    cent = z.astype(float).copy()
    masa = w.copy()
    nombre = {i: d['desc'].iloc[i][:30] for i in range(len(d))}
    tam = {i: 1 for i in range(len(d))}
    activo = list(range(len(d)))
    prox = len(d)
    total = 0.0
    filas = []

    for paso in range(len(d) - 1):
        print(f'\n--- PASO {paso + 1}: quedan {len(activo)} grupos '
              f'{"-" * 46}')
        costes = {}
        for ii, a in enumerate(activo):
            for b in activo[ii + 1:]:
                dif = cent[a] - cent[b]
                costes[(a, b)] = (masa[a] * masa[b] / (masa[a] + masa[b])) * float(dif @ dif)
        M = pd.DataFrame(np.nan, index=[nombre[i][:22] for i in activo],
                         columns=[nombre[i][:14] for i in activo])
        for (a, b), c in costes.items():
            M.iloc[activo.index(a), activo.index(b)] = c
        print('Coste de Ward de cada fusion posible:')
        print(M.round(2).to_string(na_rep='.'))

        (a, b), coste = min(costes.items(), key=lambda kv: kv[1])
        if masa[a] < masa[b]:
            a, b = b, a
        dif = cent[a] - cent[b]
        mn = masa[a] + masa[b]
        print(f'\nMinimo: "{nombre[a]}" + "{nombre[b]}"')
        print(f'  distancia^2 = ({cent[a][0]:.4f} - {cent[b][0]:.4f})^2 + '
              f'({cent[a][1]:.4f} - {cent[b][1]:.4f})^2 = {float(dif @ dif):.5f}')
        print(f'  coste = ({masa[a]:.1f} * {masa[b]:.1f} / {mn:.1f}) * '
              f'{float(dif @ dif):.5f} = {coste:.3f}')
        nuevo = (masa[a] * cent[a] + masa[b] * cent[b]) / mn
        print(f'  centroide nuevo = ({masa[a]:.1f}*{cent[a][0]:.4f} + '
              f'{masa[b]:.1f}*{cent[b][0]:.4f}) / {mn:.1f} = {nuevo[0]:.4f} ; '
              f'{nuevo[1]:.4f}')
        total += coste
        filas.append({'paso': paso + 1, 'A': nombre[a], 'B': nombre[b],
                      'masa A': masa[a], 'masa B': masa[b],
                      'distancia^2': float(dif @ dif), 'coste': coste,
                      'coste acumulado': total})

        cent = np.vstack([cent, nuevo])
        masa = np.append(masa, mn)
        tam[prox] = tam[a] + tam[b]
        nombre[prox] = f'G{prox} ({tam[prox]} act.)'
        activo.remove(a)
        activo.remove(b)
        activo.append(prox)
        prox += 1

    centro = (w[:, None] * z).sum(axis=0) / w.sum()
    inercia = float((w * ((z - centro) ** 2).sum(axis=1)).sum())
    print(f'\n{"=" * 78}')
    print(f'Suma de los {len(d) - 1} costes = {total:.4f}')
    print(f'Inercia total de la nube      = {inercia:.4f}')
    print(f'Diferencia                    = {abs(total - inercia):.2e}  '
          f'(la identidad se cumple: Ward reparte una torta fija)')
    print('=' * 78)
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# 4. Salidas
# --------------------------------------------------------------------------

def resumen_por_k(hist: pd.DataFrame, kmax: int = 12) -> pd.DataFrame:
    """El criterio para elegir k, leido de las ultimas fusiones."""
    h = hist.sort_values('paso', ascending=False).head(kmax).copy()
    filas = []
    for _, f in h.iterrows():
        k_antes = int(f['grupos tras la fusion']) + 1
        filas.append({
            'k': k_antes,
            'coste de pasar de k a k-1': f['coste de Ward'],
            '% de la inercia que cuesta': 100 * f['coste de Ward'] / hist.attrs['inercia'],
            'R2 con k grupos': 1 - (f['coste acumulado'] - f['coste de Ward']) / hist.attrs['inercia'],
            'salto vs. la fusion siguiente': f['salto vs. fusion anterior'],
            'que junta': f'{f["A"]}  +  {f["B"]}',
        })
    return pd.DataFrame(filas).sort_values('k')


def figura(paquetes: dict) -> None:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import dendrogram

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for etiqueta, (Z, hist) in paquetes.items():
        h = hist.sort_values('paso', ascending=False).head(12)
        ax[0].plot(h['grupos tras la fusion'] + 1,
                   100 * h['coste de Ward'] / hist.attrs['inercia'],
                   marker='o', label=etiqueta)
    ax[0].set_xlabel('numero de grupos k')
    ax[0].set_ylabel('% de la inercia que cuesta pasar de k a k-1')
    ax[0].set_title('Donde salta el coste de fusionar')
    ax[0].legend(fontsize=8)
    ax[0].grid(alpha=.3)

    etiqueta = 'mejorada' if 'mejorada 2023' in paquetes else list(paquetes)[0]
    clave = 'mejorada 2023' if 'mejorada 2023' in paquetes else list(paquetes)[0]
    Z = paquetes[clave][0]
    dendrogram(Z, ax=ax[1], no_labels=True, color_threshold=Z[-3, 2])
    ax[1].set_title(f'Dendrograma, {clave}')
    ax[1].set_ylabel('altura de fusion')
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        fig.savefig(OUT / f'F_I8 secuencia de fusiones de Ward.{ext}', dpi=200)
    plt.close(fig)


# --------------------------------------------------------------------------
# 5. Los arboles, en Mermaid: la copa del dendrograma, legible
# --------------------------------------------------------------------------

def miembros_de(Z: np.ndarray, n: int) -> dict[int, list[int]]:
    """Hojas que cuelgan de cada nodo del dendrograma."""
    m = {i: [i] for i in range(n)}
    for i, (a, b, _, _) in enumerate(Z):
        m[n + i] = m[int(a)] + m[int(b)]
    return m


def copa(Z: np.ndarray, n: int, k: int) -> tuple[list[int], list[int]]:
    """Los k-1 nodos de las ultimas fusiones y las k hojas que quedan colgando.

    Las alturas de Ward son monotonas, asi que la copa del arbol son
    literalmente las ultimas k-1 filas de Z: cortar en k grupos es no dibujar
    nada de lo que pasa por debajo.
    """
    internos = [n + len(Z) - i for i in range(1, k)]
    hojas = []
    for nodo in internos:
        a, b = int(Z[nodo - n][0]), int(Z[nodo - n][1])
        hojas += [x for x in (a, b) if x not in internos]
    return internos, hojas


def perfil(d: pd.DataFrame, idx: list[int], tot: dict) -> dict:
    g = d.iloc[idx]
    emp = g['empleo'].sum()
    return {
        'n': len(idx),
        'empleo': 100 * emp / tot['empleo'],
        'prod': (g['valor_agrega'].sum() / emp) / tot['prod'] * 100 if emp else np.nan,
        'expo': 100 * g['expo'].sum() / tot['expo'],
        'salarial': 100 * g['remunera'].sum() / g['valor_agrega'].sum(),
        'lider': g.sort_values('empleo', ascending=False)['desc'].iloc[0],
        'top': g.sort_values('empleo', ascending=False)['desc'].tolist(),
    }


def limpiar(t: str, corte: int = 42) -> str:
    """Mermaid se atraganta con parentesis, comillas y corchetes dentro de una etiqueta."""
    t = str(t).replace('(', '-').replace(')', '').replace('"', "'")
    t = t.replace('[', '').replace(']', '').replace('#', 'n.')
    if len(t) > corte:
        # Cortar en el espacio anterior: media palabra en una caja es peor que un puntito.
        t = t[:corte].rsplit(' ', 1)[0] + '...'
    return t.strip()


def coma(x: float, dec: int = 1) -> str:
    """Separador decimal espanol. El .md lo lee una persona, no un parser."""
    return f'{x:.{dec}f}'.replace('.', ',')


def arbol_mermaid(d: pd.DataFrame, Z: np.ndarray, hist: pd.DataFrame,
                  k: int, tot: dict) -> str:
    n = len(d)
    miembros = miembros_de(Z, n)
    internos, hojas = copa(Z, n, k)
    lineas = ['```mermaid', 'graph TD']
    # Un nodo interno por fusion, etiquetado con lo que esa fusion cuesta.
    for nodo in sorted(internos):
        paso = nodo - n + 1
        f = hist.iloc[paso - 1]
        grupos_antes = int(f['grupos tras la fusion']) + 1
        p = perfil(d, miembros[nodo], tot)
        lineas.append(
            f'  N{nodo}{{{{"k {grupos_antes} → {grupos_antes - 1}<br/>'
            f'cuesta {coma(100 * f["coste de Ward"] / hist.attrs["inercia"])}% '
            f'de la inercia<br/>'
            f'manda {limpiar(f["variable dominante"], 24)} · '
            f'{f["contrib dominante (%)"]:.0f}%"}}}}')
    for nodo in sorted(hojas):
        p = perfil(d, miembros[nodo], tot)
        clase = 'baja' if p['prod'] < 80 else ('alta' if p['prod'] > 130 else 'media')
        if p['expo'] > 40:
            clase = 'enclave'
        lineas.append(
            f'  N{nodo}["<b>{limpiar(p["lider"], 44)}</b><br/>'
            f'{p["n"]} act. · {coma(p["empleo"])}% del empleo<br/>'
            f'productividad {p["prod"]:.0f} · {p["expo"]:.0f}% de las expo<br/>'
            f'masa salarial {p["salarial"]:.0f}% del VA"]:::{clase}')
    for nodo in sorted(internos):
        a, b = int(Z[nodo - n][0]), int(Z[nodo - n][1])
        lineas.append(f'  N{nodo} --> N{a}')
        lineas.append(f'  N{nodo} --> N{b}')
    lineas += [
        '  classDef baja fill:#f7d7d2,stroke:#b23c17,color:#000',
        '  classDef media fill:#f2f2f2,stroke:#777,color:#000',
        '  classDef alta fill:#d6e8f7,stroke:#1f5c8b,color:#000',
        '  classDef enclave fill:#fdefc3,stroke:#a07c00,color:#000',
        '```',
    ]
    return '\n'.join(lineas)


def detalle_hojas(d: pd.DataFrame, Z: np.ndarray, k: int, tot: dict) -> str:
    n = len(d)
    miembros = miembros_de(Z, n)
    _, hojas = copa(Z, n, k)
    partes = []
    for nodo in sorted(hojas, key=lambda x: -perfil(d, miembros[x], tot)['empleo']):
        p = perfil(d, miembros[nodo], tot)
        cabeza = (f'**{p["lider"]}** — {p["n"]} act., {coma(p["empleo"])}% del empleo, '
                  f'productividad {p["prod"]:.0f}')
        lista = '; '.join(p['top'][:8])
        if p['n'] > 8:
            lista += f'; … y {p["n"] - 8} más'
        partes.append(f'- {cabeza}\n    - {lista}')
    return '\n'.join(partes)


def escribir_arboles(paquetes: dict, datos: dict, k: int = 8) -> None:
    """Un .md con los cuatro arboles en Mermaid, para leerlos en Obsidian."""
    destino = rutas.DOCS / 'notas de trabajo' / '2026-08-13-arboles-de-ward.md'
    orden = ['UAM 2023', 'mejorada 2023', 'UAM 2003', 'mejorada 2003']
    orden = [c for c in orden if c in paquetes]
    doc = [
        '---',
        'entidad: paper-he-katz',
        'rama: trabajo',
        'tipo: sintesis',
        f'fecha: {date.today().isoformat()}',
        'maquina: ESCRITORIO',
        'bloque: I',
        'tags:',
        '  - paper-he-katz',
        '---',
        '',
        '# La copa del dendrograma de Ward, en los dos ejercicios',
        '',
        'Generado por `py/27_ward_paso_a_paso.py --mermaid`. **No editar a mano**: se reescribe '
        'en cada corrida.',
        '',
        f'Cada árbol muestra las **últimas {k - 1} fusiones**, es decir la copa que va de {k} '
        'grupos a uno.',
        'Las alturas de Ward son monótonas, así que eso es exactamente lo que queda de dibujar '
        'un dendrograma completo',
        'cuando se corta en ' + str(k) + ' grupos: nada de lo que pasa por debajo cambia '
        'ninguna partición con k ≤ ' + str(k) + '.',
        '',
        'Los hexágonos son fusiones —con lo que cuestan y qué variable las manda—; las cajas son '
        'los grupos que quedan colgando.',
        'Color de las cajas: rojo, productividad bajo 80 (economía = 100); azul, sobre 130; '
        'amarillo, más del 40 % de las exportaciones del país.',
        '',
        '> [!warning] Cómo leerlo, para no leerlo al revés',
        '> El árbol se recorre **de arriba hacia abajo para deshacer fusiones**. La raíz es la '
        'última fusión, la más cara.',
        '> La partición en k grupos que reporta el capítulo es el conjunto de cajas que quedan '
        'al cortar los k−1 hexágonos de más arriba.',
        '',
    ]
    for clave in orden:
        Z, hist = paquetes[clave]
        d, tot = datos[clave]
        etiqueta = ('**Especificación de la UAM** — siete variables sin ponderar, balanza en '
                    'niveles' if clave.startswith('UAM') else
                    '**Contrapropuesta** — balanza normalizada, ponderación por empleo y '
                    'logaritmos')
        doc += [f'## {clave}', '', etiqueta + f', {len(d)} actividades.', '',
                arbol_mermaid(d, Z, hist, k, tot), '',
                '<details><summary>Qué actividades hay en cada caja</summary>', '',
                detalle_hojas(d, Z, k, tot), '', '</details>', '']
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text('\n'.join(doc), encoding='utf-8')
    print(f'Escrito el .md con los arboles en:\n  {destino}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--demo', action='store_true',
                    help='imprime el ejemplo chico paso a paso y termina')
    ap.add_argument('--mermaid', type=int, nargs='?', const=8, default=8,
                    help='cuantos grupos deja colgando el arbol del .md (por defecto 8)')
    args = ap.parse_args()

    rutas.preparar_directorios()

    if args.demo:
        demo()
        return 0

    paquetes, hojas_hist, hojas_k, datos = {}, {}, {}, {}
    for periodo in (1, 2):
        for spec in ESPECIFICACIONES:
            d, anio, z, w = preparar(periodo, spec)
            Z, hist = ward_trazado(z, w, list(d['desc']), uam.VARS_UAM)
            clave = f'{spec} {anio}'
            paquetes[clave] = (Z, hist)
            datos[clave] = (d, {
                'empleo': d['empleo'].sum(),
                'expo': d['expo'].sum(),
                'prod': d['valor_agrega'].sum() / d['empleo'].sum(),
            })
            hojas_hist[clave[:31]] = hist
            hojas_k[clave[:31]] = resumen_por_k(hist)
            print(f'\n== {clave}: {len(d)} actividades, {len(d) - 1} fusiones ==')
            print('  ' + verificar(z, w, Z, ESPECIFICACIONES[spec]['ponderar']))
            print(f'  inercia total = {hist.attrs["inercia"]:.2f}  '
                  f'(p * masa = {hist.attrs["p"] * w.sum():.2f})')
            print(resumen_por_k(hist, 8).to_string(index=False,
                                                   float_format=lambda x: f'{x:,.3f}'))

    with pd.ExcelWriter(OUT / f'{HOY} T_I20 fusiones de Ward paso a paso.xlsx') as wri:
        for nombre, h in hojas_hist.items():
            h.to_excel(wri, sheet_name=nombre, index=False)
    with pd.ExcelWriter(OUT / f'{HOY} T_I21 criterio para elegir k.xlsx') as wri:
        for nombre, h in hojas_k.items():
            h.to_excel(wri, sheet_name=nombre, index=False)
    figura(paquetes)
    escribir_arboles(paquetes, datos, k=args.mermaid)

    print(f'\nEscritas T_I20, T_I21 y F_I8 en {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
