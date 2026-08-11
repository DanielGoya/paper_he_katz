"""Bloque J. La salmonicultura chilena: actualización de las tablas y figuras de Katz.

POR QUÉ. El capítulo 4 del libro FCE de Jorge Katz (`4.1. La salmonicultura chilena`) y su
versión para el CINVE construyen la narrativa evolutiva de la industria sobre evidencia que
se detiene entre 2007 y 2016: la tabla de biomasa por centro es de EWOS (Puerto Varas,
noviembre de 2007), la tabla de indicadores productivos cubre 2002-2007, la gráfica del
`catch-up` con Noruega termina en 2002, la de permisos de cultivo en 2011 y los dos gráficos
nativos del presupuesto y la dotación de Sernapesca en 2016. Este bloque reconstruye esa
evidencia con las fuentes vigentes, sin cambiar las preguntas: son las mismas magnitudes,
veinte años después.

QUÉ RESPONDE. Cuatro afirmaciones de Katz que ahora quedan medidas:

1. «Chile alcanzó a Noruega» — el `catch-up` se detuvo en 2006 y la brecha se reabrió.
2. «Sus precios cotizan por debajo de los de Noruega» — se confirma, y se cuantifica por
   forma de producto, que es donde estaba la duda (Chile vende filete, Noruega pez entero).
3. «El talón de Aquiles es la fragilidad sanitaria, que resulta en elevado uso de
   antibióticos» — se confirma, con una brecha con Noruega de tres órdenes de magnitud.
4. «Una industria altamente concentrada» — CR4 y CR10 de la cosecha, contra Noruega.

Y agrega el resultado que conecta con el objeto del libro: la dispersión del uso de
antimicrobianos ENTRE empresas de la misma rama es de dos órdenes de magnitud. Es
heterogeneidad estructural dentro de la rama, medida sobre una variable ambiental.

FUENTES.
  · FAO FishStat, Global Aquaculture Production 2025.1.0 (almacén). Producción 1950-2023.
  · BACI CEPII HS22 V202601 (almacén). Comercio 2022-2024 a seis dígitos.
  · Sernapesca, informes de uso de antimicrobianos 2023 y 2024, e informes de situación
    sanitaria de la salmonicultura 2024 y 2025 (`datos/raw_local/salmonicultura`).
  · Norwegian Veterinary Institute, Fish Health Report 2024; Fiskeridirektoratet, Key
    figures from Norwegian Aquaculture Industry 2024 (misma carpeta).
  · DIPRES, Ley de Presupuestos 2016-2026, partida 07 capítulo 04 (misma carpeta).
  · Banco Mundial WDI, IPC de Chile (`config/ipc_chile_wdi.csv`).
  · Los dos gráficos nativos del .docx de Katz, cuyas series se leyeron del XML del archivo.

SALIDAS. Tablas T_J1 a T_J8 y figuras F_J1 a F_J5 en `$OUT`.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import rutas

# DejaVu Sans y no Calibri, a diferencia de los otros bloques. Con Calibri en este equipo
# matplotlib 3.11 calcula ancho cero para parte del texto y lo deja sin dibujar —se pierden
# las etiquetas de la leyenda o las de los ejes, y cambia de una corrida a otra—. DejaVu Sans
# viene con matplotlib y no falla. Vale la pena revisar si las figuras de los bloques A-I
# tienen el mismo problema latente.
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "figure.dpi": 130,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

D_FAO = rutas.ALMACEN / "FAO FishStat" / "Aquaculture_2025.1.0.zip"
D_BACI = rutas.ALMACEN / "Dat_bacii" / "BACI_HS22_V202601"
D_IPC = rutas.CONFIG / "ipc_chile_wdi.csv"

# Las gráficas del libro, extraídas del .docx y guardadas con su LEEME. Van al lado de las
# actualizadas: sin el original a la vista no se ve hasta dónde llegaba la evidencia.
D_ORIG = rutas.INTER / "figuras_originales_katz"
ORIGINALES = {
    "catchup": ("original catch-up Chile-Noruega 1990-2002.png", 2002),
    "enfermedades": ("original enfermedades y produccion 1985-2007.png", 2007),
    "region": ("original produccion por region 2006-2012.png", 2012),
    "ovas": ("original ovas importadas y locales 1984-2008.png", 2008),
    "permisos": ("original nuevos permisos por region 1982-2011.png", 2011),
}


def poner_original(eje, clave: str, titulo: str) -> None:
    """Dibuja el recorte de la gráfica del libro en un eje, sin ejes ni marco."""
    ruta = D_ORIG / ORIGINALES[clave][0]
    eje.set_axis_off()
    if not rutas.hay(ruta):
        eje.text(0.5, 0.5, f"falta {ruta.name}", ha="center", va="center", fontsize=8)
        return
    eje.imshow(plt.imread(ruta))
    eje.set_title(titulo, fontsize=10, loc="left")


def marcar_corte(eje, anio: int, texto: str, y: float = 0.94) -> None:
    """Raya vertical y etiqueta en el año hasta donde llegaba la gráfica del libro."""
    eje.axvline(anio, color="#7f8c8d", ls="--", lw=1.1)
    eje.annotate(texto, xy=(anio, y), xycoords=("data", "axes fraction"),
                 xytext=(6, 0), textcoords="offset points", fontsize=8, color="#555555",
                 va="top")

# Los seis países de la gráfica original de Katz (`El "Catch-up" de la industria salmonera
# Chilena, 1990-2002`), con sus nombres tal como los escribe FAO.
PAISES = {
    "Norway": "Noruega",
    "Chile": "Chile",
    "United Kingdom of Great Britain and Northern Ireland": "Reino Unido",
    "Canada": "Canadá",
    "Faroe Islands": "Islas Feroe",
    "Australia": "Australia",
}

# Salmónidos de cultivo. Familia Salmonidae, quitando las especies sin producción
# comercial relevante: es el agregado con que se cuenta la industria en los dos países.
SALMONIDOS = {"SAL", "COH", "TRR", "ORC", "CHI", "CHU", "SOC", "PIN", "TRS", "TRO",
              "SLZ", "CHE", "ACH", "CHR", "LAT", "SVF"}

# Partidas de salmónidos del HS 2022. HS92 no identifica el filete de salmón, y el filete
# es la mitad de lo que exporta Chile: por eso el detalle de comercio se hace en HS22 y no
# se intenta una serie larga que quedaría sesgada contra Chile.
PARTIDAS = {
    "030213": "Salmón del Pacífico, fresco o refrigerado",
    "030214": "Salmón del Atlántico, fresco o refrigerado",
    "030311": "Salmón rojo (sockeye), congelado",
    "030312": "Salmón del Pacífico n.e.p., congelado",
    "030313": "Salmón del Atlántico, congelado",
    "030441": "Filetes de salmón, frescos o refrigerados",
    "030481": "Filetes de salmón, congelados",
    "030541": "Salmón ahumado",
    "160411": "Salmón preparado o en conserva",
}
COD_CHILE, COD_NORUEGA = "152", "579"

# ---------------------------------------------------------------------------
# Datos publicados en tablas de informes, transcritos con su fuente al lado.
# No se leen programáticamente porque vienen en PDF; se dejan acá para que la
# tabla de salida sea auditable contra el informe línea por línea.
# ---------------------------------------------------------------------------

# Sernapesca, informe de uso de antimicrobianos, tabla 1. Los años 2007-2013 vienen del
# informe del año 2023 y 2014-2024 del informe del año 2024; coinciden en el traslape.
ANTIMICROBIANOS_CL = [
    # año, principio activo (t), biomasa cosechada (t)
    (2007, 385.6, 600_862), (2008, 325.6, 630_647), (2009, 184.5, 474_174),
    (2010, 143.2, 466_857), (2011, 206.8, 649_492), (2012, 337.9, 826_949),
    (2013, 450.7, 786_091), (2014, 563.2, 955_179), (2015, 557.2, 883_102),
    (2016, 382.5, 727_812), (2017, 393.9, 855_326), (2018, 322.7, 923_900),
    (2019, 334.1, 989_546), (2020, 379.6, 1_075_896), (2021, 463.4, 985_958),
    (2022, 341.5, 1_066_645), (2023, 338.9, 1_107_109), (2024, 351.1, 1_035_307),
]

# Norwegian Veterinary Institute, Fish Health Report 2024, tabla 7.10.1 (registro VetReg).
# Kilos de principio activo para TODO el pez de cultivo, incluidos peces limpiadores y
# especies marinas: es una cota superior de lo que consume la salmonicultura.
ANTIBIOTICOS_NO = {2015: 267, 2016: 199, 2017: 607, 2018: 930, 2019: 218,
                   2020: 220, 2021: 588, 2022: 425, 2023: 548, 2024: 709}

# Sernapesca, informes de situación sanitaria, «porcentaje de mortalidad por ciclo cerrado».
MORTALIDAD_CL = {
    2024: {"Salmón del Atlántico": 11.0, "Trucha arcoíris": 12.9, "Salmón coho": 6.8},
    2025: {"Salmón del Atlántico": 10.1, "Trucha arcoíris": 7.2, "Salmón coho": 4.8},
}
# Fish Health Report 2024, cap. 2.3: «annual cumulative mortality risk», 2024.
MORTALIDAD_NO_2024 = {"Salmón del Atlántico": 15.4, "Trucha arcoíris": 15.0}

# Sernapesca, informe de antimicrobianos 2024, tabla 4: ciclos cerrados del año 2024.
HOLDINGS_2024 = [
    # holding, ciclos, antimicrobianos (kg), biomasa muerta (t), cosecha (t)
    ("Empresas AquaChile", 90, 40_756.41, 10_775.46, 253_877.34),
    ("Cermaq Chile", 21, 44_335.61, 5_877.22, 90_651.09),
    ("Multi-X", 22, 56_958.55, 7_141.12, 87_879.00),
    ("Mowi Chile", 18, 40_656.68, 6_101.13, 86_616.73),
    ("Salmones Austral", 13, 18_229.04, 3_008.79, 64_382.95),
    ("Salmones Aysén", 18, 2_656.66, 2_173.01, 63_999.75),
    ("Salmones Camanchaca", 12, 24_095.21, 1_578.60, 57_163.27),
    ("Australis Mar", 16, 7_707.04, 2_171.08, 52_336.02),
    ("Blumar", 12, 10_423.50, 5_319.00, 47_188.74),
    ("Productos del Mar Ventisqueros", 13, 8_784.60, 3_357.67, 43_586.42),
    ("Marine Farm", 12, 16_253.83, 1_186.98, 41_323.96),
    ("Salmones Antártica", 11, 13_901.12, 3_185.88, 35_633.86),
    ("Invermar", 7, 25_311.52, 1_446.45, 33_045.62),
    ("Empresas Yadran", 9, 18_061.42, 1_970.39, 29_823.22),
    ("Caleta Bay", 9, 459.03, 2_436.77, 25_193.76),
    ("Cooke Aquaculture Chile", 8, 1_550.32, 1_094.89, 16_543.17),
    ("Salmones de Chile", 7, 6_119.84, 1_663.27, 15_967.73),
    ("Nova Austral", 3, 0.00, 726.89, 5_800.86),
]

# Fiskeridirektoratet, Key figures 2024, tabla 20: venta de las diez mayores empresas.
CR10_NORUEGA = {2020: 65.8, 2021: 66.8, 2022: 69.3, 2023: 68.7, 2024: 69.0}

# Sernapesca, informe de antimicrobianos 2024, tabla 3: ciclos cerrados por región.
# Es el equivalente actual de la gráfica «Expansión de la frontera de explotación acuícola
# hacia Aysén» del libro, que llega a 2012.
COSECHA_REGION_2024 = {"Los Lagos": 547_628.45, "Aysén": 395_369.06,
                       "Magallanes": 108_015.97}
CENTROS_REGION_2024 = {"Los Lagos": 148, "Aysén": 130, "Magallanes": 23}   # ciclos cerrados
# Lectura de la gráfica del libro para el primer y el último año que muestra, en toneladas.
# Son valores leídos del gráfico, no cifras publicadas: sirven para la proporción, no para
# citar niveles.
COSECHA_REGION_LIBRO = {
    2006: {"Los Lagos": 500_000, "Aysén": 135_000, "Magallanes": 5_000},
    2012: {"Los Lagos": 343_000, "Aysén": 424_000, "Magallanes": 35_000},
}

# Sernapesca, informes de situación sanitaria: centros marinos activos por mes.
CENTROS_CL = {
    2024: [313, 302, 313, 326, 337, 347, 350, 357, 340, 331, 332, 342],
    2025: [346, 337, 337, 362, 364, 371, 374, 386, 381, 375, 372, 362],
}
# Biomasa en cultivo en centros marinos, miles de toneladas, por mes.
BIOMASA_CL = {
    2024: [423.5, 408.8, 422.2, 451.9, 481.8, 517.0, 540.9, 545.5, 552.6, 531.0, 518.3, 475.6],
    2025: [473.4, 464.7, 490.6, 525.8, 567.6, 609.9, 646.1, 661.1, 655.4, 631.3, 590.7, 538.1],
}

# EWOS, `Comparación de resultados productivos en salmón atlántico. Noruega-Chile`,
# Puerto Varas, noviembre de 2007. Es la tabla 1 del libro de Katz.
BIOMASA_CENTRO_2007 = {"Chile": 1_021, "Noruega": 474}

# Fiskeridirectoratet, Key figures 2024: tablas 9, 11, 13 y 19.
NORUEGA_2024 = {
    "centros_mar": 994,          # centros de mar de salmón y trucha al 31.12.2024
    "empresas_engorda": 168,     # empresas con producción de engorda
    "empleo": 7_393 + 2_163,     # engorda + esmoltificación
    "cosecha": 1_552_887 + 95_863,   # salmón del Atlántico + trucha arcoíris
}

# Gráficos nativos del .docx de Katz (`word/charts/chart1.xml` y `chart2.xml`), leídos del
# XML del archivo: son sus propias series, no una reconstrucción.
PRESUP_SERNAPESCA = {
    1981: 81.083, 1982: 102.779, 1983: 102.194, 1984: 122.881, 1985: 158.765,
    1986: 190.373, 1987: 256.970, 1988: 322.872, 1989: 389.251, 1990: 435.237,
    1991: 883.872, 1992: 1_082.707, 1993: 1_457.351, 1994: 1_688.087, 1995: 2_058.729,
    1996: 2_819.687, 1997: 3_373.295, 1998: 3_856.647, 1999: 4_001.040, 2000: 4_270.198,
    2001: 4_039.275, 2002: 4_198.119, 2003: 4_967.567, 2004: 5_662.134, 2005: 6_773.723,
    2006: 7_392.116, 2007: 10_273.447, 2008: 15_346.149, 2009: 17_666.899, 2010: 19_299.047,
    2011: 20_687.957, 2012: 22_464.495, 2013: 25_862.790, 2014: 29_144.308, 2015: 34_926.602,
    2016: 39_999.976,
}
# DIPRES, Ley de Presupuestos, partida 07 (Economía), capítulo 04 (Sernapesca),
# programa 01, línea GASTOS, en millones de pesos de cada año. Bajado de las planillas
# oficiales, archivadas en `datos/raw_local/salmonicultura/DIPRES Sernapesca`.
PRESUP_DIPRES = {
    2012: 20_240.102, 2013: 22_517.796, 2014: 25_504.000, 2015: 29_134.900,
    2016: 32_565.760, 2017: 36_768.878, 2018: 38_290.370, 2019: 33_257.358,
    2020: 34_116.850, 2021: 33_193.882, 2022: 34_928.173, 2023: 38_640.157,
    2024: 42_324.969, 2025: 45_773.777, 2026: 46_517.850,
}

# QUÉ MIDE LA SERIE DEL LIBRO, RESUELTO.
# En 2016 el gráfico de Katz marca 40.000 millones y la Ley de Presupuestos 32.566: un 23%
# de diferencia que había que explicar antes de extender nada. La respuesta está en las
# «planillas de decretos por programa» de DIPRES, que registran las modificaciones
# presupuestarias totalmente tramitadas de cada año. Sumadas a la ley inicial dan el
# PRESUPUESTO VIGENTE, y éste reproduce la serie del libro:
#
#   año    ley inicial   + decretos = vigente     serie de Katz    razón
#   2013      22.517,8      3.345,1   25.862,8       25.862,8      1,0000
#   2014      25.504,0      3.640,3   29.144,3       29.144,3      1,0000
#   2015      29.134,9      5.791,7   34.926,6       34.926,6      1,0000
#   2016      32.565,8      7.432,8   39.998,6       40.000,0      1,0000
#   2012      20.240,1      2.006,6   22.246,7       22.464,5      1,0098
#
# O sea la serie del libro es el presupuesto VIGENTE, no la ley inicial. Eso permite
# extenderla sin empalmes artificiales: desde 2017 el vigente se lee directamente del
# informe de ejecución del cuarto trimestre, que trae las tres columnas.
PRESUP_VIGENTE = {
    2017: 39_570.4, 2018: 41_492.9, 2019: 33_952.6, 2020: 33_703.1, 2021: 36_585.9,
    2022: 41_473.2, 2023: 45_439.7, 2024: 50_080.5, 2025: 54_111.7,
}
PRESUP_DEVENGADO = {
    2017: 36_438.4, 2018: 40_156.7, 2019: 33_282.3, 2020: 33_233.7, 2021: 35_796.0,
    2022: 39_984.5, 2023: 42_996.8, 2024: 46_141.8, 2025: 48_931.1,
}
# Vigente reconstruido sumando decretos, para los años que se traslapan con el libro.
# Es la verificación de arriba, y se reporta en la tabla para que quede auditable.
VIGENTE_DECRETOS = {
    2012: 22_246.7, 2013: 25_862.8, 2014: 29_144.3, 2015: 34_926.6, 2016: 39_998.6,
    2017: 39_569.6, 2018: 41_169.5, 2019: 33_950.9, 2020: 33_702.2,
}
# Glosa «Dotación máxima de personal» de la misma Ley de Presupuestos.
DOTACION_MAXIMA = {
    2016: 966, 2017: 986, 2018: 989, 2019: 1_004, 2020: 1_259, 2021: 1_188,
    2022: 1_171, 2023: 1_176, 2024: 1_197, 2025: 1_204, 2026: 1_219,
}
# Dotación efectiva, del gráfico nativo del .docx de Katz.
DOTACION_SERNAPESCA = {
    2002: 311, 2003: 326, 2004: 340, 2005: 348, 2006: 349, 2007: 347, 2008: 344,
    2009: 489, 2010: 484, 2011: 523, 2012: 520, 2013: 575, 2014: 793, 2015: 899, 2016: 890,
}


# ---------------------------------------------------------------------------
# 1. Producción: el catch-up que se detuvo
# ---------------------------------------------------------------------------
def _leer_fao(nombre: str) -> list[dict]:
    with zipfile.ZipFile(rutas.exigir(D_FAO, "FishStat Aquaculture")) as z:
        crudo = z.read(nombre).decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(crudo)))


def produccion() -> pd.DataFrame:
    paises = {x["UN_Code"]: x["Name_En"] for x in _leer_fao("CL_FI_COUNTRY_GROUPS.csv")}
    filas: dict[tuple[str, int], float] = defaultdict(float)
    mundo: dict[int, float] = defaultdict(float)
    for r in _leer_fao("Aquaculture_Quantity.csv"):
        if r["MEASURE"] != "Q_tlw" or r["SPECIES.ALPHA_3_CODE"] not in SALMONIDOS:
            continue
        anio, valor = int(r["PERIOD"]), float(r["VALUE"])
        mundo[anio] += valor
        pais = paises.get(r["COUNTRY.UN_CODE"])
        if pais in PAISES:
            filas[(PAISES[pais], anio)] += valor
    anios = sorted(a for a in mundo if 1990 <= a)
    d = pd.DataFrame(
        {p: [filas.get((p, a), np.nan) / 1000 for a in anios] for p in PAISES.values()},
        index=anios,
    )
    d["Mundo"] = [mundo[a] / 1000 for a in anios]
    d["Chile / Noruega"] = d["Chile"] / d["Noruega"]
    d["Chile, % del mundo"] = 100 * d["Chile"] / d["Mundo"]
    d["Noruega, % del mundo"] = 100 * d["Noruega"] / d["Mundo"]
    d.index.name = "anio"
    return d


def figura_catchup(d: pd.DataFrame) -> None:
    corte = ORIGINALES["catchup"][1]
    fig, ejes = plt.subplots(1, 3, figsize=(16.6, 4.5),
                             gridspec_kw={"width_ratios": [1.05, 1.2, 1.0]})
    poner_original(ejes[0], "catchup",
                   f"a. La gráfica del libro: «El catch-up de la industria salmonera\n"
                   f"    chilena», 1990-{corte}")

    colores = {"Noruega": "#1f4e79", "Chile": "#c0392b", "Reino Unido": "#e0a800",
               "Canadá": "#7f8c8d", "Islas Feroe": "#6c3483", "Australia": "#117a65"}
    e = ejes[1]
    for p, c in colores.items():
        e.plot(d.index, d[p], color=c, lw=2.0 if p in ("Chile", "Noruega") else 1.2, label=p)
    e.axvspan(1990, corte, color="#000000", alpha=0.05)
    marcar_corte(e, corte, "hasta acá\nllega el original", y=0.62)
    e.set_ylabel("miles de toneladas")
    e.set_title("b. La misma serie, hasta el último dato disponible", fontsize=10, loc="left")
    e.legend(fontsize=8, ncol=2, frameon=False, loc="upper left")

    e = ejes[2]
    e.plot(d.index, d["Chile / Noruega"], color="#c0392b", lw=2.2)
    e.axhline(1.0, color="#333333", lw=0.9, ls="--")
    e.axvspan(1990, corte, color="#000000", alpha=0.05)
    marcar_corte(e, corte, "", y=0.5)
    pico = d["Chile / Noruega"].idxmax()
    e.annotate(f"{pico}: {d.loc[pico, 'Chile / Noruega']:.2f}",
               xy=(pico, d.loc[pico, "Chile / Noruega"]),
               xytext=(pico - 10.5, d.loc[pico, "Chile / Noruega"] - 0.11), fontsize=8,
               arrowprops=dict(arrowstyle="->", color="#999999", lw=0.8))
    ult = int(d.index.max())
    e.annotate(f"{ult}: {d.loc[ult, 'Chile / Noruega']:.2f}",
               xy=(ult, d.loc[ult, "Chile / Noruega"]),
               xytext=(ult - 11, d.loc[ult, "Chile / Noruega"] - 0.14), fontsize=8,
               arrowprops=dict(arrowstyle="->", color="#999999", lw=0.8))
    e.set_ylim(0.15, 1.12)
    e.set_ylabel("razón")
    e.set_title("c. Producción de Chile respecto de la de Noruega", fontsize=10, loc="left")
    for e in ejes[1:]:
        e.set_xlim(1990, ult)
    fig.suptitle("El catch-up con Noruega se detuvo en 2006, y la gráfica del libro "
                 "termina justo antes", fontsize=12.5, x=0.06, ha="left", y=1.02)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_J1 catch-up de la salmonicultura", ext),
                    bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 2. Antimicrobianos: el talón de Aquiles, medido
# ---------------------------------------------------------------------------
def antimicrobianos(prod: pd.DataFrame) -> pd.DataFrame:
    d = pd.DataFrame(ANTIMICROBIANOS_CL,
                     columns=["anio", "principio_activo_t", "cosecha_t"]).set_index("anio")
    # Toneladas de principio activo a gramos, sobre toneladas cosechadas.
    d["indice_g_por_t"] = d["principio_activo_t"] * 1_000_000 / d["cosecha_t"]
    d["noruega_kg"] = [ANTIBIOTICOS_NO.get(a, np.nan) for a in d.index]
    d["noruega_cosecha_t"] = [prod["Noruega"].get(a, np.nan) * 1000 for a in d.index]
    d.loc[2024, "noruega_cosecha_t"] = NORUEGA_2024["cosecha"]
    d["noruega_g_por_t"] = 1000 * d["noruega_kg"] / d["noruega_cosecha_t"]
    d["veces_chile_sobre_noruega"] = d["indice_g_por_t"] / d["noruega_g_por_t"]
    return d


def figura_antimicrobianos(d: pd.DataFrame) -> None:
    corte = ORIGINALES["enfermedades"][1]
    fig, ejes = plt.subplots(1, 3, figsize=(16.6, 4.5),
                             gridspec_kw={"width_ratios": [1.0, 1.15, 1.0]})
    poner_original(ejes[0], "enfermedades",
                   f"a. La gráfica sanitaria del libro: «Catching up y sobreexplotación\n"
                   f"    del recurso», 1985-{corte}")
    ejes = [ejes[1], ejes[2]]
    e = ejes[0]
    e.bar(d.index, d["principio_activo_t"], color="#b0c4de", label="toneladas de principio activo")
    e.set_ylabel("toneladas")
    e2 = e.twinx()
    e2.plot(d.index, d["indice_g_por_t"], color="#c0392b", lw=2.2, marker="o", ms=3.5,
            label="gramos por tonelada cosechada")
    e2.set_ylabel("gramos por tonelada cosechada")
    e2.grid(False)
    e.set_xticks(range(2007, 2025, 3))
    marcar_corte(e, corte, "el original\ntermina acá", y=0.62)
    e.set_title("b. Chile: cantidad e intensidad del uso de antimicrobianos, 2007-2024",
                fontsize=10, loc="left")
    lineas = e.get_legend_handles_labels()[0] + e2.get_legend_handles_labels()[0]
    etiq = e.get_legend_handles_labels()[1] + e2.get_legend_handles_labels()[1]
    e.legend(lineas, etiq, fontsize=8, frameon=False, loc="upper left")

    e = ejes[1]
    v = d.dropna(subset=["noruega_g_por_t"])
    e.plot(v.index, v["indice_g_por_t"], color="#c0392b", lw=2.2, marker="o", ms=3.5,
           label="Chile")
    e.plot(v.index, v["noruega_g_por_t"], color="#1f4e79", lw=2.2, marker="s", ms=3.5,
           label="Noruega")
    e.set_yscale("log")
    e.set_ylim(0.05, 3_000)
    e.set_yticks([0.1, 1, 10, 100, 1000])
    e.set_yticklabels(["0,1", "1", "10", "100", "1.000"])
    e.set_xticks(range(2015, 2025, 3))
    e.set_ylabel("gramos por tonelada cosechada, escala logarítmica")
    ult = int(v.index.max())
    e.annotate(f"{v.loc[ult, 'veces_chile_sobre_noruega']:.0f} veces", xy=(ult - 1.6, 12),
               fontsize=10, color="#333333", ha="center")
    e.annotate("", xy=(ult - 0.9, v.loc[ult, "indice_g_por_t"]),
               xytext=(ult - 0.9, v.loc[ult, "noruega_g_por_t"]),
               arrowprops=dict(arrowstyle="<->", color="#555555", lw=1.0))
    e.set_title("c. Chile y Noruega, 2015-2024", fontsize=10, loc="left")
    e.legend(fontsize=9, frameon=True, framealpha=0.95, edgecolor="none",
             loc="center left")
    fig.suptitle("Uso de antimicrobianos: el «talón de Aquiles» del libro, medido "
                 "diecisiete años después", fontsize=12.5, x=0.06, ha="left", y=1.02)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_J2 antimicrobianos en la salmonicultura", ext),
                    bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 3. Comercio: quién exporta y a qué precio
# ---------------------------------------------------------------------------
def comercio() -> tuple[pd.DataFrame, pd.DataFrame]:
    codigos = {}
    with open(rutas.exigir(D_BACI / "country_codes_V202601.csv", "códigos BACI"),
              encoding="utf-8-sig", errors="replace") as f:
        for r in csv.DictReader(f):
            codigos[r["country_code"]] = r["country_name"]

    por_pais: dict[tuple[int, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    por_partida: dict[tuple[int, str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for anio in (2022, 2023, 2024):
        ruta = rutas.exigir(D_BACI / f"BACI_HS22_Y{anio}_V202601.csv", f"BACI {anio}")
        with open(ruta, encoding="utf-8", errors="replace") as f:
            lector = csv.reader(f)
            next(lector)
            for fila in lector:
                k = fila[3].strip().strip('"').zfill(6)
                if k not in PARTIDAS:
                    continue
                exp = fila[1].strip()
                v = float(fila[4]) if fila[4] not in ("", "NA") else 0.0
                q = float(fila[5]) if fila[5] not in ("", "NA") else 0.0
                por_pais[(anio, exp)][0] += v
                por_pais[(anio, exp)][1] += q
                if exp in (COD_CHILE, COD_NORUEGA):
                    por_partida[(anio, exp, k)][0] += v
                    por_partida[(anio, exp, k)][1] += q

    filas = []
    for anio in (2022, 2023, 2024):
        total = sum(v[0] for (a, _), v in por_pais.items() if a == anio)
        orden = sorted(((c, v) for (a, c), v in por_pais.items() if a == anio),
                       key=lambda x: -x[1][0])
        for puesto, (c, (v, q)) in enumerate(orden[:12], start=1):
            filas.append({
                "anio": anio, "puesto": puesto, "pais": codigos.get(c, c),
                "valor_MUSD": v / 1000, "volumen_kt": q / 1000,
                "valor_unitario_USD_kg": v / q if q else np.nan,
                "pct_del_mundo": 100 * v / total,
            })
    ranking = pd.DataFrame(filas)

    filas = []
    for k, glosa in PARTIDAS.items():
        f = {"partida": k, "producto": glosa}
        for cod, etq in ((COD_CHILE, "Chile"), (COD_NORUEGA, "Noruega")):
            v, q = por_partida[(2024, cod, k)]
            f[f"{etq}: valor MUSD"] = v / 1000
            f[f"{etq}: volumen kt"] = q / 1000
            f[f"{etq}: USD/kg"] = v / q if q else np.nan
        f["Chile / Noruega"] = (f["Chile: USD/kg"] / f["Noruega: USD/kg"]
                                if f["Noruega: USD/kg"] else np.nan)
        filas.append(f)
    partidas = pd.DataFrame(filas)
    tot = {"partida": "", "producto": "Total"}
    for cod, etq in ((COD_CHILE, "Chile"), (COD_NORUEGA, "Noruega")):
        v = sum(por_partida[(2024, cod, k)][0] for k in PARTIDAS)
        q = sum(por_partida[(2024, cod, k)][1] for k in PARTIDAS)
        tot[f"{etq}: valor MUSD"], tot[f"{etq}: volumen kt"] = v / 1000, q / 1000
        tot[f"{etq}: USD/kg"] = v / q
    tot["Chile / Noruega"] = tot["Chile: USD/kg"] / tot["Noruega: USD/kg"]
    partidas = pd.concat([partidas, pd.DataFrame([tot])], ignore_index=True)
    return ranking, partidas


def figura_precios(partidas: pd.DataFrame) -> None:
    d = partidas[partidas["producto"] != "Total"].copy()
    d = d[(d["Chile: volumen kt"] > 1) & (d["Noruega: volumen kt"] > 1)]
    d = d.sort_values("Chile / Noruega")
    y = np.arange(len(d))
    fig, e = plt.subplots(figsize=(9.6, 4.4))
    e.barh(y - 0.19, d["Chile: USD/kg"], height=0.38, color="#c0392b", label="Chile")
    e.barh(y + 0.19, d["Noruega: USD/kg"], height=0.38, color="#1f4e79", label="Noruega")
    for i, (_, f) in enumerate(d.iterrows()):
        e.text(max(f["Chile: USD/kg"], f["Noruega: USD/kg"]) + 0.25, i,
               f"{100 * (f['Chile / Noruega'] - 1):+.0f}%", va="center", fontsize=8,
               color="#333333")
    e.set_yticks(y)
    e.set_yticklabels([g.replace(", ", ",\n") for g in d["producto"]], fontsize=8)
    e.set_xlabel("valor unitario de exportación, USD por kilo, 2024. "
                 "Sólo partidas con más de mil toneladas exportadas por los dos países")
    e.set_title("El salmón chileno se vende por debajo del noruego en el pez fresco "
                "y en el filete,\nque son tres cuartos de lo que Chile exporta",
                fontsize=11, loc="left")
    e.text(0, 1.005, "El libro lo afirma sin fecha ni cifra —«sus precios cotizan por "
           "debajo de los de Noruega»—: acá está medido, partida por partida",
           transform=e.transAxes, fontsize=8.5, color="#555555", va="bottom")
    e.legend(fontsize=9, frameon=True, framealpha=0.95, edgecolor="none",
             loc="lower right", bbox_to_anchor=(0.99, 0.02))
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_J3 valor unitario del salmon chileno y noruego", ext),
                    bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4. Escala, estructura y concentración
# ---------------------------------------------------------------------------
def estructura(prod: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    h = pd.DataFrame(HOLDINGS_2024, columns=["holding", "ciclos", "antimicrobianos_kg",
                                             "biomasa_muerta_t", "cosecha_t"])
    h["pct_cosecha"] = 100 * h["cosecha_t"] / h["cosecha_t"].sum()
    # Sernapesca calcula el índice por holding sobre la biomasa PRODUCIDA —cosechada más
    # muerta—, no sobre la cosechada: reproducirlo así devuelve sus cifras publicadas al
    # segundo decimal. La tabla anual de ese mismo informe, en cambio, divide sólo por la
    # cosecha; por eso el índice agregado de `T_J2` (339 g/t en 2024) y el promedio de esta
    # tabla (302 g/t) no coinciden, y no tienen por qué.
    h["biomasa_producida_t"] = h["cosecha_t"] + h["biomasa_muerta_t"]
    h["indice_g_por_t"] = 1000 * h["antimicrobianos_kg"] / h["biomasa_producida_t"]
    h = h.sort_values("cosecha_t", ascending=False).reset_index(drop=True)
    h["acumulado_pct"] = h["pct_cosecha"].cumsum()

    cr4 = h["pct_cosecha"].head(4).sum()
    cr10 = h["pct_cosecha"].head(10).sum()
    hhi = ((h["pct_cosecha"]) ** 2).sum()

    centros_2024 = float(np.mean(CENTROS_CL[2024]))
    centros_2025 = float(np.mean(CENTROS_CL[2025]))
    bio_2025 = max(BIOMASA_CL[2025]) * 1000
    bio_2024 = max(BIOMASA_CL[2024]) * 1000
    cosecha_cl = dict(zip([a for a, _, _ in ANTIMICROBIANOS_CL],
                          [c for _, _, c in ANTIMICROBIANOS_CL]))

    comp = pd.DataFrame([
        {"indicador": "Producción o cosecha de salmónidos (t)",
         "Chile, 2007": cosecha_cl[2007], "Chile, último año": cosecha_cl[2024],
         "Noruega, 2024": NORUEGA_2024["cosecha"]},
        {"indicador": "Centros de cultivo en el mar",
         "Chile, 2007": np.nan, "Chile, último año": max(CENTROS_CL[2025]),
         "Noruega, 2024": NORUEGA_2024["centros_mar"]},
        {"indicador": "Biomasa máxima en cultivo por centro (t)",
         "Chile, 2007": BIOMASA_CENTRO_2007["Chile"],
         "Chile, último año": bio_2025 / max(CENTROS_CL[2025]),
         "Noruega, 2024": np.nan},
        {"indicador": "Cosecha anual por centro activo promedio (t)",
         "Chile, 2007": np.nan,
         "Chile, último año": cosecha_cl[2024] / centros_2024,
         "Noruega, 2024": NORUEGA_2024["cosecha"] / NORUEGA_2024["centros_mar"]},
        {"indicador": "Empresas o holdings productores",
         "Chile, 2007": np.nan, "Chile, último año": len(HOLDINGS_2024),
         "Noruega, 2024": NORUEGA_2024["empresas_engorda"]},
        {"indicador": "Cuota de las 4 mayores en la cosecha (%)",
         "Chile, 2007": np.nan, "Chile, último año": cr4, "Noruega, 2024": np.nan},
        {"indicador": "Cuota de las 10 mayores en la cosecha (%)",
         "Chile, 2007": np.nan, "Chile, último año": cr10,
         "Noruega, 2024": CR10_NORUEGA[2024]},
        {"indicador": "Índice de Herfindahl de la cosecha (0-10.000)",
         "Chile, 2007": np.nan, "Chile, último año": hhi, "Noruega, 2024": np.nan},
        {"indicador": "Antimicrobianos, gramos por tonelada cosechada",
         "Chile, 2007": 1_000_000 * 385.6 / cosecha_cl[2007],
         "Chile, último año": 1_000_000 * 351.1 / cosecha_cl[2024],
         "Noruega, 2024": 1000 * ANTIBIOTICOS_NO[2024] / NORUEGA_2024["cosecha"]},
        {"indicador": "Mortalidad del salmón del Atlántico (%)",
         "Chile, 2007": np.nan,
         "Chile, último año": MORTALIDAD_CL[2025]["Salmón del Atlántico"],
         "Noruega, 2024": MORTALIDAD_NO_2024["Salmón del Atlántico"]},
    ])
    _ = centros_2025, bio_2024
    return h, comp


def figura_concentracion(h: pd.DataFrame) -> None:
    fig, ejes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    e = ejes[0]
    y = np.arange(len(h))[::-1]
    e.barh(y, h["pct_cosecha"], color="#4a6fa5")
    e.set_yticks(y)
    e.set_yticklabels(h["holding"], fontsize=7.5)
    e.set_xlabel("% de la cosecha de ciclos cerrados, 2024")
    e.set_title("a. Dieciocho holdings, y uno con un cuarto del total", fontsize=10,
                loc="left")

    e = ejes[1]
    orden = h.sort_values("indice_g_por_t")
    y = np.arange(len(orden))[::-1]
    e.barh(y, orden["indice_g_por_t"], color="#c0392b")
    e.set_yticks(y)
    e.set_yticklabels(orden["holding"], fontsize=7.5)
    e.set_xlabel("gramos de antimicrobiano por tonelada producida, 2024\n"
                 "(cosechada más muerta: es el denominador con que lo publica Sernapesca)")
    e.axvline(302.33, color="#333333", ls="--", lw=1.0)
    e.text(312, len(orden) - 1.4, "media de la industria\n302 g/t", fontsize=8,
           color="#333333")
    e.set_title("b. Dos órdenes de magnitud entre empresas de la misma rama",
                fontsize=10, loc="left")
    fig.suptitle("Concentración y heterogeneidad dentro de la salmonicultura chilena",
                 fontsize=12.5, x=0.06, ha="left", y=1.03)
    fig.text(0.06, 0.985, "El libro cuenta 219 empresas en 1997 y «las 5 más grandes con "
             "más del 50% de las concesiones»; no tiene gráfica de esto, y su última cifra "
             "de concentración es de alrededor de 2009",
             fontsize=8.5, color="#555555", ha="left", va="top")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_J4 concentracion y heterogeneidad intra-rama", ext),
                    bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 5. La capacidad regulatoria: presupuesto y dotación de Sernapesca
# ---------------------------------------------------------------------------
def sernapesca(prod: pd.DataFrame) -> pd.DataFrame:
    ipc = pd.read_csv(rutas.exigir(D_IPC, "IPC del Banco Mundial")).set_index("anio")
    base = ipc.loc[2025, "ipc_2010_100"]
    anios = sorted(set(PRESUP_SERNAPESCA) | set(PRESUP_DIPRES) | set(DOTACION_SERNAPESCA))
    d = pd.DataFrame(index=pd.Index(anios, name="anio"))
    d["katz_nominal_MM"] = pd.Series(PRESUP_SERNAPESCA)
    d["ley_inicial_MM"] = pd.Series(PRESUP_DIPRES)
    d["vigente_decretos_MM"] = pd.Series(VIGENTE_DECRETOS)
    d["vigente_4T_MM"] = pd.Series(PRESUP_VIGENTE)
    d["devengado_MM"] = pd.Series(PRESUP_DEVENGADO)
    # La serie continua en el concepto del libro: sus propias cifras hasta 2016 y el
    # vigente oficial del cuarto trimestre desde 2017. No hay empalme que justificar
    # porque es la misma magnitud; la verificación está en VIGENTE_DECRETOS.
    d["vigente_MM"] = d["katz_nominal_MM"].where(d.index <= 2016, d["vigente_4T_MM"])
    d["ipc_2010_100"] = ipc["ipc_2010_100"]
    for col in ("katz", "ley_inicial", "vigente"):
        base_col = f"{col}_nominal_MM" if col == "katz" else f"{col}_MM"
        d[f"{col}_real_MM_2025"] = d[base_col] * base / d["ipc_2010_100"]
    d["razon_katz_sobre_ley"] = d["katz_nominal_MM"] / d["ley_inicial_MM"]
    d["dotacion_efectiva"] = pd.Series(DOTACION_SERNAPESCA)
    d["dotacion_maxima_ley"] = pd.Series(DOTACION_MAXIMA)
    cosecha = {a: c for a, _, c in ANTIMICROBIANOS_CL}
    d["cosecha_salmonidos_t"] = pd.Series(cosecha)
    d["presupuesto_real_por_t_cosechada"] = (
        1_000_000 * d["vigente_real_MM_2025"] / d["cosecha_salmonidos_t"])
    return d


def figura_sernapesca(d: pd.DataFrame) -> None:
    """Dos filas: arriba el presupuesto, abajo la dotación; a la izquierda el original.

    Las dos gráficas del libro son gráficos nativos de Word, o sea no hay recorte que
    pegar: la columna «original» las reproduce con las series que se leyeron del XML del
    propio archivo, en pesos corrientes y con el mismo alcance temporal que tienen allá.
    """
    corte_p, corte_d = 2016, 2016
    fig, ejes = plt.subplots(2, 2, figsize=(13.6, 8.4),
                             gridspec_kw={"width_ratios": [1.0, 1.35]})

    # --- fila 1: presupuesto ---
    e = ejes[0, 0]
    k = d["katz_nominal_MM"].dropna()
    e.plot(k.index, k, color="#1f4e79", lw=2.0)
    e.set_ylabel("millones de pesos corrientes")
    e.set_title(f"a. La gráfica del libro: «Evolución presupuesto Sernapesca\n"
                f"    (millones de pesos corrientes)», 1981-{corte_p}", fontsize=10,
                loc="left")

    e = ejes[0, 1]
    v = d["vigente_real_MM_2025"].dropna()
    e.plot(v.index, v, color="#1f4e79", lw=2.2, label="presupuesto vigente")
    post = v[v.index >= corte_p]
    e.plot(post.index, post, color="#c0392b", lw=2.4, marker="o", ms=3.5,
           label="lo que agrega esta actualización")
    ley = d["ley_inicial_real_MM_2025"].dropna()
    e.plot(ley.index, ley, color="#7f8c8d", lw=1.3, ls=":", label="ley inicial")
    e.axvspan(1981, corte_p, color="#000000", alpha=0.05)
    marcar_corte(e, corte_p, "hasta acá\nllega el original", y=0.45)
    ult = int(v.index.max())
    caida = 100 * (v.loc[ult] / v.loc[corte_p] - 1)
    e.text(1982, 57_500, f"En el mismo concepto que usa el libro, el presupuesto real\n"
                         f"cayó {abs(caida):.1f}% entre {corte_p} y {ult}, con la cosecha "
                         f"42% más alta", fontsize=9, color="#c0392b", va="top")
    e.set_ylabel("millones de pesos de 2025")
    e.set_title("b. La misma serie, extendida y en moneda constante", fontsize=10,
                loc="left")
    e.legend(fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(0.0, 0.80))

    # --- fila 2: dotación ---
    e = ejes[1, 0]
    v = d["dotacion_efectiva"].dropna()
    e.plot(v.index, v, color="#1f4e79", lw=2.0, marker="o", ms=3.5)
    e.set_ylabel("personas")
    e.set_title(f"c. La gráfica del libro: «Dotación efectiva Sernapesca»,\n"
                f"    2002-{corte_d}", fontsize=10, loc="left")

    e = ejes[1, 1]
    e.plot(v.index, v, color="#1f4e79", lw=2.2, marker="o", ms=3.5,
           label="dotación efectiva (serie del libro)")
    m = d["dotacion_maxima_ley"].dropna()
    e.plot(m.index, m, color="#c0392b", lw=2.2, marker="s", ms=3.5,
           label="dotación máxima de la Ley de Presupuestos")
    e.axvspan(2002, corte_d, color="#000000", alpha=0.05)
    marcar_corte(e, corte_d, "hasta acá\nllega el original", y=0.40)
    e.axvline(2008, color="#b0b0b0", ls=":", lw=1.0)
    e.text(2008.3, 330, "crisis del ISA", fontsize=8, color="#888888")
    e.set_ylabel("personas")
    e.set_title("d. La misma serie, con la dotación autorizada por la ley", fontsize=10,
                loc="left")
    e.legend(fontsize=8, frameon=False, loc="upper left")

    fig.suptitle("La capacidad del regulador: las dos gráficas del libro, y lo que pasó "
                 "después de 2016", fontsize=12.5, x=0.06, ha="left", y=1.0)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_J5 presupuesto y dotacion de Sernapesca", ext),
                    bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 6. La frontera de explotación: el reparto regional
# ---------------------------------------------------------------------------
def figura_regiones() -> pd.DataFrame:
    corte = ORIGINALES["region"][1]
    filas = []
    for anio, reg in COSECHA_REGION_LIBRO.items():
        tot = sum(reg.values())
        for r, v in reg.items():
            filas.append({"anio": anio, "region": r, "toneladas": v,
                          "pct": 100 * v / tot, "fuente": "leído de la gráfica del libro"})
    tot = sum(COSECHA_REGION_2024.values())
    for r, v in COSECHA_REGION_2024.items():
        filas.append({"anio": 2024, "region": r, "toneladas": v, "pct": 100 * v / tot,
                      "fuente": "Sernapesca, ciclos cerrados 2024"})
    d = pd.DataFrame(filas)

    fig, ejes = plt.subplots(1, 2, figsize=(13.4, 4.6),
                             gridspec_kw={"width_ratios": [1.15, 1.0]})
    poner_original(ejes[0], "region",
                   f"a. La gráfica del libro: «Expansión de la frontera de explotación\n"
                   f"    acuícola hacia Aysén», 2006-{corte}")
    e = ejes[1]
    regiones = ["Los Lagos", "Aysén", "Magallanes"]
    colores = {"Los Lagos": "#4a6fa5", "Aysén": "#c0392b", "Magallanes": "#117a65"}
    anios = [2006, corte, 2024]
    x = np.arange(len(anios))
    abajo = np.zeros(len(anios))
    for r in regiones:
        alt = [d[(d.anio == a) & (d.region == r)]["pct"].iloc[0] for a in anios]
        e.bar(x, alt, bottom=abajo, color=colores[r], width=0.55, label=r)
        for i, (v, b) in enumerate(zip(alt, abajo)):
            if v > 3:
                e.text(x[i], b + v / 2, f"{v:.0f}%", ha="center", va="center",
                       fontsize=9, color="white")
        abajo = abajo + np.array(alt)
    e.set_xticks(x)
    e.set_xticklabels([f"{a}\n{'(gráfica del libro)' if a <= corte else '(Sernapesca)'}"
                       for a in anios], fontsize=9)
    e.set_ylabel("% de la producción de salmónidos")
    e.set_ylim(0, 108)
    e.set_title("b. El mismo reparto, con el dato más reciente", fontsize=10, loc="left")
    e.legend(fontsize=9, frameon=False, ncol=3, loc="upper center")
    e.grid(axis="x", visible=False)
    fig.suptitle("La frontera siguió moviéndose al sur: Magallanes pasó de casi nada a "
                 "un décimo de la cosecha", fontsize=12.5, x=0.06, ha="left", y=1.01)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_J6 frontera de explotacion por region", ext),
                    bbox_inches="tight")
    plt.close(fig)
    return d


def figura_pendientes() -> None:
    """Las dos gráficas del libro que este bloque todavía no puede actualizar.

    Van al output igual: tenerlas a mano en la carpeta de figuras es lo que hace visible
    qué queda por hacer, y con qué fuente habría que hacerlo.
    """
    fig, ejes = plt.subplots(1, 2, figsize=(14.0, 4.6))
    poner_original(ejes[0], "ovas",
                   "a. «Importación y producción local de ovas de salmón», 1984-2008\n"
                   "    Pendiente: Aduanas por partida arancelaria, cruzado con Sernapesca")
    poner_original(ejes[1], "permisos",
                   "b. «Nuevos permisos de cultivo por regiones del sur de Chile», "
                   "1982-2011\n    Pendiente: registro de concesiones de acuicultura de "
                   "Subpesca")
    fig.suptitle("Las dos gráficas del libro que quedan por actualizar", fontsize=12.5,
                 x=0.06, ha="left", y=1.02)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(rutas.figura("F_J7 graficas del libro pendientes de actualizar", ext),
                    bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
def main() -> None:
    rutas.preparar_directorios()

    prod = produccion()
    prod.to_excel(rutas.tabla("T_J1 produccion de salmonidos de cultivo"))
    figura_catchup(prod)
    print(f"T_J1  producción {prod.index.min()}-{prod.index.max()}; "
          f"Chile/Noruega {prod['Chile / Noruega'].iloc[-1]:.2f} en {prod.index.max()}")

    atb = antimicrobianos(prod)
    atb.to_excel(rutas.tabla("T_J2 antimicrobianos en la salmonicultura"))
    figura_antimicrobianos(atb)
    print(f"T_J2  Chile {atb.loc[2024, 'indice_g_por_t']:.0f} g/t contra "
          f"{atb.loc[2024, 'noruega_g_por_t']:.2f} g/t de Noruega en 2024: "
          f"{atb.loc[2024, 'veces_chile_sobre_noruega']:.0f} veces")

    ranking, partidas = comercio()
    ranking.to_excel(rutas.tabla("T_J3 exportadores mundiales de salmonidos"), index=False)
    partidas.to_excel(rutas.tabla("T_J4 valor unitario por partida Chile y Noruega"),
                      index=False)
    figura_precios(partidas)
    ch = ranking[(ranking["anio"] == 2024) & (ranking["pais"] == "Chile")].iloc[0]
    print(f"T_J3  Chile es el exportador n.° {int(ch['puesto'])} en 2024, "
          f"{ch['pct_del_mundo']:.1f}% del comercio mundial")
    print(f"T_J4  valor unitario total Chile/Noruega: "
          f"{partidas.iloc[-1]['Chile / Noruega']:.3f}")

    holdings, comp = estructura(prod)
    holdings.to_excel(rutas.tabla("T_J5 cosecha y antimicrobianos por holding"), index=False)
    comp.to_excel(rutas.tabla("T_J6 escala y estructura Chile y Noruega"), index=False)
    figura_concentracion(holdings)
    print(f"T_J5  CR4 {holdings['pct_cosecha'].head(4).sum():.1f}%, "
          f"CR10 {holdings['pct_cosecha'].head(10).sum():.1f}%; "
          f"índice de consumo entre {holdings['indice_g_por_t'].min():.0f} y "
          f"{holdings['indice_g_por_t'].max():.0f} g/t")

    mort = pd.DataFrame(MORTALIDAD_CL).T
    mort.index.name = "anio"
    mort.loc["Noruega 2024"] = pd.Series(MORTALIDAD_NO_2024)
    mort.to_excel(rutas.tabla("T_J7 mortalidad por ciclo cerrado"))

    sp = sernapesca(prod)
    sp.to_excel(rutas.tabla("T_J8 presupuesto y dotacion de Sernapesca"))
    figura_sernapesca(sp)
    razon = sp["razon_katz_sobre_ley"].dropna()
    err = (sp["vigente_decretos_MM"] / sp["katz_nominal_MM"] - 1).dropna().abs()
    print(f"T_J8  la serie del libro está {100 * razon.mean() - 100:.1f}% sobre la ley "
          f"inicial en promedio ({100 * razon.min() - 100:.1f} a "
          f"{100 * razon.max() - 100:.1f}%); reconstruida como vigente, el error máximo "
          f"contra el libro es {100 * err.max():.2f}%")
    real = sp["vigente_real_MM_2025"].dropna()
    por_t = sp["presupuesto_real_por_t_cosechada"]
    ult = int(real.index.max())
    print(f"      presupuesto vigente real 2016 {real[2016]:,.0f} MM contra {ult} "
          f"{real[ult]:,.0f} MM de 2025: {100 * (real[ult] / real[2016] - 1):+.1f}%; "
          f"por tonelada cosechada, de {por_t[2016]:,.0f} a {por_t[2024]:,.0f} pesos "
          f"({100 * (por_t[2024] / por_t[2016] - 1):+.1f}%)")

    reg = figura_regiones()
    reg.to_excel(rutas.tabla("T_J9 cosecha de salmonidos por region"), index=False)
    m = reg[(reg.anio == 2024) & (reg.region == "Magallanes")]["pct"].iloc[0]
    print(f"T_J9  Magallanes pasa de 1,0% de la cosecha en 2006 a {m:.1f}% en 2024")

    figura_pendientes()


if __name__ == "__main__":
    main()
