*! 02_casen_armonizar.do
*! Construye la base persona-año armonizada Casen 2000 vs Casen 2022, que es el
*! insumo de los bloques B (estratos de productividad) y C (los cuatro Chiles).
*!
*! Fuentes:
*!   Casen 2000, base principal + base complementaria de ingresos con METODOLOGÍA
*!     ACTUAL (variables *_mn), que es la que hace comparables ingresos y pobreza
*!     con las Casen recientes.
*!   Casen 2022 y Casen 2024, bases nacionales en Stata. 2024 es el punto de
*!     «actualidad» que pide la carta; 2022 se conserva como punto intermedio.
*!   Ministerio de Desarrollo Social y Familia. Encuesta de Caracterización
*!     Socioeconómica Nacional (Casen), 2000, 2022 y 2024.
*!
*! Decisiones de armonización, todas explícitas y verificables abajo:
*!   · Rama: 9 grandes divisiones CIIU rev.2. En 2000 vienen dadas (`ramar`); en 2022
*!     se agregan las 21 secciones de la rev.4. A 4 dígitos no hay comparabilidad y no
*!     se finge que la haya.
*!   · Tamaño del establecimiento: los seis tramos son idénticos en ambas encuestas
*!     (1 / 2-5 / 6-9 / 10-49 / 50-199 / 200+), así que se usan tal cual.
*!   · Ingreso: ingreso líquido de la ocupación principal corregido (`yoprcor_mn` en
*!     2000, `yoprcor` en 2022). NO se deflacta: todo se reporta en razones —respecto a
*!     la mediana del año y respecto a la línea de pobreza per cápita del año—, que es
*!     robusto al deflactor y evita discutir empalmes de IPC.

version 15
clear all

* ===========================================================================
* 1. Casen 2000
* ===========================================================================

* La base complementaria viene comprimida en el almacén; se descomprime junto al
* zip, que es donde corresponde: es el mismo dataset de origen, no material propio.
local c00_compl "$ALMACEN/Casen/2000/Base de Datos 2000 complementaria de ingresos Metodologia Actual.dta"
capture confirm file "`c00_compl'"
if _rc {
    display as text "Descomprimiendo la base complementaria de Casen 2000..."
    unzipfile "$ALMACEN/Casen/2000/BD_2000_complementaria_ingresos_Metodologia_Actual.dta.zip", ///
        replace
    * unzipfile deja el archivo en el directorio de trabajo; moverlo al almacén
    capture copy "Base de Datos 2000 complementaria de ingresos Metodologia Actual.dta" ///
        "`c00_compl'", replace
    capture erase "Base de Datos 2000 complementaria de ingresos Metodologia Actual.dta"
}
confirm file "`c00_compl'"

* -- 1a. Base principal: tamaño de establecimiento, contrato y cotización ----
use segmento folio o o9 o11 o13 o17 using "$D_CASEN00", clear
duplicates report segmento folio o
* Rama detallada del año (CIIU rev.2 a 4 dígitos). No es comparable con la de 2022,
* pero la descomposición de Theil se hace dentro de cada año, así que sirve igual y
* usa la clasificación más fina disponible en cada encuesta.
gen long rama_det = o9
drop o9
tempfile c00main
save "`c00main'"

* -- 1b. Base complementaria: ingresos y pobreza con metodología actual ------
use segmento folio o region expr sexo edad anoest condact ocupr ramar o10 ///
    yoprcor_mn ytrabcor_mn ypctotcor_mn lp_mn pobreza_mn ///
    using "`c00_compl'", clear

merge 1:1 segmento folio o using "`c00main'", keep(master match) nogenerate

gen int anio = 2000

* Condición de actividad, homogénea con 2022
gen byte ocupacion = .
replace ocupacion = 1 if condact == 1                    // ocupado
replace ocupacion = 2 if inlist(condact, 2, 3)           // desocupado
replace ocupacion = 3 if inrange(condact, 4, 13)         // inactivo

* Categoría ocupacional (códigos del proyecto, ver etiquetas al final)
gen byte categoria = .
replace categoria = 1 if o10 == 1                        // patrón o empleador
replace categoria = 2 if o10 == 2                        // cuenta propia
replace categoria = 3 if o10 == 3                        // asalariado sector público
replace categoria = 4 if o10 == 4                        // asalariado empresa pública
replace categoria = 5 if o10 == 5                        // asalariado sector privado
replace categoria = 6 if inlist(o10, 6, 7)               // servicio doméstico
replace categoria = 7 if o10 == 8                        // familiar no remunerado
replace categoria = 8 if o10 == 9                        // FF.AA. y del orden

* Tamaño del establecimiento: A..F -> 1..6, X -> perdido
gen byte tamano = .
replace tamano = 1 if o13 == "A"
replace tamano = 2 if o13 == "B"
replace tamano = 3 if o13 == "C"
replace tamano = 4 if o13 == "D"
replace tamano = 5 if o13 == "E"
replace tamano = 6 if o13 == "F"

* Rama: ya viene en las 9 divisiones CIIU rev.2
gen byte rama9 = ramar
replace rama9 = . if ramar == 0                          // no bien especificada

* Ocupación calificada: directivos, profesionales y técnicos (CIUO-88 grupos 1-3)
gen byte calificado = inlist(ocupr, 1, 2, 3)
replace calificado = . if missing(ocupr)

* Contrato y cotización previsional
gen byte contrato_d = .
replace contrato_d = 1 if inlist(o11, 1, 2, 3)
replace contrato_d = 0 if o11 == 4
gen byte cotiza_d = .
replace cotiza_d = 1 if inrange(o17, 1, 7)
replace cotiza_d = 0 if o17 == 8

rename anoest      escolaridad
rename yoprcor_mn  y_ocup_prin
rename ytrabcor_mn y_trabajo
rename ypctotcor_mn y_pc_hogar
rename lp_mn       linea_pobreza
gen byte pobre = (inlist(pobreza_mn, 1, 2)) if !missing(pobreza_mn)

keep anio region expr sexo edad escolaridad ocupacion categoria tamano rama9 ///
     rama_det calificado contrato_d cotiza_d y_ocup_prin y_trabajo y_pc_hogar ///
     linea_pobreza pobre
tempfile casen00
save "`casen00'"

* ===========================================================================
* 2. Casen 2022 y Casen 2024
*    Comparten cuestionario y codificación (rama1/rama4 CAENES, o15, o25, o16),
*    así que se procesan con el mismo código. La única diferencia es el nombre del
*    ingreso per cápita del hogar: `ypc` en 2022, `ypchtotcor` en 2024.
* ===========================================================================
tempfile casen_rec
local primero_rec = 1

foreach a in 2022 2024 {

    if `a' == 2022  local archivo "$D_CASEN22"
    if `a' == 2024  local archivo "$D_CASEN24"
    confirm file "`archivo'"

    * Dos nombres cambian entre encuestas y se resuelven leyendo el varlist antes
    * de cargar el archivo:
    *   · ingreso per cápita del hogar: `ypc` en 2022, `ypchtotcor` en 2024;
    *   · pobreza: Casen 2024 estrenó una línea nueva (canasta de la VIII EPF) que
    *     NO es comparable con 2000 ni 2022 —da 17,3% contra 4,9%—. La encuesta trae
    *     además `pobreza_2013` y `lp_2013`, que sí siguen la metodología vigente
    *     desde 2013, y son las que se usan acá.
    quietly describe using "`archivo'", varlist
    local vl " `r(varlist)' "

    local ypcvar "ypchtotcor"
    if strpos("`vl'", " ypc ") > 0  local ypcvar "ypc"

    local pobvar "pobreza"
    local lpvar  "lp"
    if strpos("`vl'", " pobreza_2013 ") > 0 {
        local pobvar "pobreza_2013"
        local lpvar  "lp_2013"
        display as text "Casen `a': se usa la serie de pobreza con metodología 2013, " ///
            "que es la comparable."
    }

    use region expr sexo edad esc activ o15 o25 o16 rama1 rama4 oficio1_08 ///
        contrato cotiza yoprcor ytrabajocor `lpvar' `pobvar' `ypcvar' ///
        using "`archivo'", clear
    rename `ypcvar' ypc
    rename `lpvar'  lp
    rename `pobvar' pobreza

    gen int anio = `a'

    gen byte ocupacion = activ                            // 1 ocupado 2 desoc 3 inactivo

    gen byte categoria = .
    replace categoria = 1 if o15 == 1
    replace categoria = 2 if o15 == 2
    replace categoria = 3 if o15 == 3
    replace categoria = 4 if o15 == 4
    replace categoria = 5 if o15 == 5
    replace categoria = 6 if inlist(o15, 6, 7)
    replace categoria = 7 if o15 == 9                     // ojo: acá el 9 es familiar
    replace categoria = 8 if o15 == 8                     // y el 8 es FF.AA.

    gen byte tamano = o25 if inrange(o25, 1, 6)

    * Rama: 21 secciones CIIU rev.4 -> 9 divisiones CIIU rev.2
    gen byte rama9 = .
    replace rama9 = 1 if rama1 == 1                                   // A
    replace rama9 = 2 if rama1 == 2                                   // B
    replace rama9 = 3 if rama1 == 3                                   // C
    replace rama9 = 4 if inlist(rama1, 4, 5)                          // D, E
    replace rama9 = 5 if rama1 == 6                                   // F
    replace rama9 = 6 if inlist(rama1, 7, 9)                          // G, I
    replace rama9 = 7 if inlist(rama1, 8, 10)                         // H, J
    replace rama9 = 8 if inlist(rama1, 11, 12, 13, 14)                // K, L, M, N
    replace rama9 = 9 if inrange(rama1, 15, 21)                       // O a U

    gen byte calificado = inlist(oficio1_08, 1, 2, 3)
    replace calificado = . if missing(oficio1_08) | oficio1_08 < 0

    * Rama detallada del año (clasificación CAENES de Casen)
    gen long rama_det = rama4 if rama4 > 0

    * Sección CIIU rev.4 (A-U). Es la llave con la que se pega la capa de
    * productividad del SII, que publica por rubro = sección. En 2000 no existe:
    * esa encuesta trae CIIU rev.2 y el SII arranca en 2005.
    gen byte seccion = rama1 if inrange(rama1, 1, 21)

    gen byte contrato_d = .
    replace contrato_d = 1 if contrato == 1
    replace contrato_d = 0 if contrato == 0
    gen byte cotiza_d = .
    replace cotiza_d = 1 if cotiza == 1
    replace cotiza_d = 0 if cotiza == 0

    * Registro en el SII: no existe en 2000; sirve para la definición OIT
    gen byte reg_sii = .
    replace reg_sii = 1 if o16 == 1
    replace reg_sii = 0 if o16 == 2

    rename esc         escolaridad
    rename yoprcor     y_ocup_prin
    rename ytrabajocor y_trabajo
    rename ypc         y_pc_hogar
    rename lp          linea_pobreza
    gen byte pobre = inlist(pobreza, 1, 2) if !missing(pobreza)

    keep anio region expr sexo edad escolaridad ocupacion categoria tamano rama9 ///
         rama_det seccion calificado contrato_d cotiza_d reg_sii y_ocup_prin ///
         y_trabajo y_pc_hogar linea_pobreza pobre

    if `primero_rec' == 1 {
        save "`casen_rec'", replace
        local primero_rec = 0
    }
    else {
        append using "`casen_rec'"
        save "`casen_rec'", replace
    }
}

use "`casen_rec'", clear

* ===========================================================================
* 3. Unir, etiquetar y validar
* ===========================================================================
append using "`casen00'"

keep if edad >= 15

label define ocuplbl 1 "Ocupado" 2 "Desocupado" 3 "Inactivo"
label values ocupacion ocuplbl

label define catlbl 1 "Patrón o empleador" 2 "Cuenta propia" ///
                    3 "Asalariado sector público" 4 "Asalariado empresa pública" ///
                    5 "Asalariado sector privado" 6 "Servicio doméstico" ///
                    7 "Familiar no remunerado" 8 "FF.AA. y del orden"
label values categoria catlbl

label define tamlbl 1 "1 persona" 2 "2 a 5" 3 "6 a 9" 4 "10 a 49" ///
                    5 "50 a 199" 6 "200 y más"
label values tamano tamlbl

label define ramalbl 1 "Agricultura, silvicultura y pesca" ///
                     2 "Minería" ///
                     3 "Manufactura" ///
                     4 "Electricidad, gas y agua" ///
                     5 "Construcción" ///
                     6 "Comercio, restaurantes y hoteles" ///
                     7 "Transporte y comunicaciones" ///
                     8 "Servicios financieros y a empresas" ///
                     9 "Servicios comunales, sociales y personales"
label values rama9 ramalbl

* Banda de empleo comparable con la ESI y con la capa de productividad del SII:
* 1 menos de 5 · 2 de 5 a 10 · 3 entre 11 y 49 · 4 entre 50 a 199 · 5 200 y más.
* Los seis tramos de Casen se colapsan a estos cinco.
gen byte banda = .
replace banda = 1 if inlist(tamano, 1, 2)      // 1 persona; 2 a 5
replace banda = 2 if tamano == 3               // 6 a 9
replace banda = 3 if tamano == 4               // 10 a 49
replace banda = 4 if tamano == 5               // 50 a 199
replace banda = 5 if tamano == 6               // 200 y más
label define bandalbl 1 "Menos de 5" 2 "De 5 a 10" 3 "Entre 11 y 49" ///
                      4 "Entre 50 y 199" 5 "200 y más"
label values banda bandalbl

label define seclbl 1 "A" 2 "B" 3 "C" 4 "D" 5 "E" 6 "F" 7 "G" 8 "H" 9 "I" 10 "J" ///
                    11 "K" 12 "L" 13 "M" 14 "N" 15 "O" 16 "P" 17 "Q" 18 "R" 19 "S" ///
                    20 "T" 21 "U"
label values seccion seclbl

* ---------------------------------------------------------------------------
* Estrato de productividad, en la tradición PREALC/CEPAL
*   bajo  = ocupados en establecimientos de hasta 5 personas, cuenta propia no
*           calificado, familiares no remunerados y servicio doméstico
*   medio = establecimientos de 6 a 49
*   alto  = establecimientos de 50 y más
* ---------------------------------------------------------------------------
gen byte estrato = .
replace estrato = 3 if tamano >= 5 & !missing(tamano)
replace estrato = 2 if inlist(tamano, 3, 4)
replace estrato = 1 if inlist(tamano, 1, 2)
replace estrato = 1 if categoria == 6                       // servicio doméstico
replace estrato = 1 if categoria == 7                       // familiar no remunerado
replace estrato = 1 if categoria == 2 & calificado == 0     // cuenta propia no calificado
replace estrato = . if ocupacion != 1
label define estlbl 1 "Baja productividad" 2 "Productividad media" 3 "Alta productividad"
label values estrato estlbl

* Informalidad comparable entre 2000 y 2022: sin cotización previsional
gen byte informal_prev = (cotiza_d == 0) if !missing(cotiza_d) & ocupacion == 1

* Informalidad en el sentido OIT: sólo calculable donde hay registro en el SII,
* es decir en las encuestas recientes, no en 2000
gen byte informal_oit = .
replace informal_oit = 0 if anio > 2000 & ocupacion == 1
replace informal_oit = 1 if anio > 2000 & ocupacion == 1 & cotiza_d == 0
replace informal_oit = 1 if anio > 2000 & ocupacion == 1 & categoria == 6 & cotiza_d == 0
replace informal_oit = 1 if anio > 2000 & ocupacion == 1 & categoria == 7
replace informal_oit = 1 if anio > 2000 & ocupacion == 1 & ///
                            inlist(categoria, 1, 2) & reg_sii == 0

* Ingreso relativo, libre de deflactor
gen double y_rel_lp = y_ocup_prin / linea_pobreza
replace y_ocup_prin = . if y_ocup_prin <= 0

compress
label data "Casen 2000, 2022 y 2024 armonizadas — heterogeneidad estructural"
save "$INTER/casen_armonizada.dta", replace

* ===========================================================================
* 4. Validación contra cifras oficiales publicadas
* ===========================================================================
display as text _n "{hline 70}"
display as text "VALIDACIÓN — comparar con las cifras publicadas por el MDSF"
display as text "{hline 70}"

foreach a in $ANIOS {
    quietly count if anio == `a'
    display as text _n "Casen `a' (N = " r(N) " personas de 15 y más)"
    quietly summarize pobre [aw = expr] if anio == `a'
    display as text "  Pobreza por ingresos (15+), metodología actual: " ///
        %5.1f 100*r(mean) "%"
    quietly summarize informal_prev [aw = expr] if anio == `a' & ocupacion == 1
    display as text "  Ocupados que no cotizan en previsión:            " ///
        %5.1f 100*r(mean) "%"
    quietly count if anio == `a' & ocupacion == 1
    quietly summarize expr if anio == `a' & ocupacion == 1
    display as text "  Ocupados expandidos:                             " ///
        %12.0fc r(sum)
    quietly summarize estrato if anio == `a' & ocupacion == 1
    display as text "  Ocupados con estrato asignado:                   " ///
        %12.0fc r(N)
}

foreach a in $ANIOS {
    quietly summarize informal_oit [aw = expr] if anio == `a' & ocupacion == 1
    if r(N) > 0 {
        display as text "  Informalidad OIT `a' (referencia ENE ~27-28%):    " ///
            %5.1f 100*r(mean) "%"
    }
}

* Sin estrato asignado no hay bloque B; avisar si la pérdida es grande
foreach a in $ANIOS {
    quietly count if anio == `a' & ocupacion == 1
    local na = r(N)
    quietly count if anio == `a' & ocupacion == 1 & missing(estrato)
    if `na' > 0 & r(N)/`na' > 0.10 {
        display as error "Atención: más del 10% de los ocupados de `a' quedó sin estrato."
    }
}

display as text _n "== Base armonizada guardada en $INTER/casen_armonizada.dta =="
