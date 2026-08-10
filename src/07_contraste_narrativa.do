*! 07_contraste_narrativa.do
*! Bloque D — Contraste entre la narrativa de Katz y los datos chilenos
*!
*! Este bloque no busca refutar a Katz sino ANCLAR el capítulo. Produce las cifras
*! contra las cuales se contrastan afirmaciones concretas del ensayo, de modo que lo
*! que quede escrito resista una lectura crítica. Las divergencias que aparecen están
*! documentadas en docs/2026.08.10 contraste narrativa Katz vs datos.md.
*!
*! Afirmaciones que se contrastan acá:
*!   D1 · «el sector informal absorbe 50% o más de la población ocupada»
*!   D2 · «la informalidad es la contracara de la concentración y los M&A»
*!   D3 · cobre, salmón y vino como «tres sectores centrales de la matriz productiva»
*!   D5 · «pronunciada caída de la tasa de inversión en las dos últimas décadas»
*!
*! (D4, la cercanía al «estado del arte», se contrasta en 06_complejidad_exportadora.do)

version 15
clear all

* ===========================================================================
* D1 · ¿Dónde llega la informalidad al 50%?
* ===========================================================================
use "$INTER/casen_armonizada.dta", clear
keep if ocupacion == 1

* -- Por rama, comparable 2000 vs 2022 --------------------------------------
preserve
    keep if !missing(rama9) & !missing(informal_prev)
    collapse (mean) informal = informal_prev (rawsum) ocupados = expr [aw = expr], ///
        by(anio rama9)
    replace informal = 100 * informal
    keep anio rama9 informal ocupados
    reshape wide informal ocupados, i(rama9) j(anio)
    gen double cambio = informal2022 - informal2000
    label variable informal2000 "% sin cotización previsional, 2000"
    label variable informal2022 "% sin cotización previsional, 2022"
    label variable ocupados2000 "Ocupados 2000"
    label variable ocupados2022 "Ocupados 2022"
    label variable cambio       "Cambio en puntos porcentuales"
    sort rama9
    list rama9 informal2000 informal2022 cambio, noobs abbreviate(14)
    export excel using "$OUT/2026.08.10 T_D1a informalidad por rama.xlsx", ///
        firstrow(varlabels) replace
restore

* -- Por categoría ocupacional ----------------------------------------------
preserve
    keep if !missing(categoria) & !missing(informal_prev)
    collapse (mean) informal = informal_prev [aw = expr], by(anio categoria)
    replace informal = 100 * informal
    reshape wide informal, i(categoria) j(anio)
    label variable informal2000 "% sin cotización previsional, 2000"
    label variable informal2022 "% sin cotización previsional, 2022"
    list, noobs abbreviate(14)
    export excel using "$OUT/2026.08.10 T_D1b informalidad por categoria ocupacional.xlsx", ///
        firstrow(varlabels) replace
restore

* -- Por rama detallada, 2022: dónde sí se llega al 50% ---------------------
preserve
    keep if anio == 2022 & !missing(rama_det) & !missing(informal_prev)
    collapse (mean) informal = informal_prev (rawsum) ocupados = expr [aw = expr], ///
        by(rama_det)
    replace informal = 100 * informal
    keep if ocupados >= 30000            // ramas con peso, para que el dato sea leíble
    gsort -informal
    gen byte sobre50 = informal >= 50
    label variable informal "% sin cotización previsional, 2022"
    label variable ocupados "Ocupados"
    label variable sobre50  "Alcanza o supera el 50%"
    quietly summarize ocupados if sobre50 == 1
    local ocup50 = r(sum)
    quietly summarize ocupados
    display as text "Ocupados en ramas con informalidad >= 50% (2022): " ///
        %12.0fc `ocup50' " de " %12.0fc r(sum) " = " %4.1f 100*`ocup50'/r(sum) "%"
    export excel using "$OUT/2026.08.10 T_D1c ramas con mayor informalidad 2022.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* D2 · ¿La informalidad acompaña a la concentración?
*      Proxy de concentración: participación del empleo de la rama en
*      establecimientos de 200 y más personas.
* ===========================================================================
preserve
    keep if !missing(rama9) & !missing(tamano) & !missing(informal_prev)
    gen byte grande = (tamano == 6)
    collapse (mean) informal = informal_prev grandes = grande [aw = expr], by(anio rama9)
    replace informal = 100 * informal
    replace grandes  = 100 * grandes
    reshape wide informal grandes, i(rama9) j(anio)
    gen double d_informal = informal2022 - informal2000
    gen double d_grandes  = grandes2022  - grandes2000

    quietly correlate d_informal d_grandes
    local r = r(rho)
    display as text _n "Correlación entre el cambio de informalidad y el cambio en el peso" ///
        " de los establecimientos grandes, 9 ramas: r = " %5.2f `r'
    display as text "Es una correlación descriptiva sobre nueve observaciones. No es evidencia causal."

    label variable d_informal "Cambio en informalidad, 2000-2022 (p.p.)"
    label variable d_grandes  "Cambio en el % del empleo en establecimientos de 200+ (p.p.)"
    export excel using "$OUT/2026.08.10 T_D2 informalidad y concentracion por rama.xlsx", ///
        firstrow(varlabels) replace

    twoway (scatter d_informal d_grandes, mlabel(rama9) mlabsize(vsmall) msymbol(O)) ///
           (lfit d_informal d_grandes, lpattern(dash)), ///
        yline(0, lpattern(dot)) xline(0, lpattern(dot)) ///
        ytitle("Cambio en informalidad 2000-2022 (p.p.)") ///
        xtitle("Cambio en el % del empleo en establecimientos de 200 y más (p.p.)") ///
        legend(off) ///
        note("Fuente: elaboración propia con Casen 2000 y 2022, nueve divisiones CIIU." ///
             "Correlación descriptiva sobre nueve ramas; no identifica ningún efecto causal.", ///
             size(vsmall))
    graph export "$OUT/F_D2 informalidad y concentracion.png", replace width(2200)
    graph export "$OUT/F_D2 informalidad y concentracion.pdf", replace
restore

* ===========================================================================
* D3 · El peso de cobre, salmón y vino en el empleo
*      2000, CIIU rev.2: cobre 2302 · pesca 1301-1302 · procesamiento 3114 ·
*                        vino 3132
*      2022, clasificación Casen: cobre 401 · pesca y acuicultura 301 ·
*                        carne y pescado 1001 · vino 1102
*      El procesamiento de pescado no se separa de la carne en 2022, así que esa
*      línea es una cota superior. Se reporta aparte por lo mismo.
* ===========================================================================
gen byte katzsec = .
replace katzsec = 1 if anio == 2000 & rama_det == 2302
replace katzsec = 2 if anio == 2000 & inlist(rama_det, 1301, 1302)
replace katzsec = 3 if anio == 2000 & rama_det == 3114
replace katzsec = 4 if anio == 2000 & rama_det == 3132

replace katzsec = 1 if anio == 2022 & rama_det == 401
replace katzsec = 2 if anio == 2022 & rama_det == 301
replace katzsec = 3 if anio == 2022 & rama_det == 1001
replace katzsec = 4 if anio == 2022 & rama_det == 1102

label define katzlbl 1 "Cobre (extracción y procesamiento)" ///
                     2 "Pesca y acuicultura" ///
                     3 "Procesamiento de pescado (2022: y carne)" ///
                     4 "Elaboración de vinos"
label values katzsec katzlbl

preserve
    gen byte tiene = !missing(katzsec)
    collapse (sum) ocupados = expr, by(anio katzsec)
    bysort anio: egen double tot = total(ocupados)
    gen double pct = 100 * ocupados / tot
    drop if missing(katzsec)
    keep anio katzsec ocupados pct
    reshape wide ocupados pct, i(katzsec) j(anio)
    label variable ocupados2000 "Ocupados 2000"
    label variable pct2000      "% del empleo total, 2000"
    label variable ocupados2022 "Ocupados 2022"
    label variable pct2022      "% del empleo total, 2022"
    list, noobs abbreviate(16)
    quietly summarize pct2000
    local s00 = r(sum)
    quietly summarize pct2022
    display as text _n "Los cuatro renglones juntos: " %4.1f `s00' "% del empleo en 2000 y " ///
        %4.1f r(sum) "% en 2022."
    export excel using "$OUT/2026.08.10 T_D3 empleo en los sectores de Katz.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* D5 · La tasa de inversión
*      Fuente local: extracción de WDI de diciembre de 2021 (llega hasta 2020).
*      Actualizar con una descarga nueva cuando haya conexión.
* ===========================================================================
local wdi "$ALMACEN/World Bank WDI/2021-12/65c64ccd-7a94-4001-b79c-ab52f611ff0b_Data.csv"
capture confirm file "`wdi'"
if _rc {
    display as error "No está el extracto de WDI; se salta D5."
}
else {
    import delimited "`wdi'", clear varnames(nonames) stringcols(_all) encoding(utf8)
    drop in 1
    rename (v1 v2 v3 v4) (pais_nombre pais serie_nombre serie)
    keep if inlist(pais, "CHL", "ARG", "BRA", "MEX", "KOR")
    keep if serie == "NE.GDI.FTOT.ZS"

    * v5..v65 son los años 1960..2020
    forvalues c = 5/65 {
        local y = 1960 + `c' - 5
        rename v`c' y`y'
    }
    reshape long y, i(pais) j(year)
    destring y, generate(fbkf) force
    drop if missing(fbkf)
    keep pais year fbkf
    label variable fbkf "Formación bruta de capital fijo (% del PIB)"

    gen byte pid = .
    replace pid = 1 if pais == "CHL"
    replace pid = 2 if pais == "ARG"
    replace pid = 3 if pais == "BRA"
    replace pid = 4 if pais == "MEX"
    replace pid = 5 if pais == "KOR"
    label define pidlbl2 1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur"
    label values pid pidlbl2

    * Promedios por década, que es como se discute el punto
    preserve
        gen int decada = 10 * floor(year/10)
        keep if inrange(year, 1990, 2020)
        collapse (mean) fbkf, by(pid decada)
        reshape wide fbkf, i(pid) j(decada)
        label variable fbkf1990 "FBKF % del PIB, promedio 1990-1999"
        label variable fbkf2000 "FBKF % del PIB, promedio 2000-2009"
        label variable fbkf2010 "FBKF % del PIB, promedio 2010-2020"
        list, noobs abbreviate(14)
        export excel using "$OUT/2026.08.10 T_D5 tasa de inversion por decada.xlsx", ///
            firstrow(varlabels) replace
    restore

    keep if inrange(year, 1990, 2020)
    keep pid year fbkf
    reshape wide fbkf, i(year) j(pid)
    twoway (line fbkf1 year, lwidth(thick)) ///
           (line fbkf2 year, lpattern(dash)) ///
           (line fbkf3 year, lpattern(shortdash)) ///
           (line fbkf4 year, lpattern(longdash)) ///
           (line fbkf5 year, lpattern(dot)), ///
        legend(order(1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur") ///
               rows(1) size(small) region(lstyle(none))) ///
        ytitle("Formación bruta de capital fijo (% del PIB)") xtitle("") ///
        note("Fuente: elaboración propia con World Development Indicators (extracción de dic-2021).", ///
             size(vsmall))
    graph export "$OUT/F_D5 tasa de inversion.png", replace width(2200)
    graph export "$OUT/F_D5 tasa de inversion.pdf", replace
}

display as text _n "== Bloque D terminado =="
