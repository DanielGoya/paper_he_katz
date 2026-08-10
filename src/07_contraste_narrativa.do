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

local A0 = $ANIO_INI
local A1 = $ANIO_FIN

* ===========================================================================
* D1 · ¿Dónde llega la informalidad al 50%?
* ===========================================================================
use "$INTER/casen_armonizada.dta", clear
keep if ocupacion == 1

* -- Por rama, comparable entre años ----------------------------------------
preserve
    keep if !missing(rama9) & !missing(informal_prev)
    collapse (mean) informal = informal_prev (rawsum) ocupados = expr [aw = expr], ///
        by(anio rama9)
    replace informal = 100 * informal
    keep anio rama9 informal ocupados
    reshape wide informal ocupados, i(rama9) j(anio)
    gen double cambio = informal`A1' - informal`A0'
    foreach a in $ANIOS {
        label variable informal`a' "% sin cotización previsional, `a'"
        label variable ocupados`a' "Ocupados `a'"
    }
    label variable cambio "Cambio `A0'-`A1' en puntos porcentuales"
    sort rama9
    list rama9 informal`A0' informal`A1' cambio, noobs abbreviate(14)
    export excel using "$OUT/2026.08.10 T_D1a informalidad por rama.xlsx", ///
        firstrow(varlabels) replace
restore

* -- Por categoría ocupacional ----------------------------------------------
preserve
    keep if !missing(categoria) & !missing(informal_prev)
    collapse (mean) informal = informal_prev [aw = expr], by(anio categoria)
    replace informal = 100 * informal
    reshape wide informal, i(categoria) j(anio)
    foreach a in $ANIOS {
        label variable informal`a' "% sin cotización previsional, `a'"
    }
    list, noobs abbreviate(14)
    export excel using "$OUT/2026.08.10 T_D1b informalidad por categoria ocupacional.xlsx", ///
        firstrow(varlabels) replace
restore

* -- Por rama detallada, año final: dónde sí se llega al 50% ----------------
preserve
    keep if anio == `A1' & !missing(rama_det) & !missing(informal_prev)
    collapse (mean) informal = informal_prev (rawsum) ocupados = expr [aw = expr], ///
        by(rama_det)
    replace informal = 100 * informal
    keep if ocupados >= 30000            // ramas con peso, para que el dato sea leíble
    gsort -informal
    gen byte sobre50 = informal >= 50
    label variable informal "% sin cotización previsional, `A1'"
    label variable ocupados "Ocupados"
    label variable sobre50  "Alcanza o supera el 50%"
    quietly summarize ocupados if sobre50 == 1
    local ocup50 = r(sum)
    quietly summarize ocupados
    display as text "Ocupados en ramas con informalidad >= 50% (`A1'): " ///
        %12.0fc `ocup50' " de " %12.0fc r(sum) " = " %4.1f 100*`ocup50'/r(sum) "%"
    export excel using "$OUT/2026.08.10 T_D1c ramas con mayor informalidad.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* D2 · ¿La informalidad acompaña a la concentración?
*      Proxy de concentración: participación del empleo de la rama en
*      establecimientos de 200 y más personas.
* ===========================================================================
preserve
    keep if inlist(anio, `A0', `A1')
    keep if !missing(rama9) & !missing(tamano) & !missing(informal_prev)
    gen byte grande = (tamano == 6)
    collapse (mean) informal = informal_prev grandes = grande [aw = expr], by(anio rama9)
    replace informal = 100 * informal
    replace grandes  = 100 * grandes
    reshape wide informal grandes, i(rama9) j(anio)
    gen double d_informal = informal`A1' - informal`A0'
    gen double d_grandes  = grandes`A1'  - grandes`A0'

    quietly correlate d_informal d_grandes
    display as text _n "Correlación entre el cambio de informalidad y el cambio en el peso" ///
        " de los establecimientos grandes, 9 ramas, `A0'-`A1': r = " %5.2f r(rho)
    display as text "Es una correlación descriptiva sobre nueve observaciones. No es evidencia causal."

    label variable d_informal "Cambio en informalidad `A0'-`A1' (p.p.)"
    label variable d_grandes  "Cambio en el % del empleo en establecimientos de 200+ (p.p.)"
    export excel using "$OUT/2026.08.10 T_D2 informalidad y concentracion por rama.xlsx", ///
        firstrow(varlabels) replace

    twoway (scatter d_informal d_grandes, mlabel(rama9) mlabsize(vsmall) msymbol(O)) ///
           (lfit d_informal d_grandes, lpattern(dash)), ///
        yline(0, lpattern(dot)) xline(0, lpattern(dot)) ///
        ytitle("Cambio en informalidad `A0'-`A1' (p.p.)") ///
        xtitle("Cambio en el % del empleo en establecimientos de 200 y más (p.p.)") ///
        legend(off) ///
        note("Fuente: elaboración propia con Casen `A0' y `A1', nueve divisiones CIIU." ///
             "Correlación descriptiva sobre nueve ramas; no identifica ningún efecto causal.", ///
             size(vsmall))
    graph export "$OUT/F_D2 informalidad y concentracion.png", replace width(2200)
    graph export "$OUT/F_D2 informalidad y concentracion.pdf", replace
restore

* ===========================================================================
* D3 · El peso de cobre, salmón y vino en el empleo
*      2000, CIIU rev.2: cobre 2302 · pesca 1301-1302 · procesamiento 3114 ·
*                        vino 3132
*      2022 y 2024, clasificación CAENES de Casen: cobre 401 · pesca y
*                        acuicultura 301 · carne y pescado 1001 · vino 1102
*      El procesamiento de pescado no se separa del de carne en las encuestas
*      recientes, así que esa línea es una cota superior.
* ===========================================================================
gen byte katzsec = .
replace katzsec = 1 if anio == 2000 & rama_det == 2302
replace katzsec = 2 if anio == 2000 & inlist(rama_det, 1301, 1302)
replace katzsec = 3 if anio == 2000 & rama_det == 3114
replace katzsec = 4 if anio == 2000 & rama_det == 3132

replace katzsec = 1 if anio > 2000 & rama_det == 401
replace katzsec = 2 if anio > 2000 & rama_det == 301
replace katzsec = 3 if anio > 2000 & rama_det == 1001
replace katzsec = 4 if anio > 2000 & rama_det == 1102

label define katzlbl 1 "Cobre (extracción y procesamiento)" ///
                     2 "Pesca y acuicultura" ///
                     3 "Procesamiento de pescado (y carne desde 2022)" ///
                     4 "Elaboración de vinos"
label values katzsec katzlbl

preserve
    collapse (sum) ocupados = expr, by(anio katzsec)
    bysort anio: egen double tot = total(ocupados)
    gen double pct = 100 * ocupados / tot
    drop if missing(katzsec)
    keep anio katzsec ocupados pct
    reshape wide ocupados pct, i(katzsec) j(anio)
    foreach a in $ANIOS {
        label variable ocupados`a' "Ocupados `a'"
        label variable pct`a'      "% del empleo total, `a'"
    }
    list, noobs abbreviate(16)
    quietly summarize pct`A0'
    local s0 = r(sum)
    quietly summarize pct`A1'
    display as text _n "Los cuatro renglones juntos: " %4.1f `s0' "% del empleo en `A0' y " ///
        %4.1f r(sum) "% en `A1'."
    export excel using "$OUT/2026.08.10 T_D3 empleo en los sectores de Katz.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* D5 · La tasa de inversión
*      Descarga propia desde la API del Banco Mundial (agosto 2026), que llega a
*      2025. El extracto antiguo de diciembre de 2021 queda como respaldo.
* ===========================================================================
capture confirm file "$D_WDI_CSV"
if _rc {
    display as error "No está el CSV de WDI en $D_WDI_CSV; se salta D5."
}
else {
    import delimited "$D_WDI_CSV", clear varnames(1) encoding(utf8)
    keep if indicador == "NE.GDI.FTOT.ZS"
    rename valor fbkf
    keep iso3 anio fbkf
    label variable fbkf "Formación bruta de capital fijo (% del PIB)"

    gen byte pid = .
    replace pid = 1 if iso3 == "CHL"
    replace pid = 2 if iso3 == "ARG"
    replace pid = 3 if iso3 == "BRA"
    replace pid = 4 if iso3 == "MEX"
    replace pid = 5 if iso3 == "KOR"
    drop if missing(pid)
    label define pidlbl3 1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur"
    label values pid pidlbl3

    quietly summarize anio
    display as text "WDI: la serie de FBKF llega hasta " r(max)

    * Promedios por década, que es como se discute el punto
    preserve
        gen int decada = 10 * floor(anio/10)
        keep if inrange(anio, 1990, 2025)
        replace decada = 2020 if anio >= 2020
        collapse (mean) fbkf, by(pid decada)
        reshape wide fbkf, i(pid) j(decada)
        label variable fbkf1990 "FBKF % del PIB, promedio 1990-1999"
        label variable fbkf2000 "FBKF % del PIB, promedio 2000-2009"
        label variable fbkf2010 "FBKF % del PIB, promedio 2010-2019"
        label variable fbkf2020 "FBKF % del PIB, promedio 2020-2025"
        list, noobs abbreviate(14)
        export excel using "$OUT/2026.08.10 T_D5 tasa de inversion por decada.xlsx", ///
            firstrow(varlabels) replace
    restore

    keep if inrange(anio, 1990, 2025)
    keep pid anio fbkf
    reshape wide fbkf, i(anio) j(pid)
    twoway (line fbkf1 anio, lwidth(thick)) ///
           (line fbkf2 anio, lpattern(dash)) ///
           (line fbkf3 anio, lpattern(shortdash)) ///
           (line fbkf4 anio, lpattern(longdash)) ///
           (line fbkf5 anio, lpattern(dot)), ///
        legend(order(1 "Chile" 2 "Argentina" 3 "Brasil" 4 "México" 5 "Corea del Sur") ///
               rows(1) size(small) region(lstyle(none))) ///
        ytitle("Formación bruta de capital fijo (% del PIB)") xtitle("") ///
        xlabel(1990(5)2025) ///
        note("Fuente: elaboración propia con World Development Indicators, Banco Mundial" ///
             "(descarga de agosto de 2026).", size(vsmall))
    graph export "$OUT/F_D5 tasa de inversion.png", replace width(2200)
    graph export "$OUT/F_D5 tasa de inversion.pdf", replace
}

display as text _n "== Bloque D terminado =="
