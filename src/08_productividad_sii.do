*! 08_productividad_sii.do
*! Capa de productividad — la tabla puente rama × tamaño de empresa
*!
*! Responde a la pregunta de si se puede definir el «Chile moderno» por productividad
*! y no por formalidad. El problema es que ninguna encuesta de hogares observa la
*! productividad del empleador, y el SII tramifica por VENTAS mientras las encuestas
*! tramifican por EMPLEO. Este do-file construye el puente.
*!
*! Fuente: Servicio de Impuestos Internos, Estadísticas de Empresas, 2005-2024.
*!         Rubro (sección CIIU rev.4) y actividad a 6 dígitos, cruzados con los 13
*!         tramos de venta. Trae número de empresas, ventas en UF, trabajadores
*!         dependientes y renta neta pagada en UF.
*!
*! Tres advertencias que hay que arrastrar a cualquier lectura:
*!   1. VENTAS no es valor agregado. En los tramos grandes hay integración vertical y
*!      comercializadoras, así que «ventas por trabajador» exagera la brecha de
*!      productividad. La versión con valor agregado real sólo existe para manufactura
*!      (ENIA) y está pendiente.
*!   2. El tramo se define POR VENTAS, así que «ventas por trabajador» y «tramo» no son
*!      independientes. Por eso el uso legítimo es ordenar celdas, no estimar una
*!      elasticidad estructural.
*!   3. Los trabajadores son dependientes informados en la DJ 1887 y se cuentan por
*!      empleador: quien tuvo dos empleos en el año aparece dos veces.
*!
*! Produce:
*!   T_F1  productividad y salario por rubro × banda de empleo
*!   T_F2  correspondencia tramo de venta -> banda de empleo, por rubro
*!   F_F1  traspaso de productividad a salarios entre celdas
*!   $INTER/puente_productividad.dta  ← la tabla que consumen los bloques siguientes

version 15
clear all

capture confirm file "$D_SII_RUBR"
if _rc {
    display as error "No está el CSV del SII en $D_SII_RUBR — se salta el bloque F."
    exit 0
}

* ===========================================================================
* 1. Cargar y limpiar
* ===========================================================================
import delimited "$D_SII_RUBR", clear varnames(1) encoding(utf8) case(preserve)

keep if !missing(anio)
drop if nempresas <= 0 | missing(nempresas)

* La sección CIIU va en la primera letra del rubro
gen str1 seccion = substr(rubro, 1, 1)
drop if seccion == "S" & strpos(rubro, "Sin información") > 0
drop if inlist(tramo13, "Sin Ventas/Sin Información")

* ===========================================================================
* 2. Puente: de tramo de VENTAS a banda de EMPLEO
*    El SII informa empresas y trabajadores en cada celda, así que el tamaño medio
*    de empresa es observable y sirve para reasignar cada celda a las bandas que usan
*    la ESI y Casen. Se hace POR RUBRO, no de forma global, porque la relación entre
*    ventas y empleo difiere mucho entre sectores.
*    Bandas: 1 = menos de 5 · 2 = 5 a 10 · 3 = 11 a 49 · 4 = 50 a 199 · 5 = 200 y más
* ===========================================================================
gen double tam_medio = ntrabajadores / nempresas

gen byte banda = .
replace banda = 1 if tam_medio <  5
replace banda = 2 if tam_medio >=  5 & tam_medio <  11
replace banda = 3 if tam_medio >= 11 & tam_medio <  50
replace banda = 4 if tam_medio >= 50 & tam_medio < 200
replace banda = 5 if tam_medio >= 200 & !missing(tam_medio)
label define bandalbl 1 "Menos de 5" 2 "De 5 a 10" 3 "Entre 11 y 49" ///
                      4 "Entre 50 y 199" 5 "200 y más"
label values banda bandalbl

* La correspondencia tiene que ser monótona en el tramo de venta; si no lo es en
* algún rubro-año, es señal de una celda rara y conviene verla.
preserve
    keep if inlist(anio, 2010, 2018, 2024)
    keep anio rubro tramo13 tam_medio banda ntrabajadores
    label variable tam_medio "Trabajadores por empresa"
    label variable banda     "Banda de empleo asignada"
    export excel using "$OUT/2026.08.10 T_F2 puente tramo de venta a banda de empleo.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* 3. Productividad y salario por rubro × banda de empleo
* ===========================================================================
collapse (sum) nempresas ventas_uf ntrabajadores renta_uf, by(anio seccion rubro banda)
drop if missing(banda) | ntrabajadores <= 0 | ventas_uf <= 0

gen double prod  = ventas_uf / ntrabajadores      // UF de venta por trabajador al año
gen double wage  = renta_uf  / ntrabajadores      // UF de renta líquida por trabajador
drop if missing(prod) | missing(wage) | wage <= 0

* Todo relativo al promedio de la economía del año: así no depende del nivel de la UF
bysort anio: egen double VT = total(ventas_uf)
bysort anio: egen double LT = total(ntrabajadores)
bysort anio: egen double RT = total(renta_uf)
gen double prod_rel = prod / (VT/LT)
gen double wage_rel = wage / (RT/LT)

* Posición de la celda en la distribución de productividad del año, ponderada por empleo
bysort anio (prod): gen double _cum = sum(ntrabajadores)
bysort anio: gen double pctil_prod = 100 * (_cum - ntrabajadores/2) / LT
drop _cum VT LT RT

label variable prod       "Ventas por trabajador (UF al año)"
label variable wage       "Renta neta por trabajador (UF al año)"
label variable prod_rel   "Productividad relativa (economía = 1)"
label variable wage_rel   "Salario relativo (economía = 1)"
label variable pctil_prod "Percentil de productividad del año, ponderado por empleo"
label variable banda      "Banda de empleo"

compress
save "$INTER/puente_productividad.dta", replace

preserve
    keep if inlist(anio, 2010, 2018, 2024)
    keep anio rubro banda nempresas ntrabajadores prod wage prod_rel wage_rel pctil_prod
    sort anio rubro banda
    export excel using "$OUT/2026.08.10 T_F1 productividad y salario por rubro y tamano.xlsx", ///
        firstrow(varlabels) replace
restore

* ===========================================================================
* 4. ¿Cuánto de la productividad llega al salario?
*    Regresión entre celdas, ponderada por empleo, con efecto fijo de rubro para que
*    la comparación sea entre empresas de distinto tamaño DENTRO del mismo sector.
* ===========================================================================
gen double lprod = ln(prod)
gen double lwage = ln(wage)
encode seccion, generate(sec_id)

display as text _n "{hline 72}"
display as text "Traspaso de productividad a salarios entre celdas rubro x tamaño"
display as text "{hline 72}"

foreach a in 2010 2018 2024 {
    quietly regress lwage lprod [aw = ntrabajadores] if anio == `a'
    local b1 = _b[lprod]
    quietly regress lwage lprod i.sec_id [aw = ntrabajadores] if anio == `a'
    local b2 = _b[lprod]
    display as text "  `a': elasticidad simple " %5.3f `b1' ///
        "   ·   con efecto fijo de rubro " %5.3f `b2'
}

* Guardar la versión con efecto fijo para el texto
quietly regress lwage lprod i.sec_id [aw = ntrabajadores] if anio == $ANIO_FIN
display as text _n "Lectura: una celda 10% más productiva que otra del mismo rubro paga " ///
    %4.1f 10*_b[lprod] "% más."

* ---- Figura F1 -------------------------------------------------------------
preserve
    keep if anio == 2024
    twoway (scatter wage_rel prod_rel [aw = ntrabajadores], msymbol(Oh) mcolor(%50)) ///
           (lfit wage_rel prod_rel [aw = ntrabajadores], lpattern(dash)) ///
           (function y = x, range(0 6) lpattern(dot) lcolor(gs8)), ///
        xscale(log) yscale(log) ///
        xlabel(0.25 0.5 1 2 4 8) ylabel(0.25 0.5 1 2 4) ///
        xtitle("Ventas por trabajador (economía = 1)") ///
        ytitle("Renta por trabajador (economía = 1)") ///
        legend(order(1 "Celda rubro × banda de empleo" 2 "Ajuste" ///
                     3 "Traspaso completo (45°)") rows(3) size(small) region(lstyle(none))) ///
        note("Fuente: elaboración propia con SII, Estadísticas de Empresas 2024. Cada punto es una" ///
             "celda rubro × banda de empleo, con área proporcional al empleo. La distancia a la línea" ///
             "de 45° es la parte de la ventaja de productividad que no llega al salario.", size(vsmall))
    graph export "$OUT/F_F1 traspaso de productividad a salarios.png", replace width(2200)
    graph export "$OUT/F_F1 traspaso de productividad a salarios.pdf", replace
restore

display as text _n "== Capa de productividad terminada =="
