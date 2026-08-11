*! 00_master.do — corre todo el análisis cuantitativo del capítulo de Chile
*!
*! Proyecto: heterogeneidad estructural en Chile, capítulo con Jorge Katz para el
*!           libro comparado que coordina Gabriela Dutrénit (UAM).
*!
*! Uso, desde una consola:
*!   "C:/Program Files (x86)/Stata15/StataMP-64.exe" /e do "D:/repos/paper_he_katz/src/00_master.do"
*!
*! Los datos se leen del almacén general y NO se copian al repo; las salidas se
*! escriben en el árbol de artefactos del proyecto. Ver config/rutas.do.
*!
*! Duración aproximada de una corrida limpia: 15-25 minutos. La parte lenta es la
*! importación del Atlas of Economic Complexity (~450 MB), que queda cacheada en
*! intermediate/ y no se repite.

version 15
clear all
set more off

* La ruta del repo es lo único que hay que saber para arrancar
global REPO_ROOT "D:/repos/paper_he_katz"
do "$REPO_ROOT/config/rutas.do"

capture log close _all
log using "$SCRATCH/log_master.txt", replace text name(master)

display as text "{hline 78}"
display as text "Heterogeneidad estructural en Chile — pipeline cuantitativo"
display as text "Corrida: " c(current_date) " " c(current_time) " · Stata " c(stata_version)
display as text "{hline 78}"

* Bloque A · HE entre sectores, Chile y benchmarks (GGDC ETD)
do "$SRC/01_etd_he_crosscountry.do"

* Construcción · base persona-año armonizada Casen 2000 vs 2022
do "$SRC/02_casen_armonizar.do"

* Bloque B · Estratos de productividad al modo PREALC/CEPAL
do "$SRC/03_casen_estratos.do"

* Bloque C · Los cuatro Chiles, con números
do "$SRC/04_casen_cuatro_chiles.do"

* Bloque E · Dispersión intra-rama en manufactura (ENIA 1995-2015)
do "$SRC/05_dispersion_intra_enia.do"

* Bloque D4 · Complejidad y diversificación exportadora (Atlas of Complexity)
do "$SRC/06_complejidad_exportadora.do"

* Bloque D · Contraste de la narrativa de Katz con los datos
do "$SRC/07_contraste_narrativa.do"

* Capa de productividad · rama × tamaño de empresa (SII, 2005-2024)
do "$SRC/08_productividad_sii.do"

* Bloque G · El «Chile moderno» definido por productividad, en tres capas
do "$SRC/09_moderno_productividad.do"

* Bloque H · La capa de productividad con VALOR AGREGADO (ENIA 1995-2015), que corrige
*            el sesgo de medir con ventas del bloque F, y la partición de la nómina
do "$SRC/10_productividad_enia.do"

display as text _n "{hline 78}"
display as text "Pipeline terminado. Salidas en: $OUT"
display as text "{hline 78}"

log close master
