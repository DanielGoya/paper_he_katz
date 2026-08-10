*! 01_etd_he_crosscountry.do
*! Bloque A — Heterogeneidad estructural ENTRE sectores: Chile con benchmarks
*!
*! Fuente: GGDC/UNU-WIDER Economic Transformation Database v2.0 (sept-2023),
*!         12 sectores, valor agregado y empleo, 1990-2018.
*!         Kruse, H., Mensah, E., Sen, K., & de Vries, G. (2023). A manufacturing
*!         (re)naissance? Industrialization in the developing world. IMF Economic
*!         Review, 71(2), 439-473. https://doi.org/10.1057/s41308-022-00183-7
*!
*! Nota de unidades: el VA está en moneda local a precios constantes de 2015. Los
*! NIVELES no son comparables entre países, pero los índices de dispersión (Theil, CV,
*! razón máx/mín) y las descomposiciones son razones y sí lo son.

version 15
clear all

* ===========================================================================
* 1. Cargar y pasar a formato largo país-año-sector
* ===========================================================================
use "$D_ETD", clear

keep if inlist(country, "Chile", "Argentina", "Brazil", "Mexico") | ///
        country == "Republic of Korea"
drop Total Warflag

local sectores Agriculture Mining Manufacturing Utilities Construction Trade ///
               Transport Business Finance Realestate Government Other

local i = 0
foreach s of local sectores {
    local ++i
    rename `s' v`i'
}

reshape long v, i(country cnt var year) j(sec)
rename v value
reshape wide value, i(country cnt year sec) j(var) string

rename valueVA_Q15 va_q
rename valueVA     va_n
rename valueEMP    emp

drop if missing(va_q) | missing(emp) | emp <= 0

* Nombres cortos, en español, para las figuras
gen str16 sector = ""
replace sector = "Agricultura"   if sec == 1
replace sector = "Minería"       if sec == 2
replace sector = "Manufactura"   if sec == 3
replace sector = "Electr. y agua" if sec == 4
replace sector = "Construcción"  if sec == 5
replace sector = "Comercio"      if sec == 6
replace sector = "Transporte"    if sec == 7
replace sector = "Serv. a empresas" if sec == 8
replace sector = "Finanzas"      if sec == 9
replace sector = "Inmobiliario"  if sec == 10
replace sector = "Gobierno"      if sec == 11
replace sector = "Otros serv."   if sec == 12

* País: código numérico estable (los nombres con tilde no sirven como sufijo de reshape)
gen byte pid = .
replace pid = 1 if country == "Chile"
replace pid = 2 if country == "Argentina"
replace pid = 3 if country == "Brazil"
replace pid = 4 if country == "Mexico"
replace pid = 5 if country == "Republic of Korea"
label define pidlbl 1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur"
label values pid pidlbl
decode pid, generate(pais)

compress
save "$INTER/etd_largo.dta", replace

* ===========================================================================
* 2. Índices de HE, en tres coberturas
*    v1 = 12 sectores
*    v2 = sin minería (la renta del recurso infla la dispersión chilena)
*    v3 = sin minería, inmobiliario ni gobierno: el VA inmobiliario incluye
*         alquileres imputados con empleo casi nulo y el gobierno se valora al
*         costo, así que ambos distorsionan la productividad medida
* ===========================================================================
tempfile indices
local primero = 1

forvalues v = 1/3 {

    use "$INTER/etd_largo.dta", clear
    if `v' == 2  drop if sec == 2
    if `v' == 3  drop if inlist(sec, 2, 10, 11)

    bysort country year: egen VA = total(va_q)
    bysort country year: egen L  = total(emp)
    gen prod = va_q / emp                       // productividad laboral sectorial
    gen pagg = VA / L                           // productividad agregada
    gen vsh  = va_q / VA
    gen lsh  = emp  / L
    gen relp = prod / pagg

    * Theil-T entre sectores: SUM_i (VA_i/VA) * ln(p_i/p)
    gen aux_t = vsh * ln(relp)
    bysort country year: egen theil = total(aux_t)

    * Coeficiente de variación ponderado por empleo
    gen aux_c = lsh * (prod - pagg)^2
    bysort country year: egen varp = total(aux_c)
    gen cv = sqrt(varp) / pagg

    bysort country year: egen pmax = max(prod)
    bysort country year: egen pmin = min(prod)
    gen ratio_maxmin = pmax / pmin

    keep pid pais year theil cv ratio_maxmin
    duplicates drop
    gen byte variante = `v'

    if `primero' == 1 {
        save "`indices'", replace
        local primero = 0
    }
    else {
        append using "`indices'"
        save "`indices'", replace
    }
}

use "`indices'", clear
label define varlbl 1 "12 sectores" 2 "Sin minería" ///
                    3 "Sin minería, inmobiliario ni gobierno"
label values variante varlbl
label variable theil        "Theil entre sectores"
label variable cv           "CV ponderado por empleo"
label variable ratio_maxmin "Razón productividad máx/mín"
order pais year variante theil cv ratio_maxmin
sort variante pid year
save "$INTER/he_indices.dta", replace

preserve
    keep if inlist(year, 1990, 2000, 2010, 2018)
    keep pais year variante theil cv ratio_maxmin
    export excel using "$OUT/2026.08.10 T_A1 indices de HE entre sectores.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* 3. Figura A1 — evolución del Theil entre sectores, cinco países
* ===========================================================================
use "$INTER/he_indices.dta", clear
keep if variante == 1
keep pid year theil
reshape wide theil, i(year) j(pid)

twoway (line theil1 year, lwidth(thick)) ///
       (line theil2 year, lpattern(dash)) ///
       (line theil3 year, lpattern(shortdash)) ///
       (line theil4 year, lpattern(longdash)) ///
       (line theil5 year, lpattern(dot)), ///
    legend(order(1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur") ///
           rows(1) size(small) region(lstyle(none))) ///
    ytitle("Índice de Theil de la productividad" "laboral entre 12 sectores") ///
    xtitle("") xlabel(1990(5)2015 2018) ///
    note("Fuente: elaboración propia con GGDC/UNU-WIDER ETD v2.0. Mayor valor = mayor" ///
         "heterogeneidad estructural entre ramas.", size(vsmall))
graph export "$OUT/F_A1 theil entre sectores.png", replace width(2200)
graph export "$OUT/F_A1 theil entre sectores.pdf", replace

* Chile, tres coberturas: cuánto de la HE medida es renta del cobre
use "$INTER/he_indices.dta", clear
keep if pid == 1
keep year variante theil
reshape wide theil, i(year) j(variante)

twoway (line theil1 year, lwidth(thick)) ///
       (line theil2 year, lpattern(dash)) ///
       (line theil3 year, lpattern(shortdash)), ///
    legend(order(1 "12 sectores" 2 "Sin minería" ///
                 3 "Sin minería, inmobiliario ni gobierno") ///
           rows(3) size(small) region(lstyle(none))) ///
    ytitle("Índice de Theil entre sectores") xtitle("") xlabel(1990(5)2015 2018) ///
    note("Fuente: elaboración propia con GGDC ETD v2.0. Chile. La distancia entre las líneas" ///
         "mide cuánta de la heterogeneidad medida proviene de la renta del recurso.", size(vsmall))
graph export "$OUT/F_A1b theil chile por cobertura.png", replace width(2200)
graph export "$OUT/F_A1b theil chile por cobertura.pdf", replace

* ===========================================================================
* 4. Figura A2 — productividad relativa por sector, Chile 2000 vs 2018
* ===========================================================================
use "$INTER/etd_largo.dta", clear
keep if pid == 1 & inlist(year, 2000, 2018)

bysort year: egen VA = total(va_q)
bysort year: egen L  = total(emp)
gen relp = (va_q/emp) / (VA/L)
gen lsh  = 100 * emp / L

keep year sec sector relp lsh
reshape wide relp lsh, i(sec sector) j(year)

gsort -relp2018
gen orden = _n
capture label drop ordlbl
forvalues i = 1/`=_N' {
    local nm = sector[`i']
    label define ordlbl `i' "`nm'", add
}
label values orden ordlbl

twoway (pcspike orden relp2000 orden relp2018, lwidth(vthin) lcolor(gs8)) ///
       (scatter orden relp2000, msymbol(Oh) msize(medium)) ///
       (scatter orden relp2018, msymbol(O)  msize(medium)), ///
    legend(order(2 "2000" 3 "2018") rows(1) size(small) region(lstyle(none))) ///
    ylabel(1/12, valuelabel angle(0) labsize(small)) ytitle("") ///
    yscale(reverse) ///
    xtitle("Productividad laboral relativa (economía = 1)") ///
    xline(1, lpattern(dot)) ///
    note("Fuente: elaboración propia con GGDC ETD v2.0. Chile, VA a precios constantes de 2015.", ///
         size(vsmall))
graph export "$OUT/F_A2 productividad relativa chile.png", replace width(2200)
graph export "$OUT/F_A2 productividad relativa chile.pdf", replace

label variable relp2000 "Prod. relativa 2000"
label variable relp2018 "Prod. relativa 2018"
label variable lsh2000  "% del empleo 2000"
label variable lsh2018  "% del empleo 2018"
keep sector relp2000 relp2018 lsh2000 lsh2018
order sector relp2000 relp2018 lsh2000 lsh2018
export excel using "$OUT/2026.08.10 T_A1b productividad relativa Chile.xlsx", ///
    firstrow(varlabels) replace

* ===========================================================================
* 5. Descomposición McMillan-Rodrik
*    Dp = SUM_i theta_i0 * Dp_i      (intra-sectorial)
*       + SUM_i p_i0    * Dtheta_i   (reasignación estática)
*       + SUM_i Dp_i    * Dtheta_i   (reasignación dinámica)
*    theta = participación en el empleo
*    McMillan, M., & Rodrik, D. (2011). Globalization, structural change and
*    productivity growth. NBER Working Paper 17143.
* ===========================================================================
tempfile mr
local primero = 1

foreach par in "1990 2000" "2000 2010" "2010 2018" "2000 2018" {

    local t0 : word 1 of `par'
    local t1 : word 2 of `par'

    forvalues v = 1/2 {

        use "$INTER/etd_largo.dta", clear
        if `v' == 2  drop if sec == 2
        keep if inlist(year, `t0', `t1')

        bysort country year: egen VA = total(va_q)
        bysort country year: egen L  = total(emp)
        gen prod  = va_q / emp
        gen theta = emp / L
        gen pagg  = VA / L

        keep pid pais year sec prod theta pagg
        reshape wide prod theta pagg, i(pid pais sec) j(year)

        gen dprod  = prod`t1'  - prod`t0'
        gen dtheta = theta`t1' - theta`t0'
        gen w_within = theta`t0' * dprod
        gen w_static = prod`t0'  * dtheta
        gen w_dynam  = dprod     * dtheta

        collapse (sum) w_within w_static w_dynam ///
                 (mean) pagg0 = pagg`t0' pagg1 = pagg`t1', by(pid pais)

        gen dpagg = pagg1 - pagg0
        gen pct_total   = 100 * dpagg    / pagg0
        gen pct_within  = 100 * w_within / pagg0
        gen pct_static  = 100 * w_static / pagg0
        gen pct_dynam   = 100 * w_dynam  / pagg0
        gen pct_realloc = pct_static + pct_dynam
        gen chk = pct_total - (pct_within + pct_static + pct_dynam)

        gen str9 periodo = "`t0'-`t1'"
        gen byte variante = `v'
        keep pid pais periodo variante pct_* chk

        if `primero' == 1 {
            save "`mr'", replace
            local primero = 0
        }
        else {
            append using "`mr'"
            save "`mr'", replace
        }
    }
}

use "`mr'", clear
label define varlbl2 1 "12 sectores" 2 "Sin minería"
label values variante varlbl2

* La identidad tiene que cerrar. El residuo admisible es ruido de punto flotante:
* las cifras están en puntos porcentuales, así que 1e-3 pp es holgadamente estricto.
quietly summarize chk
if abs(r(max)) > 1e-3 | abs(r(min)) > 1e-3 {
    display as error "La descomposición McMillan-Rodrik no cierra (residuo máx = " r(max) ")."
    exit 459
}
display as text "Chequeo OK: la descomposición McMillan-Rodrik cierra en todos los casos."

label variable pct_total   "Cambio total (% de p inicial)"
label variable pct_within  "Intra-sectorial"
label variable pct_static  "Reasignación estática"
label variable pct_dynam   "Reasignación dinámica"
label variable pct_realloc "Reasignación total"
order pais periodo variante pct_total pct_within pct_static pct_dynam pct_realloc
sort variante pid periodo
save "$INTER/mr_decomp.dta", replace

drop chk pid
export excel using "$OUT/2026.08.10 T_A2 descomposicion McMillan-Rodrik.xlsx", ///
    firstrow(varlabels) replace

* ===========================================================================
* 6. Figura A3 — intra-sectorial vs. reasignación, 2000-2018
* ===========================================================================
use "$INTER/mr_decomp.dta", clear
keep if periodo == "2000-2018" & variante == 1
keep pais pct_within pct_realloc

graph bar (asis) pct_within pct_realloc, over(pais, label(labsize(small))) ///
    legend(order(1 "Componente intra-sectorial" 2 "Reasignación entre sectores") ///
           rows(1) size(small) region(lstyle(none))) ///
    ytitle("Cambio de la productividad laboral 2000-2018" "(% de la productividad de 2000)") ///
    yline(0, lpattern(solid) lwidth(vthin)) ///
    note("Fuente: elaboración propia con GGDC ETD v2.0; descomposición de McMillan y Rodrik (2011).", ///
         size(vsmall))
graph export "$OUT/F_A3 descomposicion McMillan-Rodrik.png", replace width(2200)
graph export "$OUT/F_A3 descomposicion McMillan-Rodrik.pdf", replace

display as text _n "== Bloque A terminado =="
