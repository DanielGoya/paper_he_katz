*! 09_moderno_productividad.do
*! El «Chile moderno» definido por productividad, en tres capas
*!
*! La definición del bloque C es de formalidad y tamaño, y por eso deja un segmento
*! demasiado grande: en 2024 abarca la mitad de los ocupados. Acá se prueba la
*! alternativa que corresponde al argumento de Katz —empresas en la parte alta de la
*! distribución de productividad— y, sobre todo, se mide el paso que la narrativa da
*! por supuesto: que estar en una empresa productiva se traduzca en ingreso.
*!
*!   Capa 1 · rama × banda de empleo en la parte alta de la productividad (SII)
*!   Capa 2 · las personas que trabajan ahí (Casen)
*!   Capa 3 · las que además capturan la renta: por encima de la mediana de ingreso
*!            de su propia celda
*!
*! Límite temporal: el SII arranca en 2005, así que esta definición NO se puede
*! calcular para 2000. La comparación 2000 vs. hoy sigue corriendo con la definición
*! de formalidad del bloque C; ésta es un corte transversal de las encuestas recientes.
*!
*! Produce:
*!   T_G1  las tres capas, por año
*!   T_G2  quién está en la capa 3 y quién se queda fuera
*!   F_G1  de la empresa productiva al trabajador que captura la renta

version 15
clear all

capture confirm file "$INTER/puente_productividad.dta"
if _rc {
    display as error "Falta $INTER/puente_productividad.dta — correr antes 08. Se salta."
    exit 0
}

use "$INTER/casen_cuatro_chiles.dta", clear
keep if ocupacion == 1 & anio > 2000
keep if !missing(seccion) & !missing(banda)

* ===========================================================================
* 1. Pegar la capa de productividad
*    El SII publica por sección CIIU rev.4 (= rubro) y acá ya está reagrupado a las
*    mismas bandas de empleo que usan Casen y la ESI.
* ===========================================================================
decode seccion, generate(sec_letra)
tempfile personas
save "`personas'"

use "$INTER/puente_productividad.dta", clear
keep anio seccion banda prod_rel wage_rel pctil_prod
rename seccion sec_letra
tempfile puente
save "`puente'"

use "`personas'", clear
merge m:1 anio sec_letra banda using "`puente'", keep(master match) generate(_mp)
quietly count
local n = r(N)
quietly count if _mp == 3
display as text "Personas con celda de productividad asignada: " r(N) " de `n' (" ///
    %4.1f 100*r(N)/`n' "%)"
if r(N)/`n' < 0.85 {
    display as error "Se perdió más del 15% en el pegado. Revisar la llave sección × banda."
}
drop _mp

* ===========================================================================
* 2. Las tres capas
* ===========================================================================
* Capa 1-2: trabaja en una celda del quintil superior de productividad del año,
* medida sobre la distribución de empleo (pctil_prod >= 80)
gen byte capa2 = (pctil_prod >= 80) if !missing(pctil_prod)

* Capa 3: además, por encima de la mediana de ingreso DE SU PROPIA CELDA. Es la forma
* de preguntar quién captura la renta sin confundirlo con el nivel del sector.
gen double _y = y_ocup_prin
bysort anio sec_letra banda: egen double med_celda = median(_y)
gen byte capa3 = (capa2 == 1 & _y > med_celda) if !missing(capa2) & !missing(_y)

* Referencia: la definición de formalidad del bloque C
gen byte moderno_c = (chile == 1)

label define capalbl 0 "No" 1 "Sí"
label values capa2 capalbl
label values capa3 capalbl

* ===========================================================================
* 3. Tabla G1 — cuánta gente sobrevive a cada capa
* ===========================================================================
preserve
    gen byte uno = 1
    collapse (mean) capa2 capa3 moderno_c (rawsum) ocupados = expr [aw = expr], by(anio)
    foreach v in capa2 capa3 moderno_c {
        replace `v' = 100 * `v'
    }
    label variable capa2     "% en empresas del quintil superior de productividad"
    label variable capa3     "% que además supera la mediana de ingreso de su celda"
    label variable moderno_c "% en el «Chile moderno» por formalidad (bloque C)"
    label variable ocupados  "Ocupados"
    list, noobs abbreviate(16)
    export excel using "$OUT/2026.08.10 T_G1 el Chile moderno en tres capas.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* 4. Tabla G2 — perfil de quien está dentro y de quien queda fuera
* ===========================================================================
preserve
    keep if anio == $ANIO_FIN & !missing(capa2)
    gen byte grupo = .
    replace grupo = 1 if capa2 == 0
    replace grupo = 2 if capa2 == 1 & capa3 == 0
    replace grupo = 3 if capa3 == 1
    label define grupolbl 1 "Fuera de las empresas productivas" ///
                          2 "En empresa productiva, bajo la mediana de su celda" ///
                          3 "En empresa productiva y sobre la mediana"
    label values grupo grupolbl

    gen double y_lp = y_ocup_prin / linea_pobreza
    gen byte mujer = (sexo == 2) if !missing(sexo)
    collapse (rawsum) ocupados = expr ///
             (median) ing_lp = y_lp ///
             (mean) escolaridad = escolaridad pct_calificado = calificado ///
                    pct_informal = informal_prev pct_mujer = mujer ///
             [aw = expr], by(grupo)
    egen double tot = total(ocupados)
    gen double pct = 100 * ocupados / tot
    foreach v in pct_calificado pct_informal pct_mujer {
        replace `v' = 100 * `v'
    }
    label variable pct            "% de los ocupados"
    label variable ing_lp         "Ingreso mediano / línea de pobreza"
    label variable escolaridad    "Años de escolaridad"
    label variable pct_calificado "% en ocupación calificada (CIUO 1-3)"
    label variable pct_informal   "% sin cotización previsional"
    label variable pct_mujer      "% mujeres"
    keep grupo pct ing_lp escolaridad pct_calificado pct_informal pct_mujer
    order grupo pct ing_lp escolaridad pct_calificado pct_informal pct_mujer
    list, noobs abbreviate(16)
    export excel using "$OUT/2026.08.10 T_G2 quien captura la renta.xlsx", ///
        firstrow(varlabels) replace

    graph bar (asis) pct, over(grupo, label(labsize(vsmall) angle(20))) ///
        ytitle("% de los ocupados, $ANIO_FIN") ///
        blabel(bar, format(%4.1f) size(small)) legend(off) ///
        note("Fuente: elaboración propia con Casen $ANIO_FIN y SII, Estadísticas de Empresas." ///
             "«Empresa productiva» = celda rama × tamaño en el quintil superior de ventas por" ///
             "trabajador, ponderado por empleo.", size(vsmall))
    graph export "$OUT/F_G1 de la empresa productiva al trabajador.png", replace width(2200)
    graph export "$OUT/F_G1 de la empresa productiva al trabajador.pdf", replace
restore

display as text _n "== Chile moderno por productividad terminado =="
