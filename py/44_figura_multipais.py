"""Bloque K.4 — figura comparativa de los cuatro paises.

F_K1, dos paneles:
  a) cuanto empleo se lleva el conglomerado mayor, por pais y por corte;
  b) productividad relativa contra participacion en el empleo, con las
     actividades atipicas rotuladas: es el mapa del problema del cobre.
"""

from __future__ import annotations

import importlib.util
import os
from datetime import date

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt                                    # noqa: E402

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

# El titulo de panel con Calibri no se dibuja en este PC; ver MEMORY.md.
TIT = dict(fontfamily='DejaVu Sans', fontsize=10)

PANELES = [('Chile', 2023), ('Brasil', 2021), ('Mexico', 2018), ('Argentina', 1997)]
COLOR = {'Chile': '#1f4e79', 'Brasil': '#2e7d32', 'Mexico': '#b23a48', 'Argentina': '#e08a1e'}
# Desplazamiento del rotulo de cada pais, para que las cuatro etiquetas no se pisen.
DESPL = [(14, -34), (14, 20), (16, -14), (14, -26)]


def main():
    d = pd.read_csv(rutas.exigir(INTER / 'cou_multipais.csv', 'la extraccion multipais'))
    d['remunera'] = d['remunera'].fillna(0.0)

    fig = plt.figure(figsize=(11, 8.2))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.45], hspace=.42)

    # ---------------- panel a: concentracion de la particion
    ax = fig.add_subplot(gs[0])
    etiquetas, series = [], {2: [], 3: [], 4: []}
    for pais, anio in PANELES:
        g = d[(d.pais == pais) & (d.anio == anio)].reset_index(drop=True)
        etiquetas.append(f'{pais}\n{anio}  (n={len(g)})')
        for k in (2, 3, 4):
            cl = uam.agrupar(uam.construir_variables(g, 'nivel'), uam.VARS_UAM, k)
            emp = g.groupby(cl)['empleo'].sum()
            series[k].append(100 * emp.max() / emp.sum())
    x = np.arange(len(etiquetas))
    for i, k in enumerate((2, 3, 4)):
        ax.bar(x + (i - 1) * .26, series[k], width=.25,
               label=f'k = {k}', color=plt.cm.Blues(.35 + .25 * i), edgecolor='white')
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, fontsize=8.5)
    ax.set_ylabel('% del empleo en el conglomerado mayor', fontsize=9)
    ax.set_ylim(0, 105)
    ax.axhline(90, color='#b23a48', lw=.9, ls='--')
    ax.text(len(x) - .45, 91.5, '90 %', color='#b23a48', fontsize=8)
    ax.legend(fontsize=8, frameon=False, ncols=3,
              loc='lower center', bbox_to_anchor=(.5, -.34))
    ax.set_title('a. La particion de la UAM deja casi todo el empleo en un solo grupo', **TIT)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)

    # ---------------- panel b: productividad contra empleo
    ax2 = fig.add_subplot(gs[1])
    for n, (pais, anio) in enumerate(PANELES):
        g = d[(d.pais == pais) & (d.anio == anio)].reset_index(drop=True)
        prod = (g['valor_agrega'] / g['empleo']) / (g['valor_agrega'].sum() / g['empleo'].sum())
        share = (100 * g['empleo'] / g['empleo'].sum()).clip(lower=1e-3)
        ax2.scatter(share, prod, s=16, alpha=.5, label=f'{pais} {anio}',
                    color=COLOR[pais], edgecolors='none')
        i = prod.idxmax()
        ax2.annotate(f'{g["desc"].iloc[i][:36]}  ({prod.iloc[i]:.0f}x)',
                     (share.iloc[i], prod.iloc[i]), fontsize=7.5, color=COLOR[pais],
                     xytext=DESPL[n], textcoords='offset points',
                     arrowprops=dict(arrowstyle='-', lw=.6, color=COLOR[pais]))
    ax2.set_yscale('log')
    ax2.set_xscale('log')
    ax2.set_xlim(8e-4, 40)
    ax2.axhline(1, color='.4', lw=.8)
    ax2.set_xlabel('participacion en el empleo del pais (%)', fontsize=9)
    ax2.set_ylabel('productividad relativa (economia = 1)', fontsize=9)
    ax2.legend(fontsize=8, frameon=False, loc='upper right')
    ax2.set_title('b. Las actividades extremas tienen empleo casi nulo: '
                  'la productividad medida es un artefacto contable', **TIT)
    for s in ('top', 'right'):
        ax2.spines[s].set_visible(False)

    fig.suptitle('Los conglomerados de la UAM aplicados a los cuatro paises',
                 fontsize=12, y=.98)
    for ext in ('png', 'pdf'):
        fig.savefig(OUT / f'F_K1 conglomerados en los cuatro paises.{ext}',
                    dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Escrita F_K1 en {OUT}')


if __name__ == '__main__':
    main()
