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
| `src/02_casen_armonizar.do` | — | Base persona-año armonizada Casen 2000 vs 2022, con su validación contra cifras oficiales |
| `src/03_casen_estratos.do` | B | Estratos de productividad PREALC/CEPAL y descomposición de Theil del ingreso laboral |
| `src/04_casen_cuatro_chiles.do` | C | Los «cuatro Chiles» cuantificados, con árbol de decisión y tabla de sensibilidad |
| `src/05_dispersion_intra_enia.do` | E | Dispersión de productividad dentro de cada rama manufacturera (ENIA 1995-2015) |
| `src/06_complejidad_exportadora.do` | D4 | Complejidad y diversificación exportadora (Atlas of Economic Complexity) |
| `src/07_contraste_narrativa.do` | D | Contraste de afirmaciones puntuales del ensayo de Katz con los datos |

Cada do-file lleva en el encabezado la fuente, las decisiones de construcción y las advertencias
de medición. Los que lo ameritan traen chequeos internos que abortan la corrida si una identidad
no cierra —la descomposición McMillan-Rodrik, la de Theil, la partición de los cuatro Chiles—.

## Documentos

En `docs/`, todos en español y con fecha en el nombre según la convención del proyecto:

- **contraste narrativa Katz vs datos** — afirmación por afirmación, qué dicen los datos y qué
  habría que ajustar. Es el insumo para conversarlo con Jorge; no va al libro.
- **memo resultados** — lectura de los resultados, qué va al capítulo de Chile y qué al
  capítulo 5 de Jorge, y qué falta.
- **borrador seccion cuantitativa** — ~2.900 palabras listas para el capítulo.

## Fuentes

Todas se leen del almacén general de datos compartidos (`<dropbox>\Recursos\Datos`) y ninguna se
copia al proyecto. Están declaradas en el campo `reusable` del manifiesto de la entidad.

| Fuente | Cobertura | Bloques |
|---|---|---|
| GGDC/UNU-WIDER Economic Transformation Database v2.0 | 12 sectores, 1990-2018, 51 países | A |
| Casen 2000 (base principal + complementaria de ingresos, metodología actual) | Personas, Chile | B, C, D |
| Casen 2022 | Personas, Chile | B, C, D |
| ENIA, panel de seguimiento | Plantas de 10+ ocupados, 1995-2015 | E |
| Atlas of Economic Complexity (HS92, 4 dígitos) | País-producto-año, 1995-2023 | D4 |
| World Development Indicators (extracción dic-2021) | Macro, 1960-2020 | D5 |

Pendiente de descargar cuando haya conexión: Casen 2024 en Stata, ENE 2020-2026, Cuentas
Nacionales del Banco Central y WDI actualizado. Van al almacén general, no al proyecto.
