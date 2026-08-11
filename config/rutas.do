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
* Los documentos escritos NO viven en el repo: son notas y borradores, y el
* spec/ubicacion.md §1 los manda al vault de la entidad.
global DOCS        "$A_dropbox/Obsidian/Trabajo/paper-he-katz"

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
global D_ESI       "$ALMACEN/ESI"
* Estadísticas de Empresas del SII. La carpeta `Pub_Empresas` es la extracción de
* julio de 2019 y llega a 2018; la de 2026-08 llega a 2024 y es la que se usa. Los
* originales vienen en .xlsb, que Stata no lee: al lado hay un .csv derivado.
global D_SII       "$ALMACEN/SII/2026.08.10 Estadisticas de empresas"
global D_SII_RUBR  "$D_SII/PUB_TRAM_RUBR.csv"
global D_SII_ACT   "$D_SII/PUB_TRAM_ACT.csv"
global D_SII_2019  "$ALMACEN/SII/Pub_Empresas"

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

* ---------------------------------------------------------------------------
* 3c. Bloque H: la capa de conglomerados, que corre en Python (ver py/)
*     Estos punteros no los usa ningún .do todavía: están acá porque config/rutas.do
*     es el inventario de dónde vive cada fuente, y py/rutas.py es su gemelo.
* ---------------------------------------------------------------------------
* Cuadros de oferta y utilización y matrices insumo-producto del Banco Central.
* El COU de 2023 sale del Anuario de Cuentas Nacionales (27 meses de rezago), no de la
* página de compilaciones de referencia. Los de 2003 son .xls antiguo. Ver el LEEME.
global D_BCCH      "$ALMACEN/Banco Central de Chile"
global D_BCCH_COU  "$D_BCCH/2026.08.11 COU y MIP"
* Emisiones al aire de fuentes puntuales, MMA. Usar la columna `emision_retc`, que es la
* validada, y no `emision_total`, que es la estimación cruda. Ver el LEEME.
global D_RETC      "$ALMACEN/RETC/2026.08.11 Emisiones al aire fuentes puntuales"
global D_ILO       "$ALMACEN/ILOSTAT"

* ---------------------------------------------------------------------------
* 4. Verificación: si algo no está, parar acá y no más adelante
*    Se comprueban las fuentes de los bloques que corren en Stata. Las del bloque H
*    las verifica py/rutas.py con la misma lógica.
* ---------------------------------------------------------------------------
capture confirm file "$D_ETD"
if _rc {
    display as error "No se encuentra el ETD en: $D_ETD"
    display as error "Revisar el ancla A_dropbox en config/rutas.do."
    exit 601
}
* Inventario de punteros. NO aborta: los bloques 05, 08 y 09 están escritos para saltarse
* limpiamente si falta su fuente, y eso se respeta. Lo que hace es dejar constancia en el
* log de qué resuelve y qué no, porque hasta el 2026-08-11 `D_BCCH` y `D_ILO` apuntaban a
* carpetas inexistentes y nadie se enteró: la verificación de arriba sólo miraba el ETD.
display as text _n "{hline 60}"
display as text "Inventario de fuentes"
foreach g in D_CASEN00 D_CASEN22 D_CASEN24 D_ATLAS_CP D_ATLAS_ECI D_ENIA ///
             D_SII_RUBR D_SII_ACT D_WDI_CSV D_BCCH_COU D_RETC D_ILO {
    capture confirm file "${`g'}"
    local rc1 = _rc
    capture confirm file "${`g'}/."
    if `rc1' == 0 | _rc == 0 {
        display as text "  ok      `g'"
    }
    else {
        display as error "  FALTA   `g' -> ${`g'}"
    }
}
display as text "{hline 60}" _n
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
