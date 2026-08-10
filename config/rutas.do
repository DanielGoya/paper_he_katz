*! rutas.do — resolución de rutas del proyecto paper-he-katz
*! ÚNICO archivo del repo con rutas absolutas. Es el equivalente de
*! anclas.yaml del gestor: lo único que cambia entre los tres PCs.
*!
*! Regla del proyecto (MEMORY.md §Proyectos con datos):
*!   · los datos se LEEN del almacén general y NO se copian al repo;
*!   · las salidas se ESCRIBEN al árbol de artefactos, fuera del repo.
*!
*! Si un ancla falta, esto se cae con mensaje claro. Nunca se adivina.

version 15

* ---------------------------------------------------------------------------
* 1. Anclas de esta instalación
* ---------------------------------------------------------------------------
global A_dropbox   "D:/Dropbox"
global A_repos     "D:/repos"

* ---------------------------------------------------------------------------
* 2. Raíces derivadas
* ---------------------------------------------------------------------------
global REPO        "$A_repos/paper_he_katz"
global ALMACEN     "$A_dropbox/Recursos/Datos"          // datos de terceros, compartidos
global ARTEF       "$A_dropbox/Trabajo/Paper HE Katz"   // árbol de artefactos del proyecto

global RAW         "$ARTEF/datos/raw_local"
global INTER       "$ARTEF/datos/intermediate"
global OUT         "$ARTEF/datos/output"
global SCRATCH     "$ARTEF/datos/scratch"

global SRC         "$REPO/src"
global DOCS        "$REPO/docs"

* ---------------------------------------------------------------------------
* 3. Punteros a las bases del almacén (referenciar, nunca copiar)
* ---------------------------------------------------------------------------
global D_ETD       "$ALMACEN/GGDC ETD/ETD_230918.dta"
global D_CASEN00   "$ALMACEN/Casen/2000/casen2000_Stata.dta"
global D_CASEN22   "$ALMACEN/Casen/2022/Base de datos Casen 2022 STATA.dta"
global D_CASEN24   "$ALMACEN/Casen/2024/casen_2024.dta"
global D_ATLAS_CP  "$ALMACEN/Atlas of Economic Complexity/hs92_country_product_year_4.csv"
global D_ATLAS_ECI "$ALMACEN/Atlas of Economic Complexity/growth_proj_eci_rankings.csv"
global D_ENIA      "$ALMACEN/ENIA panel/dta/datos_seguimiento_enia.dta"
global D_ENE       "$ALMACEN/ENE"
global D_SII       "$ALMACEN/SII/Pub_Empresas"

* Bajadas nuevas de este proyecto (van al almacén, no al repo)
global D_WDI       "$ALMACEN/World Bank WDI/2026-08"
global D_WDI_CSV   "$D_WDI/wdi_5paises_1960_2025.csv"
global D_WDI_2021  "$ALMACEN/World Bank WDI/2021-12/65c64ccd-7a94-4001-b79c-ab52f611ff0b_Data.csv"

* ---------------------------------------------------------------------------
* 3b. Años de la comparación Casen
*     La carta de Dutrénit pide «2000 vs. actualidad». 2022 se conserva como punto
*     intermedio porque es la encuesta con la que se validó todo el pipeline.
* ---------------------------------------------------------------------------
global ANIOS     "2000 2022 2024"
global ANIO_INI  2000
global ANIO_FIN  2024
global D_BCCH      "$ALMACEN/Banco Central de Chile"
global D_ILO       "$ALMACEN/ILOSTAT"

* ---------------------------------------------------------------------------
* 4. Verificación: si algo no está, parar acá y no más adelante
* ---------------------------------------------------------------------------
capture confirm file "$D_ETD"
if _rc {
    display as error "No se encuentra el ETD en: $D_ETD"
    display as error "Revisar el ancla A_dropbox en config/rutas.do."
    exit 601
}
foreach d in "$OUT" "$INTER" "$SCRATCH" {
    capture mkdir "`d'"
}

* ---------------------------------------------------------------------------
* 5. Preferencias de sesión
* ---------------------------------------------------------------------------
set more off
set varabbrev off
graph set window fontface "Calibri"

* Esquema gráfico del proyecto: sobrio, para imprenta en blanco y negro o color
capture noisily set scheme s1color
