"""Las cuatro variables que pide Gabriela Dutrénit, construidas por actividad de la COU.

EL PEDIDO. «esperamos que puedan incorporar algunas variables más, e.g. nos faltan
variables para representar los avances en sustentabilidad (huella de carbono, consumo
energético ?), digitalización, tamaño de empresa promedio», con el obstáculo declarado
un día antes: «la dificultad es el acceso a las mismas variables para todos los países».

LA VUELTA. Tres de las cuatro salen de la matriz insumo-producto, que los cuatro países
ya tienen. No hacen falta encuestas nuevas ni fuentes que sólo existan en Chile.

  x_intens_energ  consumo intermedio de productos energéticos / VBP
  x_digital       consumo intermedio de productos TIC / VBP
  x_encadena      índice de Rasmussen hacia atrás, desde la inversa de Leontief
  x_tam_empresa   trabajadores dependientes / número de empresas  <- ésta NO sale de la MIP

La cuarta necesita un registro administrativo de empresas: SII en Chile, RAIS en Brasil,
OEDE en Argentina, censos económicos e INEGI en México.

FUENTES. COU y MIP del Banco Central (bajados el 2026-08-11), `PUB_TRAM_ACT` del SII, y
la planilla de insumo de la UAM para el VBP, que es el denominador que usa el ejercicio.

DECISIONES DE CONSTRUCCIÓN.

  · Denominador VBP, para ser consistente con los ratios que ya usa el ejercicio
    (`x_ingreso_interno` = VA/VBP, `x_oferta_externa` = expo/VBP).
  · Utilización intermedia a PRECIOS DE USUARIO, que es lo que la actividad efectivamente
    pagó y la valoración con la que cierra la identidad VBP − CI = VA. A precios básicos
    los márgenes de comercio y transporte se reasignan a otras filas y el gasto en
    energía de cada actividad queda subestimado.
  · Rasmussen hacia atrás normalizado: U_j = n·Σ_i L_ij / Σ_i Σ_j L_ij. Por encima de 1
    el sector arrastra más que el promedio.
  · Tamaño de empresa excluyendo el tramo «Sin Ventas/Sin Información», como hace
    `src/08_productividad_sii.do`, para que las dos capas del repo midan lo mismo.

ADVERTENCIAS DE MEDICIÓN.

  · La COU mide GASTO en energía, no energía física. Entre países los precios relativos
    de la energía difieren; por eso `24_carbono_retc.py` valida el orden contra emisiones
    físicas. Dentro de un país y un año el problema es menor.
  · El registro del SII arranca en 2005: el tamaño de empresa del período 1 (2003) se
    calcula con 2005.
  · Los trabajadores del SII son dependientes informados en la DJ 1887 y se cuentan por
    empleador, así que quien tuvo dos empleos aparece dos veces. El tamaño medio de las
    actividades con mucha rotación queda algo sobrestimado.
  · La digitalización de 2003 y la de 2023 no son la misma variable: la nomenclatura de
    73 productos no tiene servicios informáticos. Comparables dentro del año, no entre años.

SALIDA. `$INTER/variables_nuevas_p1.csv` y `_p2.csv`, que consume 23_cluster_ampliado.py.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import rutas

DIR_BCCH = "2026.08.11 COU y MIP"

ARCHIVO_COU = {1: "2003_Cuadros_73x73.xls", 2: "2023_Cuadros_111x181.xlsx"}
ARCHIVO_MIP = {1: "2003_MIP_73x73.xls", 2: "2023_MIP_111x111.xlsx"}

# Utilización intermedia total a precios de usuario, y la inversa de Leontief
# actividad por actividad.
HOJA_UTILIZACION = {1: "6.9", 2: "5"}
HOJA_LEONTIEF = {1: "MRDIX", 2: "3"}

REGLAS_SII = {1: "reglas_ciiu_a_cou73.csv", 2: "reglas_ciiu_a_cou.csv"}
ANIO_SII = {1: 2005, 2: 2023}   # el registro del SII arranca en 2005
ANIO = {1: 2003, 2: 2023}

TOL_IDENTIDAD = 0.005   # 0,5% de discrepancia admitida en VBP − CI = VA


def leer_matriz(ruta, hoja: str, n_filas: int, n_cols: int) -> pd.DataFrame:
    """Lee un cuadro del Banco Central: código de fila en la columna 1, datos a la derecha.

    Los cuadros traen bloques de título, filas en blanco y una columna «Total» al final,
    así que se localizan los anclajes en vez de fijar coordenadas: la fila de encabezado
    es la que trae la secuencia 1, 2, 3… y las filas de datos son las que traen un código
    entero en la columna 1.
    """
    b = pd.read_excel(ruta, sheet_name=hoja, header=None)

    fila_cab = None
    for i in range(min(20, len(b))):
        v = pd.to_numeric(b.iloc[i, 2:5], errors="coerce")
        if list(v.dropna().astype(int)[:3]) == [1, 2, 3]:
            fila_cab = i
            break
    if fila_cab is None:
        raise SystemExit(f"No se encontró la fila de encabezado en la hoja {hoja}.")

    cols = pd.to_numeric(b.iloc[fila_cab, 2:], errors="coerce").to_numpy()
    cols_validas = [2 + k for k, v in enumerate(cols) if pd.notna(v) and int(v) <= n_cols]
    codigos_col = [int(cols[c - 2]) for c in cols_validas]

    filas = pd.to_numeric(b.iloc[:, 1], errors="coerce")
    idx = [i for i in range(fila_cab + 1, len(b))
           if pd.notna(filas.iloc[i]) and 1 <= int(filas.iloc[i]) <= n_filas]

    m = b.iloc[idx, cols_validas].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    m.index = [int(filas.iloc[i]) for i in idx]
    m.columns = codigos_col
    return m.sort_index().sort_index(axis=1)


def rasmussen(L: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Índices de Rasmussen hacia atrás y hacia adelante desde la inversa de Leontief."""
    n = L.shape[0]
    total = L.to_numpy().sum()
    atras = n * L.sum(axis=0) / total          # poder de dispersión (columna)
    adelante = n * L.sum(axis=1) / total       # sensibilidad de dispersión (fila)
    return atras, adelante


def tamano_empresa(periodo: int) -> pd.Series:
    """Trabajadores por empresa, por actividad de la COU, desde el registro del SII."""
    reglas = pd.read_csv(
        rutas.exigir(rutas.CONFIG / REGLAS_SII[periodo], "las reglas CIIU → COU"),
        comment="#", dtype={"prefijo": str},
    ).dropna(subset=["prefijo"])
    mapa = dict(zip(reglas["prefijo"], reglas["cou"].astype(int)))

    d = pd.read_csv(rutas.exigir(rutas.D_SII_ACT, "el archivo de actividades del SII"),
                    encoding="utf-8", low_memory=False)
    d = d[(d["anio"] == ANIO_SII[periodo]) & d["actividad"].notna()]
    d = d[d["actividad"].str[:1].str.isdigit()].copy()
    # Mismo criterio que src/08_productividad_sii.do: el tramo sin ventas ni información
    # mezcla empresas inactivas con empresas sin declarar y distorsiona el tamaño medio.
    d = d[~d["tramo13"].str.contains("Sin Ventas", na=False)]
    d["ciiu"] = d["actividad"].str[:6]

    def resolver(c: str):
        for n in range(len(c), 0, -1):
            if c[:n] in mapa:
                return mapa[c[:n]]
        return np.nan

    d["cou"] = d["ciiu"].map(resolver)
    sin = d[d["cou"].isna()]
    if len(sin):
        print(f"  AVISO: {sin['ciiu'].nunique()} actividades del SII sin regla en "
              f"{REGLAS_SII[periodo]}; quedan fuera del tamaño medio.")
    g = d.dropna(subset=["cou"]).groupby(d["cou"].astype("Int64"))[
        ["nempresas", "ntrabajadores"]].sum()
    return (g["ntrabajadores"] / g["nempresas"]).rename("x_tam_empresa")


def main() -> int:
    rutas.preparar_directorios()
    insumo = pd.read_excel(rutas.exigir(rutas.D_UAM_INSUMO, "el insumo de la UAM"))
    clasif = pd.read_csv(
        rutas.exigir(rutas.CONFIG / "clasificacion_productos_cou.csv",
                     "la clasificación de productos"))
    fallas = []

    for periodo in (1, 2):
        anio = ANIO[periodo]
        d = insumo[insumo["periodo"] == periodo].set_index("codigo_3dig").sort_index()
        n_act = len(d)

        base = rutas.D_BCCH / DIR_BCCH
        cou = rutas.exigir(base / ARCHIVO_COU[periodo], f"el COU de {anio}")
        mip = rutas.exigir(base / ARCHIVO_MIP[periodo], f"la MIP de {anio}")

        n_prod = 73 if periodo == 1 else 181
        U = leer_matriz(cou, HOJA_UTILIZACION[periodo], n_prod, n_act)
        L = leer_matriz(mip, HOJA_LEONTIEF[periodo], n_act, n_act)

        print(f"--- Período {periodo} ({anio}) ---")
        print(f"  utilización intermedia : {U.shape[0]} productos × {U.shape[1]} actividades")
        print(f"  inversa de Leontief    : {L.shape[0]} × {L.shape[1]}")

        # Identidad de la COU: VBP − consumo intermedio = valor agregado. Es el chequeo
        # que valida a la vez las unidades, la valoración y que las columnas del cuadro
        # estén alineadas con los códigos de actividad del insumo de la UAM.
        #
        # Cierra actividad por actividad salvo en «Elaboración de combustibles» y
        # «Elaboración de productos de tabaco», que son las dos con impuesto específico:
        # ahí la producción a precio básico lo excluye y la identidad no cuadra por ese
        # monto. Las dos están FUERA del ejercicio de conglomerados, así que el chequeo
        # que importa es el del subconjunto clasificado.
        ci = U.sum(axis=0)
        dif = (d["vbp"] - ci.reindex(d.index).fillna(0)) - d["valor_agrega"]
        disc = dif.abs().sum() / d["valor_agrega"].abs().sum()

        res = pd.read_excel(rutas.D_UAM_HCLUST[periodo], sheet_name="sectores_cluster")
        clasificadas = d.index.intersection(res["codigo_3dig"])
        disc_cl = (dif.loc[clasificadas].abs().sum()
                   / d.loc[clasificadas, "valor_agrega"].abs().sum())

        estado = "OK" if disc_cl < TOL_IDENTIDAD else "FALLA"
        print(f"  identidad VBP − CI = VA: {estado} "
              f"(clasificadas {disc_cl:.4%}, COU completa {disc:.3%})")
        grandes = dif.abs().sort_values(ascending=False)
        grandes = grandes[grandes > 1]
        if len(grandes):
            print(f"  no cierra en {len(grandes)} actividades, todas con impuesto específico:")
            for k in grandes.index:
                dentro = "clasificada" if k in clasificadas else "excluida del ejercicio"
                print(f"    {k:3d}  {d.loc[k, 'desc'][:48]:50s} ({dentro})")
        if disc_cl >= TOL_IDENTIDAD:
            fallas.append(f"período {periodo}: el COU no cierra contra el insumo de la UAM "
                          f"en las actividades clasificadas (discrepancia {disc_cl:.2%}); "
                          "revisar unidades y valoración")

        c = clasif[clasif["periodo"] == periodo]
        p_energia = c.loc[c["grupo"] == "energia", "cod_producto"].tolist()
        p_tic = c.loc[c["grupo"] == "tic", "cod_producto"].tolist()
        p_tic_amplio = p_tic + c.loc[c["grupo"] == "tic_amplio", "cod_producto"].tolist()

        gasto_energia = U.reindex(p_energia).sum(axis=0)
        gasto_tic = U.reindex(p_tic).sum(axis=0)
        gasto_tic_amplio = U.reindex(p_tic_amplio).sum(axis=0)

        atras, adelante = rasmussen(L)
        tam = tamano_empresa(periodo)

        v = pd.DataFrame(index=d.index)
        v["desc"] = d["desc"]
        v["x_intens_energ"] = gasto_energia.reindex(d.index) / d["vbp"]
        v["x_digital"] = gasto_tic.reindex(d.index) / d["vbp"]
        v["x_digital_amplio"] = gasto_tic_amplio.reindex(d.index) / d["vbp"]
        v["x_encadena"] = atras.reindex(d.index)
        v["x_encadena_adelante"] = adelante.reindex(d.index)
        v["x_tam_empresa"] = tam.reindex(d.index)
        v["anio"] = anio
        v["anio_sii"] = ANIO_SII[periodo]

        for col in ("x_intens_energ", "x_digital", "x_encadena", "x_tam_empresa"):
            n_falta = v[col].isna().sum()
            if n_falta:
                print(f"  AVISO: {col} sin dato en {n_falta} actividades")

        print("  intensidad energética, las 5 más altas:")
        for r in v.nlargest(5, "x_intens_energ").itertuples():
            print(f"    {r.x_intens_energ:6.1%}  {r.desc}")
        print("  digitalización, las 5 más altas:")
        for r in v.nlargest(5, "x_digital").itertuples():
            print(f"    {r.x_digital:6.2%}  {r.desc}")
        print("  tamaño medio de empresa, las 5 más altas:")
        for r in v.nlargest(5, "x_tam_empresa").itertuples():
            print(f"    {r.x_tam_empresa:8.1f}  {r.desc}")
        print(f"  encadenamiento hacia atrás: min {v['x_encadena'].min():.2f}, "
              f"mediana {v['x_encadena'].median():.2f}, máx {v['x_encadena'].max():.2f}")

        destino = rutas.INTER / f"variables_nuevas_p{periodo}.csv"
        v.to_csv(destino, encoding="utf-8")
        print(f"  guardado: {destino.name}")

    if fallas:
        print("\nProblemas de construcción:", file=sys.stderr)
        for f in fallas:
            print(f"  · {f}", file=sys.stderr)
        return 459
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
