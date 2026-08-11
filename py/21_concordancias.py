"""Las tres concordancias que hacen falta para agregar variables al ejercicio de la UAM.

FUENTES. COU y MIP del Banco Central bajados el 2026-08-11 a
`<almacen>/Banco Central de Chile/2026.08.11 COU y MIP`; planillas de la UAM en
`$RAW/UAM_Dutrenit`; Estadísticas de Empresas del SII (`PUB_TRAM_ACT.csv`).

QUÉ PRODUCE.

  1. `codigo_3dig` de la UAM ↔ actividad de la COU. Se VERIFICA, no se construye: la
     hipótesis es que son el mismo código. Si las glosas no calzan una a una, aborta.

  2. `config/clasificacion_productos_cou.csv` — qué productos de la COU son energéticos
     y cuáles son TIC, en las dos nomenclaturas (181 productos en 2023, 73 en 2003).
     Se genera con una lista explícita, no con búsqueda de texto, y queda versionada
     para que se corrija a mano.

  3. La concordancia CIIU4.CL → actividad de la COU, resuelta desde
     `config/reglas_ciiu_a_cou.csv` por prefijo más largo, con informe de cobertura.

ADVERTENCIA SOBRE 2003. La nomenclatura de 73 productos no tiene ningún producto de
servicios informáticos: lo más cercano es «Servicios de comunicaciones», que en 2023 se
abre en telefonía móvil, fija, otras telecomunicaciones y servicios informáticos. La
digitalización de 2003 y la de 2023 NO son la misma variable y no deben compararse en
el tiempo. Dentro de cada año sí son válidas, que es lo que el agrupamiento necesita,
porque la estandarización es dentro del año.
"""

from __future__ import annotations

import sys

import pandas as pd

import rutas

# --- Productos energéticos y TIC, por nomenclatura --------------------------
# La lista es explícita a propósito. Un filtro por palabras clave metería
# «Transporte por tuberías» y «Obras de proyectos de energía eléctrica» entre los
# energéticos, y ninguno de los dos es un insumo de energía.
PRODUCTOS = {
    2: {  # COU 2018, 181 productos (período 2, año 2023)
        "energia": {
            27: "Carbón",
            28: "Petróleo crudo",
            29: "Gas natural",
            77: "Diésel",
            78: "Gasolinas",
            79: "Kerosene",
            80: "Aceites combustibles",
            81: "Gas licuado y otros combustibles",
            119: "Energía y potencia eléctrica",
            120: "Servicios de transmisión de electricidad",
            121: "Servicios de distribución de electricidad",
            122: "Gas distribuido por ductos",
        },
        # Núcleo TIC, en la definición de Calvino et al. (2018): compras
        # intermedias de bienes y servicios de tecnologías de la información.
        "tic": {
            104: "Computadores y sus componentes",
            107: "Teléfonos móviles",
            152: "Servicios de telefonía móvil",
            153: "Servicios de telefonía fija y de larga distancia",
            154: "Otros servicios de telefonía",
            155: "Servicios informáticos",
        },
        # Definición amplia: suma electrónica de consumo y maquinaria de oficina.
        # Se reporta como sensibilidad, no como variable principal.
        "tic_amplio": {
            105: "Otras maquinarias de oficina",
            106: "Televisores",
        },
    },
    1: {  # COU 2003, 73 productos (período 1, año 2003)
        "energia": {
            6: "Carbón",
            7: "Petróleo crudo",
            33: "Combustible y otros productos del petróleo",
            48: "Electricidad",
            49: "Gas",
        },
        "tic": {
            61: "Servicios de comunicaciones",
        },
        "tic_amplio": {
            44: "Maquinaria y equipo eléctrico",
        },
    },
}

# Hojas del COU con la matriz de utilización intermedia total a precios básicos.
HOJA_UTILIZACION = {1: "6.28", 2: "17"}

ARCHIVO_COU = {1: "2003_Cuadros_73x73.xls", 2: "2023_Cuadros_111x181.xlsx"}
ARCHIVO_MIP = {1: "2003_MIP_73x73.xls", 2: "2023_MIP_111x111.xlsx"}


def glosa_cou(periodo: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Listas de actividades y de productos de la COU, desde la hoja `Glosa`."""
    ruta = rutas.exigir(
        rutas.D_BCCH / "2026.08.11 COU y MIP" / ARCHIVO_COU[periodo],
        f"el COU del período {periodo}",
    )
    g = pd.read_excel(ruta, sheet_name="Glosa", header=None)
    act = g.iloc[9:, [1, 2]].dropna()
    act.columns = ["cod", "desc"]
    prod = g.iloc[9:, [4, 5]].dropna()
    prod.columns = ["cod", "desc"]
    for t in (act, prod):
        t["cod"] = t["cod"].astype(int)
        t["desc"] = t["desc"].astype(str).str.strip()
    return act.reset_index(drop=True), prod.reset_index(drop=True)


def verificar_identidad_uam(periodo: int, act: pd.DataFrame) -> list[str]:
    """El `codigo_3dig` de la UAM debería ser el código de actividad del Banco Central."""
    insumo = pd.read_excel(rutas.D_UAM_INSUMO)
    u = insumo[insumo["periodo"] == periodo][["codigo_3dig", "desc"]]
    m = u.merge(act, left_on="codigo_3dig", right_on="cod", how="left",
                suffixes=("_uam", "_bcch"))
    m["calza"] = m.apply(
        lambda r: rutas.normalizar(r["desc_uam"]) == rutas.normalizar(r["desc_bcch"])
        if pd.notna(r["desc_bcch"]) else False,
        axis=1,
    )
    return [
        f"    código {int(r.codigo_3dig)}: UAM «{r.desc_uam}» vs BCCh «{r.desc_bcch}»"
        for r in m[~m["calza"]].itertuples()
    ]


def escribir_clasificacion_productos(glosas: dict[int, pd.DataFrame]) -> Path_like:
    filas = []
    for periodo, grupos in PRODUCTOS.items():
        catalogo = glosas[periodo].set_index("cod")["desc"].to_dict()
        for grupo, items in grupos.items():
            for cod, etiqueta in items.items():
                oficial = catalogo.get(cod, "")
                filas.append({
                    "periodo": periodo,
                    "anio": 2003 if periodo == 1 else 2023,
                    "cod_producto": cod,
                    "grupo": grupo,
                    "desc_esperada": etiqueta,
                    "desc_cou": oficial,
                    "calza": rutas.normalizar(etiqueta) == rutas.normalizar(oficial),
                })
    d = pd.DataFrame(filas)
    destino = rutas.CONFIG / "clasificacion_productos_cou.csv"
    d.to_csv(destino, index=False, encoding="utf-8")
    return d, destino


Path_like = object  # sólo para la anotación de arriba; el repo no usa typing estricto


def resolver_reglas_ciiu() -> pd.DataFrame:
    """Lee las reglas y las resuelve contra las actividades del SII. Prefijo más largo gana."""
    ruta = rutas.exigir(rutas.CONFIG / "reglas_ciiu_a_cou.csv", "las reglas CIIU → COU")
    reglas = pd.read_csv(ruta, comment="#", dtype={"prefijo": str})
    reglas = reglas.dropna(subset=["prefijo"])
    reglas["cou"] = reglas["cou"].astype(int)
    mapa = dict(zip(reglas["prefijo"], reglas["cou"]))
    notas = dict(zip(reglas["prefijo"], reglas["nota"]))

    sii = pd.read_csv(rutas.exigir(rutas.D_SII_ACT, "el archivo de actividades del SII"),
                      encoding="utf-8", low_memory=False)
    sii = sii[sii["actividad"].notna()]
    sii = sii[sii["actividad"].str[:1].str.isdigit()].copy()
    sii["ciiu"] = sii["actividad"].str[:6]

    codigos = sii[["ciiu", "actividad"]].drop_duplicates().sort_values("ciiu")

    def resolver(c: str):
        for n in range(len(c), 0, -1):
            if c[:n] in mapa:
                return mapa[c[:n]], c[:n], notas[c[:n]]
        return None, None, None

    res = codigos["ciiu"].map(resolver)
    codigos["cou"] = [r[0] for r in res]
    codigos["prefijo"] = [r[1] for r in res]
    codigos["nota"] = [r[2] for r in res]
    return codigos, sii


def main() -> int:
    rutas.preparar_directorios()
    fallas = []
    glosas_prod = {}

    print("=== 1. El código de la UAM contra el código del Banco Central ===")
    for periodo in (1, 2):
        act, prod = glosa_cou(periodo)
        glosas_prod[periodo] = prod
        discrepancias = verificar_identidad_uam(periodo, act)
        anio = 2003 if periodo == 1 else 2023
        if discrepancias:
            print(f"  {anio}: {len(discrepancias)} actividades no calzan")
            for d in discrepancias[:10]:
                print(d)
            fallas.append(f"las glosas del período {periodo} no calzan una a una")
        else:
            print(f"  {anio}: las {len(act)} glosas calzan una a una. "
                  "El `codigo_3dig` ES el código de actividad del Banco Central.")

    print("\n=== 2. Clasificación de productos: energía y TIC ===")
    clas, destino = escribir_clasificacion_productos(glosas_prod)
    for periodo in (1, 2):
        sub = clas[clas["periodo"] == periodo]
        anio = 2003 if periodo == 1 else 2023
        n = sub.groupby("grupo").size().to_dict()
        print(f"  {anio}: " + ", ".join(f"{k} = {v}" for k, v in sorted(n.items())))
        malas = sub[~sub["calza"]]
        if len(malas):
            for r in malas.itertuples():
                print(f"    código {r.cod_producto}: esperada «{r.desc_esperada}» "
                      f"vs COU «{r.desc_cou}»")
            fallas.append(f"la clasificación de productos del período {periodo} "
                          "no calza con la glosa de la COU")
    print(f"  guardada en {destino.name}")

    print("\n=== 3. CIIU4.CL → actividad de la COU ===")
    codigos, sii = resolver_reglas_ciiu()
    sin = codigos[codigos["cou"].isna()]
    print(f"  actividades del SII (6 dígitos)      : {len(codigos)}")
    print(f"  resueltas                            : {len(codigos) - len(sin)}")
    if len(sin):
        print(f"  SIN REGLA ({len(sin)}):")
        for r in sin.itertuples():
            print(f"    {r.actividad}")
        fallas.append("hay actividades del SII sin regla en reglas_ciiu_a_cou.csv")

    ok = codigos.dropna(subset=["cou"]).copy()
    ok["cou"] = ok["cou"].astype(int)
    cubiertas = sorted(ok["cou"].unique())
    print(f"  actividades de la COU con contraparte: {len(cubiertas)} de 111")
    faltan = [c for c in range(1, 112) if c not in cubiertas]
    if faltan:
        act23, _ = glosa_cou(2)
        nombres = act23.set_index("cod")["desc"].to_dict()
        print("  actividades de la COU SIN empresas en el registro del SII:")
        for c in faltan:
            print(f"    {c:3d}  {nombres.get(c, '?')}")

    destino_c = rutas.CONFIG / "concordancia_cou_ciiu4cl.csv"
    ok[["ciiu", "actividad", "cou", "prefijo", "nota"]].to_csv(
        destino_c, index=False, encoding="utf-8")
    print(f"  guardada en {destino_c.name}")

    # Peso de las asignaciones apoyadas en prefijos cortos: son las que más conviene
    # revisar a mano, porque una regla de dos dígitos cubre una división entera.
    sii23 = sii[sii["anio"] == 2023].merge(ok[["ciiu", "cou", "prefijo"]], on="ciiu")
    sii23["largo"] = sii23["prefijo"].str.len()
    peso = (sii23.groupby("largo")["ntrabajadores"].sum() / sii23["ntrabajadores"].sum())
    print("  trabajadores asignados según el largo del prefijo que resolvió la regla:")
    for largo, p in peso.items():
        print(f"    {largo} dígitos: {p:6.1%}")

    if fallas:
        print("\nHay problemas de concordancia. Corregir antes de construir variables:",
              file=sys.stderr)
        for f in fallas:
            print(f"  · {f}", file=sys.stderr)
        return 459

    print("\nLas tres concordancias están resueltas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
