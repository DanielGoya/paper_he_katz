*! 06_complejidad_exportadora.do
*! Bloque D4 — ¿Se acercó Chile al «estado del arte» internacional?
*!
*! Katz sostiene que en la tercera fase Chile deja de ser tomador de precios y pasa a
*! dialogar con la frontera tecnológica. Esa afirmación es contrastable: si el país se
*! acercó a la frontera, debería verse en la complejidad y en la diversificación de su
*! canasta exportadora. Este bloque mide ambas cosas.
*!
*! Fuente: Atlas of Economic Complexity, Harvard Growth Lab. País-producto-año,
*!         HS92 a 4 dígitos, 1995-2023, más el ranking de ECI.
*!         The Growth Lab at Harvard University. The Atlas of Economic Complexity.
*!
*! Produce:
*!   T_D4a  estructura y complejidad de la canasta exportadora chilena
*!   T_D4b  cobre, salmón y vino como % de las exportaciones
*!   F_D4a  ECI de Chile y comparadores
*!   F_D4b  diversificación: productos con VCR > 1 y peso de los cinco mayores

version 15
clear all

* ===========================================================================
* 1. Índice de complejidad económica, cinco países
* ===========================================================================
import delimited "$D_ATLAS_ECI", clear varnames(1) encoding(utf8)
keep if inlist(country_iso3_code, "CHL", "ARG", "BRA", "MEX", "KOR")
keep country_iso3_code year eci_hs92 eci_rank_hs92
drop if missing(eci_hs92)

gen byte pid = .
replace pid = 1 if country_iso3_code == "CHL"
replace pid = 2 if country_iso3_code == "ARG"
replace pid = 3 if country_iso3_code == "BRA"
replace pid = 4 if country_iso3_code == "MEX"
replace pid = 5 if country_iso3_code == "KOR"
label define pidlbl 1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur"
label values pid pidlbl
save "$INTER/eci_paises.dta", replace

preserve
    keep pid year eci_hs92
    reshape wide eci_hs92, i(year) j(pid)
    twoway (line eci_hs921 year, lwidth(thick)) ///
           (line eci_hs922 year, lpattern(dash)) ///
           (line eci_hs923 year, lpattern(shortdash)) ///
           (line eci_hs924 year, lpattern(longdash)) ///
           (line eci_hs925 year, lpattern(dot)), ///
        legend(order(1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur") ///
               rows(1) size(small) region(lstyle(none))) ///
        ytitle("Índice de complejidad económica (ECI, HS92)") xtitle("") ///
        yline(0, lpattern(dot) lcolor(gs10)) ///
        note("Fuente: elaboración propia con el Atlas of Economic Complexity, Harvard Growth Lab.", ///
             size(vsmall))
    graph export "$OUT/F_D4a complejidad economica.png", replace width(2200)
    graph export "$OUT/F_D4a complejidad economica.pdf", replace
restore

* ===========================================================================
* 2. Canasta exportadora a 4 dígitos
*    El archivo país-producto-año pesa ~450 MB. Se importa una vez y se deja en
*    intermediate/ el subconjunto de los cinco países; las corridas siguientes lo
*    reutilizan.
* ===========================================================================
capture confirm file "$INTER/atlas_5paises.dta"
if _rc {
    display as text "Importando el Atlas país-producto-año (esto tarda unos minutos)..."
    timer clear 1
    timer on 1
    import delimited "$D_ATLAS_CP", clear varnames(1) encoding(utf8) stringcols(4)
    timer off 1
    timer list 1
    keep if inlist(country_iso3_code, "CHL", "ARG", "BRA", "MEX", "KOR")
    keep country_iso3_code product_hs92_code year export_value export_rca pci
    recast double export_value
    compress
    save "$INTER/atlas_5paises.dta", replace
}
use "$INTER/atlas_5paises.dta", clear

destring product_hs92_code, generate(hs4) force
drop if missing(hs4)
drop if missing(export_value) | export_value < 0

* ---- Métricas por país-año ------------------------------------------------
bysort country_iso3_code year: egen double exp_tot = total(export_value)
gen double sh = export_value / exp_tot

* Diversificación: número de productos con ventaja comparativa revelada
gen byte vcr1 = (export_rca >= 1) if !missing(export_rca)

* Concentración: Herfindahl de la canasta y peso de los cinco mayores
gen double sh2 = sh^2
gsort country_iso3_code year -sh
by country_iso3_code year: gen int rank = _n
gen double sh_top5 = sh if rank <= 5

* Complejidad de la canasta, ponderada por exportaciones
gen double pci_w = sh * pci if !missing(pci)

collapse (sum) n_vcr1 = vcr1 hhi = sh2 top5 = sh_top5 pci_prom = pci_w ///
         (max) exp_tot = exp_tot, by(country_iso3_code year)
replace top5 = 100 * top5
gen double hhi_1000 = 1000 * hhi

label variable n_vcr1   "Productos HS4 con VCR > 1"
label variable hhi_1000 "Herfindahl de la canasta (x1.000)"
label variable top5     "% de las exportaciones en los 5 mayores productos"
label variable pci_prom "PCI promedio de la canasta, ponderado por exportaciones"
save "$INTER/atlas_metricas.dta", replace

preserve
    keep if country_iso3_code == "CHL"
    keep year n_vcr1 hhi_1000 top5 pci_prom
    sort year
    export excel using "$OUT/2026.08.10 T_D4a canasta exportadora de Chile.xlsx", ///
        firstrow(varlabels) replace

    twoway (connected n_vcr1 year, yaxis(1) msymbol(O) msize(small)) ///
           (connected top5 year, yaxis(2) msymbol(Sh) msize(small) lpattern(dash)), ///
        ytitle("Número de productos HS4 con VCR > 1", axis(1)) ///
        ytitle("% de las exportaciones en los 5 mayores productos", axis(2)) ///
        xtitle("") ///
        legend(order(1 "Productos con VCR > 1 (eje izq.)" ///
                     2 "Peso de los 5 mayores (eje der.)") ///
               rows(2) size(small) region(lstyle(none))) ///
        note("Fuente: elaboración propia con el Atlas of Economic Complexity (HS92, 4 dígitos). Chile.", ///
             size(vsmall))
    graph export "$OUT/F_D4b diversificacion exportadora de Chile.png", replace width(2200)
    graph export "$OUT/F_D4b diversificacion exportadora de Chile.pdf", replace
restore

* ===========================================================================
* 3. Los tres sectores de Katz en la canasta exportadora
*    Cobre  : HS4 2603 (minerales), 7402 (cobre sin refinar), 7403 (refinado)
*    Salmón : HS4 0302, 0303, 0304 (pescado fresco, congelado y filetes). A 4 dígitos
*             no se separa el salmón del resto del pescado, pero en Chile domina
*             ampliamente; se declara como aproximación por exceso.
*    Vino   : HS4 2204
* ===========================================================================
use "$INTER/atlas_5paises.dta", clear
keep if country_iso3_code == "CHL"
destring product_hs92_code, generate(hs4) force
drop if missing(hs4) | missing(export_value)

bysort year: egen double exp_tot = total(export_value)

gen byte sector = 0
replace sector = 1 if inlist(hs4, 2603, 7402, 7403)
replace sector = 2 if inlist(hs4, 302, 303, 304)
replace sector = 3 if hs4 == 2204

collapse (sum) valor = export_value (max) exp_tot = exp_tot, by(year sector)
gen double pct = 100 * valor / exp_tot
keep year sector pct
reshape wide pct, i(year) j(sector)
label variable pct0 "% resto de las exportaciones"
label variable pct1 "% cobre"
label variable pct2 "% pescado (incluye salmón)"
label variable pct3 "% vino"
gen double pct_tres = pct1 + pct2 + pct3
label variable pct_tres "% de los tres sectores de Katz"
sort year
export excel using "$OUT/2026.08.10 T_D4b cobre salmon y vino en las exportaciones.xlsx", ///
    firstrow(varlabels) replace

twoway (area pct_tres year, fintensity(30)) ///
       (line pct1 year, lwidth(medthick)) ///
       (line pct2 year, lpattern(dash)) ///
       (line pct3 year, lpattern(shortdash)), ///
    legend(order(1 "Los tres juntos" 2 "Cobre" 3 "Pescado (incl. salmón)" 4 "Vino") ///
           rows(1) size(small) region(lstyle(none))) ///
    ytitle("% de las exportaciones de bienes") xtitle("") ///
    note("Fuente: elaboración propia con el Atlas of Economic Complexity (HS92, 4 dígitos)." ///
         "A 4 dígitos el salmón no se separa del resto del pescado: la serie es una cota superior.", ///
         size(vsmall))
graph export "$OUT/F_D4c cobre salmon y vino en las exportaciones.png", replace width(2200)
graph export "$OUT/F_D4c cobre salmon y vino en las exportaciones.pdf", replace

display as text _n "== Bloque D4 terminado =="
