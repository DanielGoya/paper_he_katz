*! 04_casen_cuatro_chiles.do
*! Bloque C — Los «cuatro Chiles» de Katz, con números (Casen 2000 vs 2022)
*!
*! Katz describe cuatro «países» que conviven dentro de Chile y no dialogan: el
*! moderno que se acerca a la frontera, el de recursos naturales, el rezagado y el
*! excluido. Es una taxonomía de PERSONAS, no de sectores: por eso ninguna matriz
*! insumo-producto ni ningún análisis de conglomerados sectoriales puede contarla.
*! Acá se la operacionaliza sobre los microdatos y se mide cuánta gente hay en cada
*! segmento y cómo cambió entre 2000 y 2022.
*!
*! ES UNA TAXONOMÍA, NO UNA ESTIMACIÓN. Los cortes son decisiones, no parámetros
*! estimados, y por eso la sensibilidad va publicada junto al resultado principal.
*!
*! Árbol de decisión (se aplica EN ESTE ORDEN, sobre la población de 15 años y más):
*!   1. En situación de exclusión y sin empleo formal        -> Chile excluido
*!   2. Ocupado formal en la cadena de recursos naturales,
*!      en establecimiento sobre el corte de tamaño          -> Chile de recursos naturales
*!   3. Ocupado formal sobre el corte de tamaño,
*!      fuera de la cadena de RRNN                           -> Chile moderno
*!   4. Cualquier otro ocupado                               -> Chile rezagado
*!   5. Resto                                                -> Fuera del mercado laboral
*!
*! El quinto grupo existe porque los cuatro de Katz no cubren a toda la población de
*! 15 y más (jubilados, estudiantes, inactivos no pobres). Omitirlo sería inflar los
*! otros cuatro.
*!
*! Tres perillas, con la sensibilidad publicada en T_C2:
*!   · corte de tamaño del establecimiento para «moderno» y «RRNN» (6+ / 50+ / 2+);
*!   · exigir o no ocupación calificada (CIUO grupos 1-3) para «moderno»;
*!   · exclusión ABSOLUTA (pobreza por ingresos con la metodología actual) o
*!     RELATIVA (quintil más bajo de ingreso per cápita del hogar del propio año).
*!     La distinción no es técnica: la pobreza absoluta chilena se desplomó entre
*!     2000 y 2022 y la posición relativa no, así que el tamaño del «Chile excluido»
*!     depende por completo de cuál de las dos se mire. Se reportan ambas.

version 15
clear all

use "$INTER/casen_armonizada.dta", clear

* ===========================================================================
* 1. Cadena de recursos naturales
*    2000: CIIU rev.2 · 2022: CIIU rev.4. Se identifica por división, que es el
*    nivel donde ambas revisiones dicen lo mismo.
* ===========================================================================
gen int div_det = floor(rama_det/100)
gen int gru_det = floor(rama_det/10)

gen byte cadena_rrnn = 0

* --- 2000, CIIU rev.2 ---
replace cadena_rrnn = 1 if anio == 2000 & inlist(div_det, 11, 12, 13)          // agro, silvicultura, pesca
replace cadena_rrnn = 1 if anio == 2000 & inlist(div_det, 21, 22, 23, 29)      // minería
replace cadena_rrnn = 1 if anio == 2000 & div_det == 31                        // alimentos, bebidas, tabaco
replace cadena_rrnn = 1 if anio == 2000 & gru_det == 331                       // madera (excluye muebles)
replace cadena_rrnn = 1 if anio == 2000 & gru_det == 341                       // papel (excluye imprenta)
replace cadena_rrnn = 1 if anio == 2000 & div_det == 37                        // metales básicos

* --- 2022, CIIU rev.4 ---
replace cadena_rrnn = 1 if anio == 2022 & inrange(div_det, 1, 3)               // agro, silvicultura, pesca
replace cadena_rrnn = 1 if anio == 2022 & inrange(div_det, 4, 9)               // minería
replace cadena_rrnn = 1 if anio == 2022 & inrange(div_det, 10, 12)             // alimentos, bebidas, tabaco
replace cadena_rrnn = 1 if anio == 2022 & div_det == 16                        // madera
replace cadena_rrnn = 1 if anio == 2022 & div_det == 17                        // papel
replace cadena_rrnn = 1 if anio == 2022 & div_det == 24                        // metales básicos

replace cadena_rrnn = . if missing(rama_det) | rama_det <= 0

* Chequeo: la cadena de RRNN tiene que estar contenida en las ramas 1, 2 y 3
quietly count if cadena_rrnn == 1 & !inlist(rama9, 1, 2, 3)
if r(N) > 0 {
    display as error "Hay " r(N) " casos marcados como cadena de RRNN fuera de las ramas 1-3."
    exit 459
}
display as text "Chequeo OK: la cadena de RRNN queda dentro de agro, minería y manufactura."

* ===========================================================================
* 2. Los cuatro Chiles
* ===========================================================================
gen byte formal = (cotiza_d == 1) if !missing(cotiza_d)
replace formal = 0 if ocupacion == 1 & missing(cotiza_d)

* Exclusión relativa: quintil más bajo del ingreso per cápita del hogar, del propio año.
* Ojo: `summarize, detail` no devuelve p20, así que el corte se saca con _pctile.
gen byte q1_pc = .
foreach a in 2000 2022 {
    quietly _pctile y_pc_hogar [aw = expr] if anio == `a' & !missing(y_pc_hogar), p(20)
    local corte20 = r(r1)
    quietly replace q1_pc = (y_pc_hogar <= `corte20') if anio == `a' & !missing(y_pc_hogar)
    quietly summarize q1_pc [aw = expr] if anio == `a'
    display as text "Quintil 1 de ingreso per cápita, `a': corte = " %12.0fc `corte20' ///
        "; cubre el " %4.1f 100*r(mean) "% de la población de 15 y más"
    if abs(r(mean) - 0.20) > 0.03 {
        display as error "El quintil 1 de `a' no cubre ~20% de la población."
        exit 459
    }
}

capture program drop clasificar
program define clasificar
    args nombre corte_tam exigir_calif excl_rel
    quietly {
        capture drop `nombre'
        gen byte `nombre' = .

        * Criterio de exclusión: absoluto (pobreza por ingresos) o relativo (quintil 1)
        tempvar excl
        gen byte `excl' = 0
        if `excl_rel' == 1 {
            replace `excl' = (q1_pc == 1)
        }
        if `excl_rel' == 0 {
            replace `excl' = (pobre == 1)
        }

        * Condición de pertenencia al segmento «con inserción productiva formal»
        tempvar nucleo
        gen byte `nucleo' = (ocupacion == 1 & formal == 1 & ///
                             tamano >= `corte_tam' & !missing(tamano))
        if `exigir_calif' == 1  replace `nucleo' = 0 if calificado != 1

        * 1. Excluido
        replace `nombre' = 4 if `excl' == 1 & `nucleo' == 0
        * 2. Recursos naturales
        replace `nombre' = 2 if missing(`nombre') & `nucleo' == 1 & cadena_rrnn == 1
        * 3. Moderno
        replace `nombre' = 1 if missing(`nombre') & `nucleo' == 1
        * 4. Rezagado
        replace `nombre' = 3 if missing(`nombre') & ocupacion == 1
        * 5. Fuera del mercado laboral
        replace `nombre' = 5 if missing(`nombre')
    }
end

*            nombre     tamaño  calif  exclusión relativa
clasificar   chile         3       0        0     // principal
clasificar   chile_s1      5       1        0     // estricto: 50+, sólo calificados
clasificar   chile_s2      2       0        0     // amplio: 2+
clasificar   chile_s3      3       0        1     // principal con exclusión relativa

label define chilelbl 1 "Chile moderno" 2 "Chile de recursos naturales" ///
                      3 "Chile rezagado" 4 "Chile excluido" ///
                      5 "Fuera del mercado laboral"
foreach v in chile chile_s1 chile_s2 chile_s3 {
    label values `v' chilelbl
}

save "$INTER/casen_cuatro_chiles.dta", replace

* ===========================================================================
* 3. Tabla central: tamaño y características de cada Chile
* ===========================================================================
use "$INTER/casen_cuatro_chiles.dta", clear

gen byte mujer  = (sexo == 2) if !missing(sexo)
gen double y_lp = y_ocup_prin / linea_pobreza

preserve
    collapse (sum) pob = expr, by(anio chile)
    bysort anio: egen double tot = total(pob)
    gen double pct_pob15 = 100 * pob / tot
    keep anio chile pob pct_pob15
    tempfile p1
    save "`p1'"
restore

preserve
    keep if ocupacion == 1
    collapse (sum) ocup = expr, by(anio chile)
    bysort anio: egen double tot = total(ocup)
    gen double pct_ocupados = 100 * ocup / tot
    keep anio chile ocup pct_ocupados
    tempfile p2
    save "`p2'"
restore

preserve
    keep if ocupacion == 1 & !missing(y_ocup_prin)
    gen double masa = expr * y_ocup_prin
    collapse (sum) masa, by(anio chile)
    bysort anio: egen double tot = total(masa)
    gen double pct_masa = 100 * masa / tot
    keep anio chile pct_masa
    tempfile p3
    save "`p3'"
restore

collapse (median) med_lp = y_lp ///
         (mean) escolaridad = escolaridad edad = edad pct_mujer = mujer ///
                pct_informal = informal_prev pct_pobre = pobre ///
         [aw = expr], by(anio chile)

merge 1:1 anio chile using "`p1'", nogenerate
merge 1:1 anio chile using "`p2'", nogenerate
merge 1:1 anio chile using "`p3'", nogenerate

foreach v in pct_mujer pct_informal pct_pobre {
    replace `v' = 100 * `v'
}

label variable pob          "Personas de 15 y más (expandidas)"
label variable pct_pob15    "% de la población de 15 y más"
label variable ocup         "Ocupados (expandidos)"
label variable pct_ocupados "% de los ocupados"
label variable pct_masa     "% de la masa de ingresos laborales"
label variable med_lp       "Ingreso mediano de la ocupación principal / línea de pobreza"
label variable escolaridad  "Años de escolaridad (promedio)"
label variable edad         "Edad promedio"
label variable pct_mujer    "% mujeres"
label variable pct_informal "% sin cotización previsional (ocupados)"
label variable pct_pobre    "% en situación de pobreza por ingresos"

order anio chile pob pct_pob15 ocup pct_ocupados pct_masa med_lp escolaridad ///
      edad pct_mujer pct_informal pct_pobre
sort anio chile
save "$INTER/cuatro_chiles_resumen.dta", replace
export excel using "$OUT/2026.08.10 T_C1 los cuatro Chiles.xlsx", ///
    firstrow(varlabels) replace

list anio chile pct_pob15 pct_ocupados pct_masa med_lp, noobs sepby(anio) abbreviate(14)

* ===========================================================================
* 4. Sensibilidad a los cortes
* ===========================================================================
use "$INTER/casen_cuatro_chiles.dta", clear
tempfile sens
local primero = 1
foreach v in chile chile_s1 chile_s2 chile_s3 {
    preserve
        collapse (sum) pob = expr, by(anio `v')
        rename `v' segmento
        bysort anio: egen double tot = total(pob)
        gen double pct = 100 * pob / tot
        gen str10 corte = "`v'"
        keep anio segmento corte pct
        if `primero' == 1 {
            save "`sens'", replace
            local primero = 0
        }
        else {
            append using "`sens'"
            save "`sens'", replace
        }
    restore
}
use "`sens'", clear
gen byte icorte = .
replace icorte = 1 if corte == "chile"
replace icorte = 2 if corte == "chile_s1"
replace icorte = 3 if corte == "chile_s2"
replace icorte = 4 if corte == "chile_s3"
drop corte
label values segmento chilelbl
reshape wide pct, i(anio segmento) j(icorte)
label variable pct1 "% principal (6+, exclusión absoluta)"
label variable pct2 "% estricto (50+, sólo calificados)"
label variable pct3 "% amplio (2+)"
label variable pct4 "% principal con exclusión relativa (quintil 1)"
sort anio segmento
export excel using "$OUT/2026.08.10 T_C2 sensibilidad de los cuatro Chiles.xlsx", ///
    firstrow(varlabels) replace

* ===========================================================================
* 5. Figuras
* ===========================================================================
use "$INTER/cuatro_chiles_resumen.dta", clear

graph bar (asis) pct_pob15, over(chile, label(labsize(vsmall) angle(25))) over(anio) ///
    ytitle("% de la población de 15 años y más") ///
    blabel(bar, format(%4.1f) size(vsmall)) legend(off) ///
    note("Fuente: elaboración propia con Casen 2000 y 2022. Clasificación construida sobre" ///
         "los cuatro «países» que describe Katz; ver el árbol de decisión en el do-file y la" ///
         "tabla de sensibilidad T_C2.", size(vsmall))
graph export "$OUT/F_C1 poblacion en cada uno de los cuatro Chiles.png", replace width(2200)
graph export "$OUT/F_C1 poblacion en cada uno de los cuatro Chiles.pdf", replace

keep if chile <= 4
graph bar (asis) pct_ocupados pct_masa, over(chile, label(labsize(vsmall) angle(25))) ///
    over(anio) ///
    legend(order(1 "% de los ocupados" 2 "% de la masa de ingresos laborales") ///
           rows(1) size(small) region(lstyle(none))) ///
    ytitle("Porcentaje") ///
    note("Fuente: elaboración propia con Casen 2000 y 2022.", size(vsmall))
graph export "$OUT/F_C2 empleo e ingresos por segmento.png", replace width(2200)
graph export "$OUT/F_C2 empleo e ingresos por segmento.pdf", replace

* ===========================================================================
* 6. Distribución regional del Chile de recursos naturales y del excluido
* ===========================================================================
use "$INTER/casen_cuatro_chiles.dta", clear
collapse (sum) pob = expr, by(anio region chile)
bysort anio region: egen double tot = total(pob)
gen double pct = 100 * pob / tot
keep anio region chile pct
reshape wide pct, i(anio region) j(chile)
label variable pct1 "% Chile moderno"
label variable pct2 "% Chile de recursos naturales"
label variable pct3 "% Chile rezagado"
label variable pct4 "% Chile excluido"
label variable pct5 "% fuera del mercado laboral"
sort anio region
export excel using "$OUT/2026.08.10 T_C3 los cuatro Chiles por region.xlsx", ///
    firstrow(varlabels) replace

display as text _n "== Bloque C terminado =="
