*! 03_casen_estratos.do
*! Bloque B — Estratos de productividad al modo PREALC/CEPAL, Casen 2000 vs 2022
*!
*! La heterogeneidad estructural, tal como la definió el estructuralismo
*! latinoamericano (Pinto, 1970; PREALC), no es una propiedad de los sectores sino de
*! los ESTRATOS de ocupados: conviven en la misma economía —y con frecuencia en la
*! misma rama— segmentos con productividades que difieren en un orden de magnitud.
*! Este bloque mide eso con microdatos, que es justamente lo que un análisis de
*! conglomerados sectoriales no puede ver.
*!
*! Advertencia de medición: las encuestas de hogares no observan producto, así que el
*! ingreso laboral opera como proxy de la productividad. Es el proxy que usa la propia
*! CEPAL en su serie de heterogeneidad estructural, y hay que declararlo.
*!
*! Produce:
*!   T_B1  caracterización de los tres estratos, 2000 y 2022
*!   T_B2  composición de cada rama por estrato
*!   T_B3  descomposición de Theil del ingreso laboral: entre y dentro de rama
*!   F_B1  empleo e ingreso por estrato
*!   F_B2  brecha de ingreso respecto al estrato alto
*!   F_B3  cuánto de la desigualdad de ingresos laborales explica la rama

version 15
clear all

* ===========================================================================
* 0. Programa auxiliar: descomposición de Theil-T con ponderadores
*    T = T_entre + T_dentro
*    T_entre  = SUM_g s_g * ln(ybar_g / ybar)
*    T_dentro = SUM_g s_g * T_g
*    con s_g = participación del grupo g en el ingreso total
* ===========================================================================
capture program drop theildec
program define theildec, rclass
    syntax varname(numeric) [if] [in], WVar(varname numeric) GVar(varname numeric)

    marksample touse
    markout `touse' `wvar' `gvar'
    quietly replace `touse' = 0 if `varlist' <= 0 | missing(`varlist')

    tempvar y w g wy
    quietly gen double `y' = `varlist' if `touse'
    quietly gen double `w' = `wvar'   if `touse'
    quietly gen double `g' = `gvar'   if `touse'
    quietly gen double `wy' = `w' * `y'

    quietly summarize `w' if `touse', meanonly
    local W = r(sum)
    quietly summarize `wy' if `touse', meanonly
    local Y = r(sum)
    local ybar = `Y' / `W'

    * Theil total
    tempvar contrib
    quietly gen double `contrib' = `w' * (`y'/`ybar') * ln(`y'/`ybar') if `touse'
    quietly summarize `contrib' if `touse', meanonly
    local T = r(sum) / `W'

    * Componente entre grupos
    tempvar gw gy
    quietly egen double `gw' = total(`w') if `touse', by(`g')
    quietly egen double `gy' = total(`wy') if `touse', by(`g')

    preserve
        quietly keep if `touse'
        quietly bysort `g': keep if _n == 1
        quietly gen double sg    = `gy' / `Y'
        quietly gen double ybarg = `gy' / `gw'
        quietly gen double aux   = sg * ln(ybarg / `ybar')
        quietly summarize aux, meanonly
        local TB = r(sum)
        quietly count
        local G = r(N)
    restore

    local TW = `T' - `TB'
    return scalar theil       = `T'
    return scalar theil_entre = `TB'
    return scalar theil_dentro= `TW'
    return scalar share_entre = `TB' / `T'
    return scalar grupos      = `G'
end

* ===========================================================================
* 1. Caracterización de los estratos
* ===========================================================================
use "$INTER/casen_armonizada.dta", clear
keep if ocupacion == 1 & !missing(estrato)

gen byte mujer   = (sexo == 2) if !missing(sexo)
gen double y_lp  = y_ocup_prin / linea_pobreza   // ingreso en múltiplos de la línea

* Mediana ponderada del ingreso, por año, para expresar todo en relativos
gen double y_med_anio = .
foreach a in 2000 2022 {
    quietly summarize y_ocup_prin [aw = expr] if anio == `a', detail
    quietly replace y_med_anio = r(p50) if anio == `a'
}
gen double y_rel_med = y_ocup_prin / y_med_anio

preserve
    collapse (sum) empleo = expr, by(anio estrato)
    bysort anio: egen double tot = total(empleo)
    gen double pct_empleo = 100 * empleo / tot
    keep anio estrato pct_empleo
    tempfile pemp
    save "`pemp'"
restore

preserve
    keep if !missing(y_ocup_prin)
    gen double masa = expr * y_ocup_prin
    collapse (sum) masa, by(anio estrato)
    bysort anio: egen double tot = total(masa)
    gen double pct_ingreso = 100 * masa / tot
    keep anio estrato pct_ingreso
    tempfile ping
    save "`ping'"
restore

collapse (median) med_rel = y_rel_med med_lp = y_lp ///
         (mean) escolaridad = escolaridad pct_contrato = contrato_d ///
                pct_cotiza = cotiza_d pct_mujer = mujer ///
         [aw = expr], by(anio estrato)

merge 1:1 anio estrato using "`pemp'", nogenerate
merge 1:1 anio estrato using "`ping'", nogenerate

foreach v in pct_contrato pct_cotiza pct_mujer {
    replace `v' = 100 * `v'
}

* Brecha respecto al estrato de alta productividad
bysort anio (estrato): gen double ref = med_rel[_N]
gen double brecha_alto = 100 * med_rel / ref
drop ref

label variable pct_empleo    "% del empleo"
label variable pct_ingreso   "% de la masa de ingresos laborales"
label variable med_rel       "Ingreso mediano / mediana del año"
label variable med_lp        "Ingreso mediano / línea de pobreza p.c."
label variable brecha_alto   "Ingreso mediano como % del estrato alto"
label variable escolaridad   "Años de escolaridad (promedio)"
label variable pct_contrato  "% con contrato escrito"
label variable pct_cotiza    "% que cotiza en previsión"
label variable pct_mujer     "% mujeres"

order anio estrato pct_empleo pct_ingreso med_rel med_lp brecha_alto ///
      escolaridad pct_contrato pct_cotiza pct_mujer
sort anio estrato
save "$INTER/estratos_resumen.dta", replace
export excel using "$OUT/2026.08.10 T_B1 estratos de productividad.xlsx", ///
    firstrow(varlabels) replace

* ---- Figura B1: empleo e ingreso por estrato -------------------------------
use "$INTER/estratos_resumen.dta", clear
gen byte grupo = anio == 2022
graph bar (asis) pct_empleo pct_ingreso, over(estrato, label(labsize(small))) ///
    over(anio) ///
    legend(order(1 "% del empleo" 2 "% de la masa de ingresos laborales") ///
           rows(1) size(small) region(lstyle(none))) ///
    ytitle("Porcentaje") ///
    note("Fuente: elaboración propia con Casen 2000 (metodología de ingresos actual) y Casen 2022." ///
         "Estratos en la tradición PREALC/CEPAL: bajo = hasta 5 ocupados, cuenta propia no calificado," ///
         "servicio doméstico y familiares no remunerados; medio = 6 a 49; alto = 50 y más.", size(vsmall))
graph export "$OUT/F_B1 empleo e ingreso por estrato.png", replace width(2200)
graph export "$OUT/F_B1 empleo e ingreso por estrato.pdf", replace

* ---- Figura B2: brecha de ingreso respecto al estrato alto -----------------
graph bar (asis) brecha_alto, over(estrato, label(labsize(small))) over(anio) ///
    ytitle("Ingreso mediano de la ocupación principal" "(estrato de alta productividad = 100)") ///
    blabel(bar, format(%4.0f) size(small)) ///
    legend(off) ///
    note("Fuente: elaboración propia con Casen 2000 y 2022.", size(vsmall))
graph export "$OUT/F_B2 brecha de ingreso por estrato.png", replace width(2200)
graph export "$OUT/F_B2 brecha de ingreso por estrato.pdf", replace

* ===========================================================================
* 2. Composición de cada rama por estrato: la heterogeneidad vive DENTRO
* ===========================================================================
use "$INTER/casen_armonizada.dta", clear
keep if ocupacion == 1 & !missing(estrato) & !missing(rama9)

collapse (sum) empleo = expr, by(anio rama9 estrato)
bysort anio rama9: egen double tot = total(empleo)
gen double pct = 100 * empleo / tot
keep anio rama9 estrato pct
reshape wide pct, i(anio rama9) j(estrato)
label variable pct1 "% en estrato bajo"
label variable pct2 "% en estrato medio"
label variable pct3 "% en estrato alto"
sort anio rama9
export excel using "$OUT/2026.08.10 T_B2 composicion de cada rama por estrato.xlsx", ///
    firstrow(varlabels) replace

* ===========================================================================
* 3. Descomposición de Theil del ingreso laboral
*    Tres particiones, de la más gruesa a la más fina:
*      (a) 9 divisiones CIIU        — el nivel al que son comparables 2000 y 2022
*      (b) rama detallada del año   — 4 dígitos, la clasificación más fina disponible
*      (c) estrato de productividad — 3 grupos
*    Si ni siquiera la partición más fina por rama explica gran parte de la
*    desigualdad, entonces la HE es sobre todo un fenómeno intra-sectorial.
* ===========================================================================
use "$INTER/casen_armonizada.dta", clear
keep if ocupacion == 1 & y_ocup_prin > 0 & !missing(y_ocup_prin)

tempname res
postfile `res' int anio str28 particion double(theil entre dentro share_entre) ///
    int grupos using "$INTER/theil_dec.dta", replace

foreach a in 2000 2022 {
    theildec y_ocup_prin if anio == `a', wvar(expr) gvar(rama9)
    post `res' (`a') ("Rama: 9 divisiones CIIU") (r(theil)) (r(theil_entre)) ///
        (r(theil_dentro)) (100*r(share_entre)) (r(grupos))

    theildec y_ocup_prin if anio == `a', wvar(expr) gvar(rama_det)
    post `res' (`a') ("Rama: 4 dígitos del año") (r(theil)) (r(theil_entre)) ///
        (r(theil_dentro)) (100*r(share_entre)) (r(grupos))

    theildec y_ocup_prin if anio == `a', wvar(expr) gvar(estrato)
    post `res' (`a') ("Estrato de productividad") (r(theil)) (r(theil_entre)) ///
        (r(theil_dentro)) (100*r(share_entre)) (r(grupos))

    * Partición cruzada rama9 x estrato: el techo de lo que ambas cosas juntas explican
    quietly egen long _cruce = group(rama9 estrato) if anio == `a'
    theildec y_ocup_prin if anio == `a', wvar(expr) gvar(_cruce)
    post `res' (`a') ("Rama 9 x estrato") (r(theil)) (r(theil_entre)) ///
        (r(theil_dentro)) (100*r(share_entre)) (r(grupos))
    drop _cruce
}
postclose `res'

use "$INTER/theil_dec.dta", clear
label variable theil       "Theil total"
label variable entre       "Componente entre grupos"
label variable dentro      "Componente dentro de grupos"
label variable share_entre "% de la desigualdad explicada entre grupos"
label variable grupos      "Número de grupos"
list, noobs sepby(anio) abbreviate(14)
export excel using "$OUT/2026.08.10 T_B3 descomposicion Theil del ingreso laboral.xlsx", ///
    firstrow(varlabels) replace

* La identidad de la descomposición tiene que cerrar
gen double chk = theil - entre - dentro
quietly summarize chk
if abs(r(max)) > 1e-8 | abs(r(min)) > 1e-8 {
    display as error "La descomposición de Theil no cierra."
    exit 459
}
display as text "Chequeo OK: T = T_entre + T_dentro en todas las particiones."

* ---- Figura B3 --------------------------------------------------------------
keep if inlist(particion, "Rama: 9 divisiones CIIU", "Rama: 4 dígitos del año", ///
                          "Estrato de productividad", "Rama 9 x estrato")
gen byte part = .
replace part = 1 if particion == "Rama: 9 divisiones CIIU"
replace part = 2 if particion == "Rama: 4 dígitos del año"
replace part = 3 if particion == "Estrato de productividad"
replace part = 4 if particion == "Rama 9 x estrato"
label define partlbl 1 "Rama (9 divisiones)" 2 "Rama (4 dígitos)" ///
                     3 "Estrato de productividad" 4 "Rama x estrato"
label values part partlbl

graph bar (asis) share_entre, over(part, label(labsize(small) angle(30))) over(anio) ///
    ytitle("% de la desigualdad de ingresos laborales" "explicada por diferencias ENTRE grupos") ///
    blabel(bar, format(%4.1f) size(small)) legend(off) ///
    note("Fuente: elaboración propia con Casen 2000 y 2022. Descomposición del índice de Theil-T" ///
         "del ingreso de la ocupación principal entre ocupados con ingreso positivo." ///
         "El resto —la mayor parte— es desigualdad DENTRO de cada grupo.", size(vsmall))
graph export "$OUT/F_B3 desigualdad entre vs dentro de grupos.png", replace width(2200)
graph export "$OUT/F_B3 desigualdad entre vs dentro de grupos.pdf", replace

display as text _n "== Bloque B terminado =="
