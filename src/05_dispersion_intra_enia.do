*! 05_dispersion_intra_enia.do
*! Bloque E — Dispersión de productividad DENTRO de cada rama manufacturera
*!
*! Fuente: ENIA (Encuesta Nacional Industrial Anual, INE), panel de seguimiento de
*!         establecimientos 1995-2015. Cubre plantas de 10 y más ocupados.
*!
*! Por qué importa: el bloque B mostró con Casen que el grueso de la dispersión de
*! ingresos laborales vive DENTRO de las ramas. Acá se comprueba lo mismo con
*! productividad medida de verdad —valor agregado por ocupado a nivel de planta—, que
*! es el objeto del que habla Katz cuando contrasta firmas «grandes» con pymes.
*!
*! Advertencia: la ENIA excluye a los establecimientos de menos de 10 ocupados, o sea
*! justamente el estrato de baja productividad. Todo lo que se mida acá es una COTA
*! INFERIOR de la heterogeneidad manufacturera real.
*!
*! Produce:
*!   T_E1  dispersión intra-rama de la productividad, años seleccionados
*!   T_E2  descomposición entre/dentro de rama a 3 dígitos
*!   F_E1  evolución de la razón p90/p10 y del componente entre ramas

version 15
clear all

capture confirm file "$D_ENIA"
if _rc {
    display as error "No está la ENIA en $D_ENIA — se salta el bloque E."
    exit 0
}

use anio ciiu3 ciiu4 a004 b021 k005 estrato using "$D_ENIA", clear

* ---------------------------------------------------------------------------
* 1. Moneda: desde 2008 algunas plantas declaran en dólares o euros y el código
*    de `a004` cambia de un año a otro. Se conserva la categoría modal de cada
*    año, que es el peso; las demás distorsionarían la cola baja.
* ---------------------------------------------------------------------------
bysort anio a004: gen long _n_cat = _N
bysort anio (_n_cat): gen byte _modal = (_n_cat == _n_cat[_N])
quietly count if _modal == 0
display as text "Plantas descartadas por declarar en otra moneda: " r(N)
keep if _modal == 1
drop _n_cat _modal

* ---------------------------------------------------------------------------
* 2. Productividad laboral por planta
* ---------------------------------------------------------------------------
gen double prod = k005 / b021
drop if missing(prod) | prod <= 0 | b021 <= 0

* Rama a 3 dígitos: CIIU rev.3 hasta 2012, rev.4 desde 2013. No son la misma
* clasificación, así que la comparación de niveles se hace dentro de cada régimen y
* la serie completa se lee como indicativa, no como empalme.
gen long rama3 = ciiu3
replace rama3 = ciiu4 if anio >= 2013 & !missing(ciiu4)
drop if missing(rama3)

* Sólo ramas con al menos 20 plantas en el año, para que los percentiles signifiquen algo
bysort anio rama3: gen long n_plantas = _N
keep if n_plantas >= 20

* Recorte del 1% en cada cola DENTRO de cada rama-año. El valor agregado neto de la
* ENIA se acerca a cero en unas pocas plantas y eso hace estallar la cola baja; sin
* recortar, la razón p90/p10 salta de 12 a 57 y de vuelta a 10 sin que pase nada real.
bysort anio rama3: egen double _p01 = pctile(prod), p(1)
bysort anio rama3: egen double _p99 = pctile(prod), p(99)
quietly count
local antes = r(N)
drop if prod < _p01 | prod > _p99
quietly count
display as text "Recorte al 1% por rama-año: " `antes'-r(N) " plantas de `antes'"
drop _p01 _p99

* Metales básicos: es la refinación de cobre, o sea la renta del recurso otra vez.
* Igual que en el bloque A, todo se reporta con y sin ella.
gen byte metales_basicos = 0
replace metales_basicos = 1 if anio <= 2012 & inrange(rama3, 270, 279)   // CIIU rev.3 27
replace metales_basicos = 1 if anio >= 2013 & inrange(rama3, 240, 249)   // CIIU rev.4 24

gen double lprod = ln(prod)

* ---------------------------------------------------------------------------
* 3. Dispersión intra-rama: p90/p10 y desviación estándar del log
* ---------------------------------------------------------------------------
preserve
    collapse (p90) p90 = prod (p10) p10 = prod (sd) sd_lprod = lprod ///
             (count) n = prod (sum) emp = b021, by(anio rama3)
    gen double ratio_9010 = p90 / p10

    * Resumen por año. La razón p90/p10 se reporta como MEDIANA entre ramas: el
    * promedio ponderado lo domina la refinación de cobre en los años del boom y salta
    * de 12 a 55 sin que cambie nada estructural. La desviación estándar del log sí es
    * estable y es la medida que se usa en el texto.
    tempfile porrama med9010
    save "`porrama'"
    collapse (median) ratio_9010, by(anio)
    save "`med9010'"
    use "`porrama'", clear
    collapse (mean) sd_lprod [aw = emp], by(anio)
    merge 1:1 anio using "`med9010'", nogenerate
    label variable ratio_9010 "Razón p90/p10 de la productividad, mediana entre ramas"
    label variable sd_lprod   "Desv. estándar del log de la productividad, intra-rama"
    save "$INTER/enia_dispersion.dta", replace
    export excel using "$OUT/2026.08.10 T_E1 dispersion intra-rama en manufactura.xlsx", ///
        firstrow(varlabels) replace
restore

* ---------------------------------------------------------------------------
* 4. Descomposición de Theil de la productividad entre y dentro de ramas
*    Ponderada por empleo de la planta, que es la convención en esta literatura.
* ---------------------------------------------------------------------------
tempname res
postfile `res' int anio byte sin_metales double(theil entre dentro share_entre) ///
    int ramas using "$INTER/enia_theil.dta", replace

levelsof anio, local(anios)
foreach a of local anios {
  forvalues sm = 0/1 {
    preserve
        quietly keep if anio == `a'
        if `sm' == 1  quietly drop if metales_basicos == 1
        quietly summarize b021, meanonly
        local L = r(sum)
        quietly gen double va = prod * b021
        quietly summarize va, meanonly
        local VA = r(sum)
        local pagg = `VA' / `L'

        quietly gen double contrib = b021 * (prod/`pagg') * ln(prod/`pagg')
        quietly summarize contrib, meanonly
        local T = r(sum) / `L'

        quietly collapse (sum) va b021, by(rama3)
        quietly gen double sg    = va / `VA'
        quietly gen double ybarg = va / b021
        quietly gen double aux   = sg * ln(ybarg / `pagg')
        quietly summarize aux, meanonly
        local TB = r(sum)
        quietly count
        local G = r(N)

        post `res' (`a') (`sm') (`T') (`TB') (`T'-`TB') (100*`TB'/`T') (`G')
    restore
  }
}
postclose `res'

use "$INTER/enia_theil.dta", clear
label define smlbl 0 "Toda la manufactura" 1 "Sin metales básicos"
label values sin_metales smlbl
label variable sin_metales "Cobertura"
label variable theil       "Theil de la productividad entre plantas"
label variable entre       "Componente entre ramas (3 dígitos)"
label variable dentro      "Componente dentro de ramas"
label variable share_entre "% explicado entre ramas"
label variable ramas       "Número de ramas"
list, noobs abbreviate(12)
export excel using "$OUT/2026.08.10 T_E2 Theil de productividad en manufactura.xlsx", ///
    firstrow(varlabels) replace

* ---------------------------------------------------------------------------
* 5. Figura E1
* ---------------------------------------------------------------------------
keep if sin_metales == 1
merge 1:1 anio using "$INTER/enia_dispersion.dta", nogenerate

twoway (connected sd_lprod anio, yaxis(1) msymbol(O)) ///
       (connected share_entre anio, yaxis(2) msymbol(Sh) lpattern(dash)), ///
    ytitle("Desv. estándar del log de la productividad" "dentro de cada rama", axis(1)) ///
    ylabel(0(0.25)1.25, axis(1)) ylabel(0(20)80, axis(2)) ///
    ytitle("% de la dispersión explicado" "por diferencias entre ramas", axis(2)) ///
    xtitle("") xlabel(1995(5)2015) ///
    xline(2012.5, lpattern(dot) lcolor(gs10)) ///
    legend(order(1 "Dispersión dentro de la rama (eje izq.)" ///
                 2 "% entre ramas (eje der.)") rows(2) size(small) region(lstyle(none))) ///
    note("Fuente: elaboración propia con ENIA 1995-2015 (INE), plantas de 10 y más ocupados," ///
         "excluida la refinación de metales básicos, recortado el 1% de cada cola por rama-año." ///
         "La línea punteada marca el cambio de CIIU rev.3 a rev.4 en 2013.", size(vsmall))
graph export "$OUT/F_E1 dispersion de productividad en manufactura.png", replace width(2200)
graph export "$OUT/F_E1 dispersion de productividad en manufactura.pdf", replace

display as text _n "== Bloque E terminado =="
