# Heterogeneidad estructural en Chile — capítulo con Jorge Katz

Código de la entidad `paper-he-katz` del gestor de proyectos.

Capítulo de Chile del libro comparado sobre heterogeneidad estructural que coordina Gabriela
Dutrénit (UAM); con Jorge Katz, DG en la parte cuantitativa.

## Las raíces

El repo es **una** de las raíces de la entidad, atadas todas por el mismo `id`
(`MEMORY.md` §Proyectos con datos). Las otras viven en Dropbox y **no** están acá:

| Raíz | Dónde |
|---|---|
| Vault (notas, panel, tareas) | `<vault_trabajo>\paper-he-katz` |
| Artefactos y memoria del proyecto | `<dropbox>\Trabajo\Paper HE Katz` |
| Datos y salidas | `<dropbox>\Trabajo\Paper HE Katz\datos` |

> Los datos y las salidas **no entran a git**: el `.gitignore` es red de seguridad,
> no el mecanismo. El mecanismo es que las rutas de entrada y salida apuntan fuera
> del repositorio, por configuración.

El estado del proyecto y los próximos pasos están en
`<dropbox>\Trabajo\Paper HE Katz\MEMORY.md`.

## Cómo correrlo

Requiere **Stata 15 o superior**. Una corrida limpia toma 15-25 minutos; la parte lenta es la
importación del Atlas of Economic Complexity (~450 MB), que queda cacheada en `intermediate/`.

```bash
"C:/Program Files (x86)/Stata15/StataMP-64.exe" /e do "D:/repos/paper_he_katz/src/00_master.do"
```

O, desde el acceso directo `Análisis HE Katz` de la carpeta padre, que además sincroniza el
repositorio antes de correr.

Lo único que cambia entre computadores es `config/rutas.do`, que es el equivalente local de
`anclas.yaml` del gestor. Si falta una base, el script se cae ahí con mensaje claro en vez de
fallar más adelante.

## Qué hace cada archivo

| Archivo | Bloque | Qué produce |
|---|---|---|
| `config/rutas.do` | — | Resuelve anclas y punteros a las bases del almacén. Único archivo con rutas absolutas |
| `src/00_master.do` | — | Corre todo de punta a punta; el log queda en `datos\scratch` |
| `src/01_etd_he_crosscountry.do` | A | Índices de HE entre sectores y descomposición McMillan-Rodrik, Chile con benchmarks (GGDC ETD) |
| `src/02_casen_armonizar.do` | — | Base persona-año armonizada Casen 2000, 2022 y 2024, con su validación contra cifras oficiales |
| `src/03_casen_estratos.do` | B | Estratos de productividad PREALC/CEPAL y descomposición de Theil del ingreso laboral |
| `src/04_casen_cuatro_chiles.do` | C | Los «cuatro Chiles» cuantificados, con árbol de decisión y tabla de sensibilidad |
| `src/05_dispersion_intra_enia.do` | E | Dispersión de productividad dentro de cada rama manufacturera (ENIA 1995-2015) |
| `src/06_complejidad_exportadora.do` | D4 | Complejidad y diversificación exportadora (Atlas of Economic Complexity) |
| `src/07_contraste_narrativa.do` | D | Contraste de afirmaciones puntuales del ensayo de Katz con los datos |
| `src/08_productividad_sii.do` | F | Productividad y salarios por rama × tamaño de empresa, y el puente de tramo de venta a banda de empleo (SII 2005-2024) |
| `src/09_moderno_productividad.do` | G | El «Chile moderno» definido por productividad, en tres capas |
| `src/10_productividad_enia.do` | H | Productividad con valor agregado real de planta y no con ventas, y quién se queda con la nómina (ENIA 1995-2015) |
| `src/11_conglomerados_chile.do` | I | Do-file autónomo y expositivo: réplica del Ward chileno, reincorporación del cobre y sensibilidades una por una (comercio, logs, ponderación, PAM, universo, *k*, agregación y clones) |

Cada do-file lleva en el encabezado la fuente, las decisiones de construcción y las advertencias
de medición. Los que lo ameritan traen chequeos internos que abortan la corrida si una identidad
no cierra —la descomposición McMillan-Rodrik, la de Theil, la partición de los cuatro Chiles—.

## La capa de Python: bloques I, J y K

Corre **aparte del pipeline de Stata**. El bloque I existe en Python porque replica el `hclust` de
R que usó el equipo de la UAM y `scipy.cluster.hierarchy` lo reproduce exactamente; los bloques J y
K se le sumaron después y comparten el entorno.

```bash
powershell -File "D:/repos/paper_he_katz/scripts/crear-entorno.ps1"
```

Después, **desde `py/`** y en este orden (los scripts se invocan por ruta absoluta al intérprete
del venv, nunca con el nombre `python`):

```bash
D:/repos/paper_he_katz/.venv/Scripts/python.exe 20_replica_hclust.py
```

y en seguida `21`, `22`, `23`, `24`, `25` (bloque I) · `30` (bloque J) · `41`, `42`, `43`, `44`
(bloque K). Dentro de cada bloque el orden importa; entre bloques, no. `40_uam_metodo.py` no se
corre solo: lo importan `42`, `43` y `44`.

### Bloque I — la capa de conglomerados

Responde al pedido de Gabriela Dutrénit de incorporar variables de sustentabilidad, digitalización
y tamaño de empresa.

La implementación que produjo los resultados del bloque vive en Python. Para mostrar el
procedimiento íntegramente en Stata 15, `src/11_conglomerados_chile.do` traduce la réplica y las
principales sensibilidades a Stata/Mata. Corre de forma autónoma y no forma parte de
`src/00_master.do`; puede detenerse después de cada enfoque activando `PAUSAR` al comienzo.

| Archivo | Qué produce |
|---|---|
| `py/rutas.py` | Gemelo de `config/rutas.do`: único archivo de `py/` con rutas absolutas |
| `py/20_replica_hclust.py` | Réplica del agrupamiento de la UAM. Verifica que reproduce su partición y aborta si no: es el test de regresión del bloque |
| `py/21_concordancias.py` | Verifica que el `codigo_3dig` de la UAM es el código de actividad del Banco Central; clasifica los productos energéticos y TIC; resuelve CIIU4.CL → COU |
| `py/22_variables_nuevas.py` | Intensidad energética, digitalización, encadenamientos de Rasmussen y tamaño medio de empresa, por actividad |
| `py/23_cluster_ampliado.py` | Capa A (caracterización) y capa B (reagrupamiento), con placebo de dilución. Tablas `T_I1`-`T_I6`, figuras `F_I1`-`F_I2` |
| `py/24_carbono_retc.py` | Validación física contra emisiones declaradas de CO₂. Tablas `T_I7`-`T_I8`, figura `F_I3` |
| `py/25_unidad_de_observacion.py` | La unidad de observación del agrupamiento: agregar la manufactura o ponderar por empleo, y logaritmar las variables asimétricas. Tablas `T_I9`-`T_I12`, figura `F_I4` |

Las dos concordancias de nomenclatura viven en `config/` como CSV editables a mano
(`reglas_ciiu_a_cou.csv` para las 111 actividades de 2023 y `reglas_ciiu_a_cou73.csv` para las 73
de 2003), y se corrigen ahí, no en el código.

### Bloque J — la salmonicultura

| Archivo | Qué produce |
|---|---|
| `py/30_salmonicultura.py` | Actualiza con fuentes vigentes las tablas y gráficas de la sección 4.1 del libro FCE de Katz, que se detienen entre 2002 y 2016: *catch-up* con Noruega, antimicrobianos, precios de exportación, concentración, escala, mortalidad y presupuesto de Sernapesca. Tablas `T_J1`-`T_J9`, figuras `F_J1`-`F_J7`, cada una con el original de Katz como primer panel |

### Bloque K — los cuatro países

Aplica los criterios de la UAM a Argentina, Brasil y México, y diagnostica si aparece en ellos algo
comparable al problema del cobre chileno.

| Archivo | Qué produce |
|---|---|
| `py/40_uam_metodo.py` | El método de la UAM como módulo reutilizable: construcción de las siete variables, estandarización, Ward —con y sin pesos—, y los índices de Rand. No se ejecuta solo |
| `py/41_cou_multipais.py` | Extrae de las matrices insumo-producto de los cuatro países las siete magnitudes del ejercicio. Escribe `intermediate/cou_multipais.csv` |
| `py/42_cluster_multipais.py` | Valida el método sobre Chile y corre la especificación de la UAM y la mejorada país por país. Tablas `T_K1`-`T_K4` |
| `py/43_diagnostico_sectores.py` | Actividades atípicas, concentración exportadora y efecto de excluirlas. Tablas `T_K5`-`T_K8` |
| `py/44_figura_multipais.py` | Figura comparativa `F_K1` |

Los años no son los mismos en los cuatro países, y no por descuido: son los más cercanos a los de
Chile entre los que publican **empleo y remuneraciones por actividad**, que es la restricción que
manda. Brasil 2003 y 2021, México 2008 y 2018, Argentina sólo 1997. El detalle está en el memo
`2026-08-12-conglomerados-en-los-cuatro-paises` del vault y en el `LEEME.md` de cada carpeta de
datos.

## Documentos

**No están en este repo.** Son notas y borradores, y `spec/ubicacion.md` §1 los manda al vault de
la entidad, en `<vault_trabajo>\paper-he-katz`:

| Nota | Qué es |
|---|---|
| `2026-08-10-analisis-cuantitativo-de-la-HE` | Resumen corto de qué se hizo y qué salió |
| `2026-08-10-borrador-seccion-cuantitativa` | El texto para el capítulo |
| `2026-08-10-memo-de-resultados` | Lectura de resultados y reparto entre capítulos |
| `2026-08-10-contraste-narrativa-katz-vs-datos` | Afirmación por afirmación, para conversar con Jorge |
| `2026-08-11-lectura-de-las-planillas-de-la-UAM` | Qué traen las planillas del *cluster analysis* y qué problemas tiene su especificación |
| `2026-08-11-variables-adicionales-para-los-conglomerados` | Bloque I: las cuatro variables que pidió Dutrénit, construidas y corridas |
| `notas de trabajo\2026-08-11-agregar-o-ponderar-los-conglomerados` | Bloque I: la unidad de observación, la ponderación y los logaritmos |
| `notas de trabajo\2026-08-11-actualizacion-de-tablas-y-figuras-de-salmonicultura` | Bloque J |
| `notas de trabajo\2026-08-12-conglomerados-en-los-cuatro-paises` | Bloque K |

El estado del proyecto y las decisiones técnicas están en
`<dropbox>\Trabajo\Paper HE Katz\MEMORY.md`.

## Fuentes

Todas se leen del almacén general de datos compartidos (`<dropbox>\Recursos\Datos`) y ninguna se
copia al proyecto. Están declaradas en el campo `reusable` del manifiesto de la entidad.

| Fuente | Cobertura | Bloques |
|---|---|---|
| GGDC/UNU-WIDER Economic Transformation Database v2.0 | 12 sectores, 1990-2018, 51 países | A |
| Casen 2000 (base principal + complementaria de ingresos, metodología actual) | Personas, Chile | B, C, D |
| Casen 2022 y Casen 2024 | Personas, Chile | B, C, D, G |
| ENIA, panel de seguimiento | Plantas de 10+ ocupados, 1995-2015 | E |
| Atlas of Economic Complexity (HS92, 4 dígitos) | País-producto-año, 1995-2023 | D4 |
| SII, Estadísticas de Empresas | Rama × tramo de venta, 2005-2024 | F, G, H, I |
| World Development Indicators (API, agosto 2026) | Macro, 1960-2025 | D5 |
| Planillas del *cluster analysis* de la UAM | 73 y 111 actividades, 2003 y 2023 | I |
| COU y MIP del Banco Central (referencia 2003 y 2018; COU 2023 del Anuario) | 73 y 111 actividades | I |
| RETC, emisiones al aire de fuentes puntuales (MMA) | Establecimientos, 2023 | I |
| Sernapesca, informes de antimicrobianos y sanitarios; *Norwegian Fish Health Report*; DIPRES, Ley de Presupuestos | Chile y Noruega, 2007-2025 | J |
| FAO FishStat Aquaculture 2025.1.0 | País-especie-año | J |
| Repositorio de COU y MIP de la CEPAL | Argentina, Brasil, Chile y México | K |
| Tabelas de Recursos e Usos del IBGE (niveles 51 y 68) | 51 y 68 actividades, 2000-2021 | K |

Dos advertencias de comparabilidad que están resueltas en el código y conviene no volver a
descubrir: Casen 2024 estrenó una línea de pobreza que no empalma con las anteriores —se usa
`pobreza_2013`— y los archivos del SII vienen en `.xlsb`, que Stata no lee, así que al lado de
cada uno hay un `.csv` derivado.

Y dos del bloque I, cada una documentada en el `LEEME.md` de su carpeta del almacén: la matriz de
utilización intermedia hay que leerla a **precios de usuario** —es la valoración con la que cierra
la identidad VBP − consumo intermedio = valor agregado—, y del RETC hay que usar la columna
`emision_retc`, que es la validada por el MMA, y no `emision_total`, que es la estimación cruda y
lleva el CO₂ nacional por encima del inventario del país.

Pendiente de descargar: series anuales de Cuentas Nacionales del Banco Central (valor agregado y
ocupados por actividad, 1996-2024), para extender el bloque A más allá de 2018. Van al almacén
general, no al proyecto.
