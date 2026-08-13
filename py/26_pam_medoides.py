"""PAM / k-medoides: el arreglo ortodoxo contra los valores extremos.

LA PREGUNTA. El agrupamiento de la UAM es Ward sobre distancia euclidiana. Las
dos propiedades que lo hacen fragil frente al cobre son conocidas: la distancia
crece con el CUADRADO del puntaje z, asi que una sola variable extrema domina; y
el centroide de un grupo es una media, asi que una observacion atipica lo
arrastra. La respuesta de este proyecto fue logaritmar y ponderar. La respuesta
ortodoxa de la literatura es otra, y es la que se prueba aca:

    PAM (Partitioning Around Medoids) con distancia de Manhattan.

Cambia las dos piezas a la vez. El centro de un grupo deja de ser una media y
pasa a ser una observacion real —el medoide, que es el analogo multivariado de
la mediana—, y la distancia deja de elevar al cuadrado. Ademas PAM optimiza un
criterio global con reasignacion: a diferencia de Ward, que es aglomerativo y
nunca revisa una fusion, la fase SWAP puede sacar de un grupo a una actividad
que quedo mal colocada en un paso temprano.

QUE SE COMPARA. Tres cosas distintas, que conviene no mezclar:

  1. EL ALGORITMO SOLO. PAM euclidiano contra Ward, con las mismas variables y
     la misma estandarizacion. Aisla el efecto de reasignar y de usar medoides.
  2. LA METRICA. PAM Manhattan contra PAM euclidiano. Aisla el efecto de no
     elevar al cuadrado.
  3. LAS DOS ESTRATEGIAS DE ROBUSTEZ, UNA CONTRA OTRA. La de este proyecto
     (logaritmos + ponderacion por empleo + balanza normalizada, sobre Ward)
     contra la ortodoxa (PAM + Manhattan + ponderacion). Si convergen, la
     especificacion preferida deja de depender de la familia de metodos, que es
     el argumento que un referi va a pedir.

Y de paso resuelve dos pendientes registrados en MEMORY.md:

  - EL CRITERIO PARA k. PAM viene con la silueta de Kaufman y Rousseeuw, que es
     su companera natural y se calcula sobre la matriz de distancias, sin
     suponer centroides. Se reporta para k = 2..7, ponderada por empleo y sin
     ponderar.
  - LA EXCLUSION DE SECTORES. Todas las especificaciones se corren dos veces:
     sobre las actividades clasificadas por la UAM y sobre la COU COMPLETA, con
     el cobre adentro. Se reporta donde cae el cobre y cuantos conglomerados se
     degeneran (menos del 1 % del empleo).

METRICA DE CALIDAD SUSTANTIVA. Ademas de la silueta —que mide separacion en el
espacio de las siete variables— se reporta el eta cuadrado: que fraccion de la
varianza del logaritmo de la productividad, entre actividades y ponderada por
empleo, queda ENTRE conglomerados. Es la misma medida con la que se contrastan
las particiones rivales del capitulo (hclust de la UAM, complejos productivos,
los cuatro Chiles de la lamina 25 del CINVE), asi que hace comparables cosas que
la silueta no compara.

DEPENDE DE. `20_replica_hclust.py` (escribe `intermediate/uam_replica_p*.csv`) y
de `40_uam_metodo.py`, que aporta la construccion de variables, la
estandarizacion ponderada y el Ward con masas.

SALIDAS. T_I13 (comparacion de especificaciones), T_I14 y T_I15 (membresias de
2023 y 2003) y F_I5 en `$OUT`.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage

_spec = importlib.util.spec_from_file_location(
    "uam_metodo", Path(__file__).with_name("40_uam_metodo.py"))
uam = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uam)

import rutas  # noqa: E402  (el modulo del metodo se carga por ruta: empieza con digito)

# rutas.FECHA marca el lote del bloque I original (2026.08.11). Esta corrida es
# su propio lote, para no renombrar las tablas ya escritas.
HOY = date.today().strftime("%Y.%m.%d")

VARS = uam.VARS_UAM
SUMABLES = ["valor_agrega", "vbp", "remunera", "empleo", "fbcf", "expo", "impo"]
ANIO = {1: 2003, 2: 2023}
KS = (2, 3, 4, 5, 6, 7)
K_DETALLE = 4

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Calibri", "DejaVu Sans"],
    "figure.dpi": 130,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def asegurar_fuente(tamanos: tuple[float, ...]) -> None:
    """Comprueba que la fuente elegida DIBUJE a cada tamano, y si no, la cambia.

    En el PC de escritorio, el Calibri de `C:\\Windows\\Fonts\\calibri.ttf` no
    dibuja NADA a 6,5 · 7 · 8,5 · 9 · 9,5 · 10,5 puntos con dpi 130: el texto se
    compone —ocupa su lugar, la leyenda reserva el ancho— pero sale en blanco. A
    6 · 7,5 · 8 · 10 · 11 · 12 dibuja bien. El fallo es silencioso: matplotlib no
    avisa, la figura se escribe y el texto simplemente no esta.

    Como es un problema de la instalacion de la fuente y no del codigo, puede
    aparecer en una PC y no en otra. En vez de memorizar los tamanos que hoy
    funcionan, se prueba cada uno de los que la figura va a usar y, si alguno
    falla, se cae a DejaVu Sans para TODA la figura —tipografia despareja seria
    peor que un cambio de fuente—.
    """
    prueba = "Ward euclidiano y PAM Manhattan 0123456789"
    malos = []
    for fs in tamanos:
        fig = plt.figure(figsize=(6, 1))
        fig.text(0.02, 0.5, prueba, fontsize=fs)
        lienzo = fig.canvas
        lienzo.draw()
        tinta = int((np.asarray(lienzo.buffer_rgba())[:, :, :3].min(axis=2) < 200).sum())
        plt.close(fig)
        if tinta < 50:
            malos.append(fs)
    if malos:
        actual = plt.rcParams["font.sans-serif"][0]
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
        print(f"AVISO: {actual} no dibuja a los tamanos {malos} en esta maquina; "
              f"la figura se compone con DejaVu Sans.")


# ---------------------------------------------------------------------------
# Distancias
# ---------------------------------------------------------------------------
def matriz_distancias(z: np.ndarray, metrica: str) -> np.ndarray:
    """Matriz completa de distancias entre observaciones estandarizadas."""
    dif = z[:, None, :] - z[None, :, :]
    if metrica == "euclid":
        return np.sqrt((dif ** 2).sum(axis=2))
    if metrica == "manhattan":
        return np.abs(dif).sum(axis=2)
    raise ValueError(f"metrica desconocida: {metrica}")


# ---------------------------------------------------------------------------
# PAM: Partitioning Around Medoids (Kaufman y Rousseeuw)
# ---------------------------------------------------------------------------
def _coste(D: np.ndarray, med: list[int], w: np.ndarray) -> float:
    """Suma ponderada de distancias de cada observacion a su medoide."""
    return float((w * D[med, :].min(axis=0)).sum())


def _build(D: np.ndarray, k: int, w: np.ndarray) -> list[int]:
    """Fase BUILD: el primer medoide es el que minimiza el coste total si fuera
    unico; cada siguiente es el que mas lo reduce dados los ya elegidos."""
    n = D.shape[0]
    med = [int(np.argmin((w[:, None] * D).sum(axis=0)))]
    dmin = D[med[0]].copy()
    while len(med) < k:
        coste_si = np.array([np.inf if j in med else (w * np.minimum(dmin, D[j])).sum()
                             for j in range(n)])
        med.append(int(np.argmin(coste_si)))
        dmin = np.minimum(dmin, D[med[-1]])
    return med


def _swap(D: np.ndarray, med: list[int], w: np.ndarray) -> tuple[list[int], float]:
    """Fase SWAP: prueba cada intercambio medoide <-> no medoide y acepta el mejor
    mientras siga bajando el coste. Es la reasignacion que Ward no puede hacer."""
    n, k = D.shape[0], len(med)
    med = list(med)
    actual = _coste(D, med, w)
    while True:
        mejor_coste, mejor_med = actual, None
        for pos in range(k):
            for h in range(n):
                if h in med:
                    continue
                cand = med.copy()
                cand[pos] = h
                c = _coste(D, cand, w)
                if c < mejor_coste - 1e-12:
                    mejor_coste, mejor_med = c, cand
        if mejor_med is None:
            return med, actual
        med, actual = mejor_med, mejor_coste


def pam(D: np.ndarray, k: int, w: np.ndarray | None = None,
        reinicios: int = 50) -> tuple[list[int], np.ndarray]:
    """PAM: fase BUILD mas fase SWAP, con reinicios aleatorios.

    Con pesos, el criterio es sum_i w_i * d(i, medoide(i)); con pesos enteros
    equivale a replicar cada observacion w veces, igual que en el Ward ponderado
    de `40_uam_metodo.ward_ponderado`.

    POR QUE LOS REINICIOS. La fase SWAP es busqueda local: acepta el mejor
    intercambio y para cuando ninguno mejora, asi que puede quedarse en un
    optimo local. Medido contra la enumeracion exhaustiva en casos chicos
    (n = 14, k = 3), el BUILD+SWAP clasico —el de Kaufman y Rousseeuw, que es el
    de `pam()` en R— falla en 11 de 60 casos, con una brecha de hasta 6,8 % en
    el coste. Con reinicios desde conjuntos de medoides al azar, y quedandose con
    el mejor, la falla desaparece en las mismas pruebas. La semilla es fija: dos
    corridas dan exactamente el mismo resultado.
    """
    n = D.shape[0]
    w = np.ones(n) if w is None else np.asarray(w, dtype=float)
    rng = np.random.default_rng(20260813 + k)

    mejor_med, mejor_coste = _swap(D, _build(D, k, w), w)
    for _ in range(reinicios):
        inicio = list(rng.choice(n, size=k, replace=False))
        cand, coste = _swap(D, inicio, w)
        if coste < mejor_coste - 1e-12:
            mejor_med, mejor_coste = cand, coste

    return mejor_med, D[mejor_med, :].argmin(axis=0)


# ---------------------------------------------------------------------------
# Silueta de Kaufman y Rousseeuw, sobre la matriz de distancias
# ---------------------------------------------------------------------------
def silueta(D: np.ndarray, et: np.ndarray, w: np.ndarray | None = None) -> float:
    """Silueta media. Con `w`, promedios y media final ponderados por el peso.

    s(i) = (b - a) / max(a, b), con `a` la distancia media a los demas del propio
    grupo y `b` la menor distancia media a otro grupo. Un grupo unitario aporta 0
    por convencion, que es la de Rousseeuw.
    """
    n = D.shape[0]
    w = np.ones(n) if w is None else np.asarray(w, dtype=float)
    grupos = np.unique(et)
    if len(grupos) < 2:
        return float("nan")
    s = np.zeros(n)
    for i in range(n):
        propio_sin_i = et == et[i]
        propio_sin_i[i] = False
        if w[propio_sin_i].sum() <= 0:
            s[i] = 0.0
            continue
        a = float((w[propio_sin_i] * D[i, propio_sin_i]).sum() / w[propio_sin_i].sum())
        b = min(float((w[et == g] * D[i, et == g]).sum() / w[et == g].sum())
                for g in grupos if g != et[i])
        s[i] = 0.0 if max(a, b) == 0 else (b - a) / max(a, b)
    return float((w * s).sum() / w.sum())


# ---------------------------------------------------------------------------
# Varianza de la productividad explicada por la particion
# ---------------------------------------------------------------------------
def eta2_productividad(d: pd.DataFrame, et: np.ndarray, w: np.ndarray) -> float:
    """R2 de regresar el log de la productividad contra dummies de conglomerado.

    Ponderado por empleo: es la fraccion de la dispersion de productividad ENTRE
    actividades que la particion deja entre grupos y no dentro de ellos. Se lee
    en logaritmos porque la productividad es multiplicativa y su nivel esta
    dominado por la cola alta.
    """
    y = np.log(np.maximum(d["valor_agrega"].to_numpy() / d["empleo"].to_numpy(), 1e-12))
    w = np.asarray(w, dtype=float)
    ok = np.isfinite(y) & (w > 0)
    y, w, et = y[ok], w[ok], np.asarray(et)[ok]
    mu = float((w * y).sum() / w.sum())
    total = float((w * (y - mu) ** 2).sum())
    if total <= 0:
        return float("nan")
    entre = 0.0
    for g in np.unique(et):
        m = et == g
        mg = float((w[m] * y[m]).sum() / w[m].sum())
        entre += float(w[m].sum()) * (mg - mu) ** 2
    return entre / total


# ---------------------------------------------------------------------------
# Etiquetado y particion
# ---------------------------------------------------------------------------
def reetiquetar(et: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Numera los conglomerados por masa descendente: C1 es siempre el mayor."""
    et = np.asarray(et)
    masa = {g: float(np.asarray(w)[et == g].sum()) for g in np.unique(et)}
    orden = {g: i for i, g in enumerate(sorted(masa, key=lambda g: -masa[g]), start=1)}
    return np.array([orden[g] for g in et])


def preparar(d: pd.DataFrame, spec: dict) -> tuple[np.ndarray, np.ndarray | None]:
    """Construye las variables segun la especificacion y devuelve (z, pesos)."""
    v = uam.construir_variables(d, balanza=spec["balanza"])
    if spec["logs"]:
        v = uam.transformar_logs(v, VARS)
    w = d["empleo"].to_numpy(dtype=float) if spec["pesos"] else None
    z = uam.estandarizar(v, VARS, w)
    if not np.isfinite(z).all():
        malas = [x for i, x in enumerate(VARS) if not np.isfinite(z[:, i]).all()]
        raise ValueError(f"variables no finitas tras estandarizar: {malas}")
    return z, w


def particionar(d: pd.DataFrame, spec: dict, k: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve (etiquetas reetiquetadas, matriz de distancias, pesos efectivos)."""
    z, w = preparar(d, spec)
    peso_ef = np.ones(len(d)) if w is None else w
    D = matriz_distancias(z, spec["metrica"])
    if spec["algoritmo"] == "ward":
        if w is None:
            Z = linkage(z, method="ward", metric="euclidean")
        else:
            Z = uam.ward_ponderado(z, w)
        et = fcluster(Z, t=k, criterion="maxclust")
    elif spec["algoritmo"] == "pam":
        _, et = pam(D, k, w)
    else:
        raise ValueError(spec["algoritmo"])
    return reetiquetar(et, peso_ef), D, peso_ef


# ---------------------------------------------------------------------------
# Descripcion
# ---------------------------------------------------------------------------
def describir(d: pd.DataFrame, et: np.ndarray, tot: dict) -> pd.DataFrame:
    g = d.assign(_c=et).groupby("_c")
    t = pd.DataFrame({
        "n": g.size(),
        "empleo_%": 100 * g["empleo"].sum() / tot["empleo"],
        "VA_%": 100 * g["valor_agrega"].sum() / tot["valor_agrega"],
        "expo_%": 100 * g["expo"].sum() / tot["expo"],
    })
    t["productividad"] = 100 * (t["VA_%"] / t["empleo_%"])
    t["masa_salarial_VA_%"] = 100 * g["remunera"].sum() / g["valor_agrega"].sum()
    t.index.name = "conglomerado"
    return t


def imprimir(titulo: str, res: pd.DataFrame, d: pd.DataFrame, et: np.ndarray) -> None:
    print(f"\n{'-' * 86}\n{titulo}\n{'-' * 86}")
    print(res.round(1).to_string())
    dd = d.assign(_c=et)
    for c in sorted(pd.unique(et)):
        sub = dd[dd["_c"] == c].sort_values("empleo", ascending=False)
        print(f"\n  C{c} ({len(sub)} unidades):")
        for _, r in sub.head(14).iterrows():
            print(f"      {str(r['desc'])[:60]:62s} {r['empleo']:>10,.0f}")
        if len(sub) > 14:
            print(f"      ... y {len(sub) - 14} mas")


# ---------------------------------------------------------------------------
# Especificaciones
# ---------------------------------------------------------------------------
def specs() -> list[dict]:
    """Las siete especificaciones que se comparan, con su etiqueta de lectura."""
    def s(nombre, algoritmo, metrica, pesos, logs, balanza):
        return {"nombre": nombre, "algoritmo": algoritmo, "metrica": metrica,
                "pesos": pesos, "logs": logs, "balanza": balanza}
    return [
        # Referencia: es exactamente la UAM.
        s("1. Ward euclidiano (UAM)", "ward", "euclid", False, False, "nivel"),
        # 1. El algoritmo solo.
        s("2. PAM euclidiano", "pam", "euclid", False, False, "nivel"),
        # 2. La metrica.
        s("3. PAM Manhattan", "pam", "manhattan", False, False, "nivel"),
        # 3. Las dos estrategias de robustez, una contra otra.
        s("4. Ward + logs + peso + balanza norm.", "ward", "euclid", True, True, "norm"),
        s("5. PAM euclid. + peso + balanza norm.", "pam", "euclid", True, False, "norm"),
        s("6. PAM Manhattan + peso + balanza norm.", "pam", "manhattan", True, False, "norm"),
        s("7. PAM Manhattan + logs + peso + bal. norm.", "pam", "manhattan", True, True, "norm"),
    ]


# ---------------------------------------------------------------------------
# Invariancia a la desagregacion
# ---------------------------------------------------------------------------
def clonar(d: pd.DataFrame, cuantas: int = 5, veces: int = 3) -> tuple[pd.DataFrame, list[str]]:
    """Parte las `cuantas` actividades de mas empleo en `veces` clones identicos.

    No cambia la economia, solo la nomenclatura: una particion que se mueve con
    esto esta leyendo el nivel de desagregacion del Banco Central, no la
    estructura productiva.
    """
    grandes = set(d["empleo"].nlargest(cuantas).index)
    filas = []
    for i, r in d.iterrows():
        n = veces if i in grandes else 1
        for j in range(n):
            s = r.copy()
            for col in SUMABLES:
                s[col] = r[col] / n
            s.name = f"{i}_{j}"
            filas.append(s)
    return pd.DataFrame(filas), [f"{i}_0" for i in d.index]


# ---------------------------------------------------------------------------
def cargar(periodo: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """La replica (actividades clasificadas), la COU completa y los totales."""
    d = pd.read_csv(rutas.exigir(rutas.INTER / f"uam_replica_p{periodo}.csv",
                                 "la replica; correr antes 20_replica_hclust.py"),
                    index_col=0)
    d.index = d.index.astype(str)
    insumo = pd.read_excel(rutas.exigir(rutas.D_UAM_INSUMO, "el insumo de la UAM"))
    full = insumo[insumo["periodo"] == periodo].set_index("codigo_3dig").sort_index()
    full.index = full.index.astype(str)
    tot = insumo[insumo["periodo"] == periodo][SUMABLES].sum().to_dict()
    return d, full, tot


def verificar() -> None:
    """Cuatro controles de la implementacion. Si alguno falla, la corrida para.

    PAM es una heuristica —la fase SWAP acepta el mejor intercambio local—, asi
    que no basta con que corra: hay que comprobar que sobre casos donde el optimo
    global es enumerable, lo encuentra. Y el equivalente ponderado tiene que
    coincidir con replicar cada observacion, que es la misma propiedad que se le
    exige al Ward con masas en `40_uam_metodo.ward_ponderado`.
    """
    from itertools import combinations
    rng = np.random.default_rng(20260813)

    # 1. Optimo global, por fuerza bruta. n = 14 y k = 3 son 364 conjuntos.
    for prueba in range(12):
        x = rng.normal(size=(14, 4))
        D = matriz_distancias(x, "euclid")
        med, _ = pam(D, 3)
        mejor = min(_coste(D, list(c), np.ones(14)) for c in combinations(range(14), 3))
        obtenido = _coste(D, med, np.ones(14))
        assert obtenido <= mejor + 1e-9, f"PAM no halla el optimo (prueba {prueba})"

    # 2. Pesos enteros equivalen a replicar la observacion.
    x = rng.normal(size=(10, 3))
    w = rng.integers(1, 4, size=10).astype(float)
    idx = np.repeat(np.arange(10), w.astype(int))
    Dw = matriz_distancias(x, "manhattan")
    Dr = matriz_distancias(x[idx], "manhattan")
    _, et_w = pam(Dw, 3, w)
    _, et_r = pam(Dr, 3)
    ari = uam.rand_ajustado(et_w, pd.Series(et_r).groupby(idx).first().to_numpy())
    assert abs(ari - 1.0) < 1e-9, f"PAM ponderado != PAM sobre replicas (ARI {ari:.4f})"

    # 3. La silueta separa lo separable y no ve estructura donde no la hay.
    blobs = np.vstack([rng.normal(0, 0.2, (25, 2)), rng.normal(12, 0.2, (25, 2))])
    et = np.r_[np.ones(25, int), 2 * np.ones(25, int)]
    s_sep = silueta(matriz_distancias(blobs, "euclid"), et)
    ruido = rng.uniform(size=(60, 2))
    _, et_r2 = pam(matriz_distancias(ruido, "euclid"), 2)
    s_ruido = silueta(matriz_distancias(ruido, "euclid"), et_r2)
    assert s_sep > 0.95, f"silueta baja en dos nubes separadas: {s_sep:.3f}"
    assert s_ruido < 0.55, f"silueta alta sobre ruido uniforme: {s_ruido:.3f}"

    # 4. Con peso unitario, la silueta ponderada es la simple.
    assert abs(silueta(matriz_distancias(blobs, "euclid"), et, np.ones(50)) - s_sep) < 1e-12

    print(f"Controles de implementacion: 4/4 OK "
          f"(optimo global en 12 casos; ponderacion = replicacion; "
          f"silueta {s_sep:.3f} separadas / {s_ruido:.3f} ruido)")


def main() -> int:
    rutas.preparar_directorios()
    verificar()
    filas, membres, figura_datos = [], [], {}

    for periodo in (2, 1):
        anio = ANIO[periodo]
        d, full, tot = cargar(periodo)
        cobre = [i for i in full.index
                 if "cobre" in rutas.normalizar(str(full.loc[i, "desc"]))]
        print(f"\n{'=' * 86}\nPERIODO {periodo} ({anio}) — {len(d)} actividades clasificadas, "
              f"{len(full)} en la COU completa\n{'=' * 86}")

        # Control: la especificacion 1 tiene que devolver la particion de la UAM.
        et_ctrl, _, _ = particionar(d, specs()[0], 4 if periodo == 1 else 2)
        rand_ctrl = uam.rand_simple(d["cluster"].to_numpy(), et_ctrl)
        print(f"Control: especificacion 1 contra la UAM -> Rand {rand_ctrl:.4f} "
              f"{'OK' if rand_ctrl == 1.0 else 'FALLA'}")
        if rand_ctrl != 1.0:
            print("  La referencia no reproduce el original. Parar aca.")
            return 461

        for etiqueta_base, base in (("clasificadas", d), ("COU completa", full)):
            w_emp = base["empleo"].to_numpy(dtype=float)
            ref = None
            en_detalle: dict[str, np.ndarray] = {}
            print(f"\n--- {anio} · {etiqueta_base} ({len(base)} actividades) "
                  f"{'-' * 30}")
            for spec in specs():
                for k in KS:
                    try:
                        et, D, w_ef = particionar(base, spec, k)
                    except ValueError as e:
                        print(f"  {spec['nombre']:44s} k={k}: {e}")
                        continue
                    res = describir(base, et, tot)
                    sil_p = silueta(D, et, w_emp)
                    sil_s = silueta(D, et, None)
                    eta2 = eta2_productividad(base, et, w_emp)
                    degen = int((res["empleo_%"] < 1.0).sum())
                    if spec["nombre"].startswith("1.") and k == K_DETALLE:
                        ref = et
                    fila = {
                        "anio": anio, "base": etiqueta_base, "especificacion": spec["nombre"],
                        "algoritmo": spec["algoritmo"], "metrica": spec["metrica"],
                        "ponderado": spec["pesos"], "logs": spec["logs"],
                        "balanza": spec["balanza"], "unidades": len(base), "k": k,
                        "tamanos (n)": " / ".join(str(x) for x in res["n"]),
                        "empleo % por grupo": " / ".join(f"{x:.1f}" for x in res["empleo_%"]),
                        "productividad por grupo": " / ".join(
                            f"{x:.0f}" for x in res["productividad"]),
                        "masa salarial/VA por grupo": " / ".join(
                            f"{x:.1f}" for x in res["masa_salarial_VA_%"]),
                        "empleo % del mayor": float(res["empleo_%"].max()),
                        "grupos con <1% del empleo": degen,
                        "silueta ponderada": sil_p,
                        "silueta sin ponderar": sil_s,
                        "eta2 log productividad": eta2,
                    }
                    if etiqueta_base == "clasificadas":
                        fila["Rand vs UAM"] = uam.rand_simple(base["cluster"].to_numpy(), et)
                        fila["ARI vs UAM"] = uam.rand_ajustado(base["cluster"].to_numpy(), et)
                    if ref is not None and k == K_DETALLE:
                        fila["ARI vs Ward mismo k"] = uam.rand_ajustado(ref, et)
                    # El cobre esta EXCLUIDO de las actividades clasificadas: solo
                    # se puede decir donde cae cuando se corre la COU completa.
                    if cobre and cobre[0] in base.index:
                        s = pd.Series(et, index=base.index)
                        g = s.loc[cobre[0]]
                        fila["cobre en"] = (f"C{g} de {k}, con {(s == g).sum()} actividades, "
                                            f"{res.loc[g, 'empleo_%']:.2f} % del empleo")
                    filas.append(fila)

                    if k == K_DETALLE:
                        en_detalle[spec["nombre"]] = et
                        print(f"  {spec['nombre']:44s} k={k} "
                              f"tam {fila['tamanos (n)']:22s} "
                              f"prod {fila['productividad por grupo']:26s} "
                              f"sil {sil_p:5.2f} eta2 {eta2:5.3f}")
                        imprimir(f"{anio} · {etiqueta_base} · {spec['nombre']} · k={k}",
                                 res, base, et)
                        m = base[["desc", "empleo", "valor_agrega", "expo"]].copy()
                        m["conglomerado"] = et
                        m["empleo_%"] = 100 * m["empleo"] / tot["empleo"]
                        m["expo_%"] = 100 * m["expo"] / tot["expo"]
                        m["productividad"] = ((100 * m["valor_agrega"] / tot["valor_agrega"])
                                              / (m["empleo"] / tot["empleo"]))
                        m["especificacion"] = f"{anio} · {etiqueta_base} · {spec['nombre']}"
                        membres.append(m.reset_index())

                    if etiqueta_base == "clasificadas":
                        figura_datos.setdefault((anio, spec["nombre"]), {})[k] = (
                            sil_p, float(res["empleo_%"].max()), eta2)

            # ---------------------------------------------------------------
            # ¿Convergen las dos estrategias de robustez?
            # ---------------------------------------------------------------
            # La pregunta que decide si la especificacion preferida del capitulo
            # depende de la familia de metodos: ARI de cada par de
            # especificaciones sobre las MISMAS actividades y el mismo k.
            nombres = list(en_detalle)
            print(f"\n  ARI entre especificaciones, {anio} · {etiqueta_base} · k={K_DETALLE}:")
            encabezado = "      " + "".join(f"{n.split('.')[0]:>7s}" for n in nombres)
            print(encabezado)
            for a in nombres:
                celdas = "".join(
                    f"{uam.rand_ajustado(en_detalle[a], en_detalle[b]):7.3f}" for b in nombres)
                print(f"    {a.split('.')[0]:>2s}{celdas}")
                fila = {"anio": anio, "base": f"[ARI entre especificaciones] {etiqueta_base}",
                        "especificacion": a, "unidades": len(base), "k": K_DETALLE}
                fila.update({f"ARI vs {b}": uam.rand_ajustado(en_detalle[a], en_detalle[b])
                             for b in nombres})
                filas.append(fila)

        # -------------------------------------------------------------------
        # Invariancia a la desagregacion, por familia de metodos
        # -------------------------------------------------------------------
        dc, prim = clonar(d)
        print(f"\n--- {anio} · invariancia: las 5 actividades de mas empleo partidas en "
              f"3 clones identicos ---")
        print(f"    {', '.join(str(x) for x in d.loc[d['empleo'].nlargest(5).index, 'desc'])}")
        for k in (2, 4):
            fila = {"anio": anio, "base": "[invariancia a clonar]",
                    "especificacion": f"ARI antes vs despues de clonar, k={k}",
                    "unidades": len(dc), "k": k}
            for spec in specs():
                try:
                    a, _, _ = particionar(d, spec, k)
                    b, _, _ = particionar(dc, spec, k)
                except ValueError:
                    continue
                ari = uam.rand_ajustado(a, pd.Series(b, index=dc.index).loc[prim].to_numpy())
                fila[spec["nombre"]] = ari
                print(f"    k={k}  {spec['nombre']:44s} ARI {ari:.3f}")
            filas.append(fila)

    # -----------------------------------------------------------------------
    resumen = pd.DataFrame(filas)
    resumen.to_excel(OUT_T(f"T_I13 PAM medoides contra Ward"), index=False)
    memb = pd.concat(membres, ignore_index=True)
    for anio, nombre in ((2023, "T_I14 membresias PAM 2023"),
                         (2003, "T_I15 membresias PAM 2003")):
        memb[memb["especificacion"].str.startswith(str(anio))].to_excel(
            OUT_T(nombre), index=False)
    dibujar(figura_datos)
    print(f"\nTablas y figura escritas en {rutas.OUT}")
    return 0


def OUT_T(nombre: str) -> Path:
    """Ruta de tabla con el lote de HOY, no con `rutas.FECHA`."""
    return rutas.OUT / f"{HOY} {nombre}.xlsx"


def dibujar(datos: dict) -> None:
    """Silueta y degeneracion por k, para 2023 y 2003, en las siete especificaciones."""
    if not datos:
        return
    asegurar_fuente((8.5, 9, 10, 12))
    anios = sorted({a for a, _ in datos})
    fig, axes = plt.subplots(3, len(anios), figsize=(6.2 * len(anios), 11.0), sharex=True)
    axes = np.atleast_2d(axes)
    if axes.shape[0] == 1:
        axes = axes.T
    colores = plt.cm.tab10(np.linspace(0, 1, 10))
    titulos = ("silueta media (ponderada por empleo)",
               "empleo del conglomerado mayor, %",
               "η² del log de la productividad")
    for j, anio in enumerate(anios):
        nombres = [n for a, n in datos if a == anio]
        for i, nombre in enumerate(nombres):
            dd = datos[(anio, nombre)]
            ks = sorted(dd)
            for fila in range(3):
                axes[fila, j].plot(ks, [dd[k][fila] for k in ks], marker="o", ms=4,
                                   color=colores[i % 10], lw=1.6,
                                   label=nombre if fila == 0 else None)
        for fila in range(3):
            axes[fila, j].set_title(f"{anio} — {titulos[fila]}", fontsize=10)
        axes[1, j].axhline(90, color="#C44E52", lw=1, ls="--")
        axes[2, j].set_xlabel("número de conglomerados (k)")
    # Siete etiquetas largas no caben dentro de un panel: van al pie, en dos filas
    # y compartidas por los seis paneles.
    manijas, etiquetas_leg = axes[0, 0].get_legend_handles_labels()
    fig.legend(manijas, etiquetas_leg, fontsize=9, ncol=2, loc="upper center",
               bbox_to_anchor=(0.5, 0.045), frameon=False)
    fig.suptitle("PAM / k-medoides contra Ward: separación, degeneración del corte y "
                 "capacidad de ordenar la productividad", fontsize=12)
    fig.text(0.5, -0.075,
             "Arriba, silueta media de Kaufman y Rousseeuw: mide cuánto más cerca está cada "
             "actividad de su propio grupo que del más próximo; premia aislar una observación "
             "extrema, así que\nsube justo donde la partición se degenera. En el medio, "
             "porcentaje del empleo que reúne el conglomerado mayor: por encima de la línea "
             "roja la partición no informa. Abajo, fracción de la\nvarianza del logaritmo de "
             "la productividad —entre actividades, ponderada por empleo— que queda ENTRE "
             "conglomerados. Actividades clasificadas por la UAM.",
             ha="center", fontsize=8.5, color="#444444")
    fig.tight_layout(rect=(0, 0.075, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(rutas.OUT / f"F_I5 PAM medoides contra Ward.{ext}", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
