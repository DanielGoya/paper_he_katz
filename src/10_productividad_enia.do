*! 10_productividad_enia.do
*! Bloque H — La capa de productividad medida con VALOR AGREGADO (manufactura)
*!
*! Por qué existe este bloque. La capa del bloque F (`08_productividad_sii.do`) mide
*! productividad como VENTAS por trabajador, porque es lo único que publica el SII. En
*! los tramos grandes esa medida exagera la brecha: una empresa integrada verticalmente
*! y una comercializadora facturan mucho por trabajador sin generar proporcionalmente
*! más valor agregado. La ENIA sí observa el valor agregado neto de cada planta
*! (`k005`), así que permite rehacer la misma tabla con el numerador correcto y medir
*! cuánto de la brecha del SII era integración vertical.
*!
*! Fuente: ENIA (Encuesta Nacional Industrial Anual, INE), panel de seguimiento de
*!         establecimientos 1995-2015. Cubre plantas de 10 y más ocupados.
*!
*! Lo que la ENIA tiene y el SII no: la nómina partida en propietarios y personal
*! directivo, trabajadores de proceso, trabajadores no asociados al proceso y personal
*! subcontratado, cada uno con su masa de remuneraciones. Eso permite preguntar no sólo
*! cuánto de la productividad llega al salario, sino A QUIÉN llega.
*!
*! Cuatro advertencias que hay que arrastrar a cualquier lectura:
*!   1. La ENIA excluye a las plantas de menos de 10 ocupados. Las bandas 1 y 2 del
*!      proyecto (menos de 5, y 5 a 10) sólo aparecen por plantas del panel que cayeron
*!      bajo el umbral: NO son representativas y se reportan marcadas.
*!   2. El `estrato` de la ENIA es el estrato OCDE del marco muestral y NO coincide con
*!      las bandas del proyecto: 0 = menos de 10 · 1 = 10-19 · 2 = 20-49 · 3 = 50-249 ·
*!      4 = 250 y más. Los cortes en 250 y en 10 no son los del proyecto (200 y 11), así
*!      que la banda se construye con el empleo efectivo de la planta (`b021`), que es
*!      observado, y el estrato se reporta aparte como documentación (T_H1b).
*!      Además el estrato viene del marco y arrastra rezago: el 8,2% de las plantas del
*!      estrato 3 declara 200 o más ocupados en el año.
*!   3. Desde 2008 algunas plantas declaran en dólares o euros y el código de `a004`
*!      cambia de año en año (en 2013-2015 usa códigos que ni siquiera están en el
*!      anexo del descriptor). Se conserva sólo la categoría modal de cada año. Como
*!      `a004` se registra recién desde 2011, en 2008-2010 puede quedar moneda
*!      extranjera sin identificar; el recorte de colas absorbe parte de eso.
*!   4. Las remuneraciones cambian de variable en 2008: b022/b024/b026/b028 hasta 2007,
*!      b023/b025/b027/b029 desde 2008. La partición de la nómina existe desde 2000; en
*!      1995-1999 sólo está el total. Y b022/b023 (directivos) viene en cero en ~36% de
*!      las plantas, porque el dueño-gerente se paga con retiros (b034) y no con sueldo:
*!      la razón directivo/operario se calcula sobre las plantas que sí lo declaran y
*!      eso selecciona. Se informa cuántas quedan.
*!   5. El recorte del 1% POR RAMA-AÑO que usa el bloque E no basta acá. Las ramas
*!      chicas tienen 20 plantas en el año, así que su percentil 99 es prácticamente el
*!      máximo y no recorta nada; quedan 55 plantas con productividad de más de 100
*!      veces la mediana de su propia rama, que son errores de unidad —una planta que
*!      declara en miles de dólares y no en miles de pesos está 650 veces arriba—. En
*!      una razón p90/p10 eso no se nota, pero acá la brecha por tamaño se construye
*!      sumando valor agregado y empleo, y un puñado de plantas manda. Sin corregirlo la
*!      brecha 200+/11-49 caía de 1,70 en 2010 a 0,80 en 2015, o sea las plantas grandes
*!      aparecían MENOS productivas que las chicas, con un quiebre justo en 2013. Por
*!      eso se agrega un recorte del 1% en cada cola a nivel de AÑO, sobre toda la
*!      manufactura. Con él el quiebre desaparece y la serie coincide con la de medianas,
*!      que es robusta por construcción: T_H2 reporta las dos.
*!
*! No se deflacta nada, igual que en el resto del pipeline: todo se reporta en razones
*! dentro del año, y las regresiones son cortes transversales año por año.
*!
*! Produce:
*!   T_H1   productividad y salario por rama × banda de empleo (años seleccionados)
*!   T_H1b  correspondencia entre el estrato OCDE de la ENIA y las bandas del proyecto
*!   T_H2   la brecha por tamaño en manufactura: valor agregado (ENIA) vs ventas (SII)
*!   T_H3   traspaso productividad-salario, serie 1995-2015, ENIA vs SII
*!   T_H4   razón directivo/operario y estructura de la nómina por decil intra-rama
*!   F_H1   el traspaso a salarios: ENIA contra SII
*!   F_H2   razón directivo/operario por decil de productividad intra-rama
*!   F_H3   brecha de productividad por tamaño: valor agregado contra ventas
*!   $INTER/puente_productividad_enia.dta  ← la tabla paralela a la del bloque F

version 15
clear all

capture confirm file "$D_ENIA"
if _rc {
    display as error "No está la ENIA en $D_ENIA — se salta el bloque H."
    exit 0
}

* Años de corte para las tablas de niveles. 2010 y 2015 son los únicos años recientes
* que comparten la ENIA (termina en 2015) y el SII (empieza en 2005).
* Dos formas de cada lista: la separada por espacios sirve para `foreach`, la separada
* por comas para `inlist`.
global H_ANIOS_L  "1995 2005 2010 2015"
global H_ANIOS    "1995, 2005, 2010, 2015"
global H_COMPAR_L "2010 2015"
global H_COMPAR   "2010, 2015"

* ===========================================================================
* 1. Base de plantas: limpieza, rama, banda y nómina armonizada
* ===========================================================================
use anio ciiu3 ciiu4 estrato a004 b001 b002 b003 b004 b005 b006 b009 b018 b021 ///
    b022 b023 b024 b025 b026 b027 b028 b029 b030 b031 b033 k005 using "$D_ENIA", clear

* ---- 1.1 Moneda: sólo la categoría modal de cada año --------------------------
bysort anio a004: gen long _n_cat = _N
bysort anio (_n_cat): gen byte _modal = (_n_cat == _n_cat[_N])
quietly count if _modal == 0
display as text "Plantas descartadas por declarar en otra moneda: " r(N)
keep if _modal == 1
drop _n_cat _modal

* ---- 1.2 Rama a 3 dígitos ----------------------------------------------------
* CIIU rev.3 hasta 2012 y rev.4 desde 2013. El que no aplica viene en CERO, no en
* missing, así que hay que filtrarlo explícitamente. No son la misma clasificación:
* la serie se lee dentro de cada régimen y no como empalme.
gen long rama3 = .
replace rama3 = ciiu3 if anio <= 2012 & ciiu3 > 0
replace rama3 = ciiu4 if anio >= 2013 & ciiu4 > 0
drop if missing(rama3)

* ---- 1.3 Productividad: valor agregado neto por ocupado ----------------------
gen double prod = k005 / b021
drop if missing(prod) | prod <= 0 | b021 <= 0

* Sólo ramas con al menos 20 plantas en el año, para que percentiles y deciles
* signifiquen algo (misma regla que el bloque E).
bysort anio rama3: gen long n_plantas = _N
keep if n_plantas >= 20

* ---- 1.4 Recorte del 1% en cada cola, por rama-año y por año -----------------
* Primero dentro de la rama-año, como en el bloque E: el valor agregado neto se acerca
* a cero en unas pocas plantas y eso hace estallar la cola baja.
bysort anio rama3: egen double _p01 = pctile(prod), p(1)
bysort anio rama3: egen double _p99 = pctile(prod), p(99)
quietly count
local antes = r(N)
drop if prod < _p01 | prod > _p99
quietly count
display as text "Recorte al 1% por rama-año: " `antes'-r(N) " plantas de `antes'"
drop _p01 _p99

* Y después a nivel de año, sobre toda la manufactura. Es indispensable acá: ver la
* advertencia 5 de la cabecera. El recorte por rama-año no toca a las ramas de 20
* plantas, y las que sobreviven son justamente los errores de unidad que dominan
* cualquier agregado construido como suma.
bysort anio: egen double _y01 = pctile(prod), p(1)
bysort anio: egen double _y99 = pctile(prod), p(99)
quietly count
local antes = r(N)
drop if prod < _y01 | prod > _y99
quietly count
display as text "Recorte adicional al 1% por año: " `antes'-r(N) " plantas de `antes'"
drop _y01 _y99

* ---- 1.5 Banda de empleo, con los cortes del proyecto ------------------------
* Se construye con el empleo EFECTIVO de la planta y no con el estrato OCDE, porque los
* cortes del estrato (10 y 250) no son los del proyecto (11 y 200). Ver advertencia 2.
gen byte banda = .
replace banda = 1 if b021 <   5
replace banda = 2 if b021 >=  5 & b021 <  11
replace banda = 3 if b021 >= 11 & b021 <  50
replace banda = 4 if b021 >= 50 & b021 < 200
replace banda = 5 if b021 >= 200 & !missing(b021)
label define bandalbl 1 "Menos de 5" 2 "De 5 a 10" 3 "Entre 11 y 49" ///
                      4 "Entre 50 y 199" 5 "200 y más"
label values banda bandalbl

* Marca de las bandas que están fuera del marco muestral de la ENIA
gen byte fuera_marco = inlist(banda, 1, 2)

label define estlbl 0 "Menos de 10 (fuera de marco)" 1 "10 a 19" 2 "20 a 49" ///
                    3 "50 a 249" 4 "250 y más"
label values estrato estlbl

* ---- 1.6 Metales básicos -----------------------------------------------------
* Es la refinación de cobre, o sea la renta del recurso otra vez. Igual que en los
* bloques A y E, todo se reporta con y sin ella.
gen byte metales_basicos = 0
replace metales_basicos = 1 if anio <= 2012 & inrange(rama3, 270, 279)   // CIIU rev.3 27
replace metales_basicos = 1 if anio >= 2013 & inrange(rama3, 240, 249)   // CIIU rev.4 24

* ---- 1.7 Nómina armonizada a través del quiebre de 2008 ----------------------
* Empleo por categoría (b009 = dir + ope + nop, verificado exacto en las 100.803 obs)
gen double L_dir = b001 + b002          // propietarios y personal directivo
gen double L_ope = b003 + b004          // con contrato, asociados al proceso industrial
gen double L_nop = b005 + b006          // con contrato, no asociados al proceso
gen double L_con = b009                 // total con contrato
gen double L_sin = b018                 // total sin contrato (subcontratados y a domicilio)
gen double L_tot = b021                 // total con y sin contrato

* Remuneraciones. Hasta 2007 la serie va en b022/b024/b026/b028; desde 2008, en
* b023/b025/b027/b029. b030+b031 (subcontratados) y b033 (sin contrato) existen desde 2000.
gen double R_dir = cond(anio <= 2007, b022, b023)
gen double R_ope = cond(anio <= 2007, b024, b025)
gen double R_nop = cond(anio <= 2007, b026, b027)
gen double R_con = cond(anio <= 2007, b028, b029)
gen double R_sub = b030 + b031
gen double R_sin = b033

* El salario se mide sobre los trabajadores CON contrato, que son los que cubre R_con.
* Mezclarlo con b021 subestimaría el salario en las plantas que subcontratan.
gen double wage = R_con / L_con if L_con > 0 & R_con > 0

* Recorte del salario en los dos niveles, por la misma razón que el de productividad:
* un error de moneda infla `k005` y `R_con` a la vez. Se marca como missing en vez de
* borrar la planta, para no perderla en los agregados de valor agregado y empleo, que
* no dependen del salario.
bysort anio rama3: egen double _w01 = pctile(wage), p(1)
bysort anio rama3: egen double _w99 = pctile(wage), p(99)
replace wage = . if wage < _w01 | wage > _w99
drop _w01 _w99
bysort anio: egen double _v01 = pctile(wage), p(1)
bysort anio: egen double _v99 = pctile(wage), p(99)
replace wage = . if wage < _v01 | wage > _v99
drop _v01 _v99

gen double lprod = ln(prod)
gen double lwage = ln(wage)

label variable prod  "Valor agregado por ocupado"
label variable wage  "Remuneración por trabajador con contrato"
label variable banda "Banda de empleo"

compress
save "$INTER/enia_plantas.dta", replace

quietly count
display as text _n "Base de plantas del bloque H: " r(N) " observaciones planta-año, 1995-2015."

* ===========================================================================
* 2. La tabla paralela a la del bloque F: rama × banda de empleo
*    Misma estructura que `puente_productividad.dta`, con valor agregado en vez de
*    ventas en el numerador.
* ===========================================================================
use "$INTER/enia_plantas.dta", clear

* La nómina de la celda se suma SÓLO sobre las plantas cuyo salario sobrevivió el
* recorte. Si no, una sola planta con error de moneda en `R_con` desbarata el salario
* de toda la celda: es lo que hacía saltar el error estándar de la regresión de 2013 y
* 2015 a 0,4 y dejaba la elasticidad de 2015 en 0,14 sin significancia.
gen double R_con_ok = R_con if !missing(wage)
gen double L_con_ok = L_con if !missing(wage)

collapse (sum) va = k005 L = L_tot nomina = R_con_ok Lc = L_con_ok ///
         (count) n_plantas = prod (count) n_wage = wage, ///
         by(anio rama3 banda metales_basicos fuera_marco)
drop if L <= 0 | va <= 0

gen double prod = va / L
gen double wage = nomina / Lc if Lc > 0 & nomina > 0

* Todo relativo al promedio de la manufactura del año: así no depende del nivel de
* precios y no hace falta deflactar.
bysort anio: egen double VA_T  = total(va)
bysort anio: egen double L_T   = total(L)
bysort anio: egen double NOM_T = total(nomina)
bysort anio: egen double LC_T  = total(Lc)
gen double prod_rel = prod / (VA_T / L_T)
gen double wage_rel = wage / (NOM_T / LC_T)

* Posición de la celda en la distribución de productividad del año, ponderada por empleo
bysort anio (prod): gen double _cum = sum(L)
bysort anio: gen double pctil_prod = 100 * (_cum - L/2) / L_T
drop _cum VA_T L_T NOM_T LC_T

label variable prod        "Valor agregado por ocupado (miles de pesos del año)"
label variable wage        "Remuneración por trabajador con contrato (miles de pesos del año)"
label variable prod_rel    "Productividad relativa (manufactura = 1)"
label variable wage_rel    "Salario relativo (manufactura = 1)"
label variable pctil_prod  "Percentil de productividad del año, ponderado por empleo"
label variable banda       "Banda de empleo"
label variable n_plantas   "Plantas en la celda"
label variable n_wage      "Plantas con salario utilizable en la celda"
label variable L           "Ocupados en la celda"
label variable fuera_marco "Celda fuera del marco de la ENIA (menos de 11 ocupados)"

compress
save "$INTER/puente_productividad_enia.dta", replace

preserve
    keep if inlist(anio, $H_ANIOS)
    keep anio rama3 banda n_plantas L prod wage prod_rel wage_rel pctil_prod fuera_marco
    order anio rama3 banda n_plantas L prod wage prod_rel wage_rel pctil_prod fuera_marco
    sort anio rama3 banda
    export excel using "$OUT/2026.08.11 T_H1 productividad y salario por rama y tamano (ENIA).xlsx", ///
        firstrow(varlabels) replace
restore

* ---- T_H1b: qué relación tiene el estrato OCDE con las bandas del proyecto ----
use "$INTER/enia_plantas.dta", clear
gen byte uno = 1
collapse (sum) plantas = uno ocupados = L_tot, by(estrato banda)
bysort estrato: egen double tot_est = total(plantas)
gen double pct = 100 * plantas / tot_est
drop tot_est
label variable plantas  "Plantas (todos los años)"
label variable ocupados "Ocupados"
label variable pct      "% del estrato OCDE que cae en la banda"
format pct %6.1f
display as text _n "{hline 72}"
display as text "El estrato OCDE de la ENIA no coincide con las bandas del proyecto"
display as text "{hline 72}"
list, noobs abbreviate(14)
export excel using "$OUT/2026.08.11 T_H1b estrato OCDE de la ENIA y bandas del proyecto.xlsx", ///
    firstrow(varlabels) replace

* ===========================================================================
* 3. El comparador del SII, a tres dígitos y sólo manufactura
*
*    `puente_productividad.dta` (bloque F) está construido sobre PUB_TRAM_RUBR, que
*    agrega por RUBRO = sección CIIU. Ahí la manufactura entera es un solo rubro, o sea
*    cinco celdas por año: alcanza para una razón entre bandas, pero no para estimar una
*    elasticidad. PUB_TRAM_ACT sí trae la actividad a seis dígitos con su subrubro a
*    tres, que es la misma unidad que la rama de la ENIA —y desde 2013 la misma CIIU
*    rev.4—.
*
*    Cada nivel se usa donde es sólido, y no más allá:
*      · T_H2 (razón entre bandas) usa el RUBRO, porque la banda del SII es una
*        IMPUTACIÓN a partir del tamaño medio de empresa del tramo de venta. A nivel de
*        rubro esa imputación sale monótona y limpia (bloque F, T_F2); a nivel de
*        subrubro es ruidosa, y la razón 200+/11-49 de manufactura salta de 0,79 en 2010
*        a 1,71 en 2015 sin que cambie nada real. Además el 5,64 / 6,74 del rubro es la
*        cifra que el capítulo efectivamente reporta: es la que hay que poner a prueba.
*      · T_H3 (elasticidad) usa el subrubro con los tramos de venta TAL COMO SE
*        PUBLICAN, sin imputar banda: así hay cientos de celdas por año y no se le
*        agrega ruido de imputación al regresor.
* ===========================================================================
local hay_sii = 0
capture confirm file "$D_SII_ACT"
if _rc {
    display as error "No está $D_SII_ACT — el bloque H va sin comparador del SII."
}
else {
    local hay_sii = 1
    import delimited "$D_SII_ACT", clear varnames(1) encoding(utf8) case(preserve)

    keep if !missing(anio)
    drop if nempresas <= 0 | missing(nempresas)
    keep if substr(rubro, 1, 1) == "C"                    // sección C: manufactura
    drop if strpos(subrubro, "Sin información") > 0
    drop if tramo13 == "Sin Ventas/Sin Información"

    * Subrubro a 3 dígitos, que es la rama comparable con la ENIA
    gen long rama3 = real(substr(subrubro, 1, 3))
    drop if missing(rama3)

    * Las celdas se dejan como las publica el SII: subrubro × tramo de venta. No se
    * imputa banda de empleo, para no meterle ruido al regresor.
    collapse (sum) nempresas ventas_uf ntrabajadores renta_uf, by(anio rama3 tramo13)
    drop if ntrabajadores <= 0 | ventas_uf <= 0

    gen double prod      = ventas_uf / ntrabajadores
    gen double wage      = renta_uf  / ntrabajadores
    gen double tam_medio = ntrabajadores / nempresas
    drop if missing(prod) | missing(wage) | wage <= 0

    label variable prod      "Ventas por trabajador (UF al año)"
    label variable wage      "Renta neta por trabajador (UF al año)"
    label variable tam_medio "Trabajadores por empresa"
    label variable rama3     "Subrubro CIIU a 3 dígitos"
    compress
    save "$INTER/sii_manufactura.dta", replace

    quietly count
    display as text "Capa SII de manufactura a 3 dígitos: " r(N) " celdas rama × tramo."
}

* ===========================================================================
* 3b. El punto del bloque: ¿cuánto de la brecha por tamaño del SII era integración
*     vertical? Misma manufactura, mismo año, mismas bandas; sólo cambia el numerador.
* ===========================================================================
* Se reportan dos razones: la agregada (suma de valor agregado sobre suma de empleo,
* que es la que replica la construcción del SII) y la de medianas de planta, que es
* robusta por construcción. Si las dos dicen lo mismo, el recorte no está haciendo el
* trabajo por sí solo.
tempname brecha
postfile `brecha' int anio str32 fuente byte sin_metales ///
    double(p_b3 p_b4 p_b5 r53 r43 r53_med r43_med) ///
    using "$INTER/enia_brecha_tamano.dta", replace

foreach a in $H_COMPAR_L {
  forvalues sm = 0/1 {
    use "$INTER/enia_plantas.dta", clear
    quietly keep if anio == `a'
    if `sm' == 1 {
        quietly drop if metales_basicos == 1
    }
    quietly collapse (sum) va = k005 L = L_tot (median) pmed = prod, by(banda)
    quietly gen double p = va / L
    forvalues b = 3/5 {
        local p`b' = .
        local m`b' = .
        quietly summarize p if banda == `b', meanonly
        if r(N) > 0 {
            local p`b' = r(mean)
        }
        quietly summarize pmed if banda == `b', meanonly
        if r(N) > 0 {
            local m`b' = r(mean)
        }
    }
    post `brecha' (`a') ("ENIA · valor agregado") (`sm') (`p3') (`p4') (`p5') ///
        (`p5'/`p3') (`p4'/`p3') (`m5'/`m3') (`m4'/`m3')
  }
}

* La misma razón, con ventas del SII y sólo manufactura. Se usa la capa del bloque F,
* que es la que el capítulo reporta: rubro (= sección C) × banda imputada.
capture confirm file "$INTER/puente_productividad.dta"
if _rc {
    display as error "Falta $INTER/puente_productividad.dta — T_H2 queda sólo con ENIA."
}
else {
  foreach a in $H_COMPAR_L {
    use "$INTER/puente_productividad.dta", clear
    quietly keep if anio == `a' & seccion == "C"
    quietly count
    if r(N) > 0 {
        quietly collapse (sum) ventas_uf ntrabajadores, by(banda)
        quietly gen double p = ventas_uf / ntrabajadores
        forvalues b = 3/5 {
            local p`b' = .
            quietly summarize p if banda == `b', meanonly
            if r(N) > 0 {
                local p`b' = r(mean)
            }
        }
        * El SII publica celdas, no empresas: no hay mediana de planta que reportar.
        post `brecha' (`a') ("SII · ventas") (0) (`p3') (`p4') (`p5') ///
            (`p5'/`p3') (`p4'/`p3') (.) (.)
    }
  }
}
postclose `brecha'

use "$INTER/enia_brecha_tamano.dta", clear
label define smlbl2 0 "Toda la manufactura" 1 "Sin metales básicos"
label values sin_metales smlbl2
label variable fuente      "Fuente y medida"
label variable sin_metales "Cobertura"
label variable p_b3        "Productividad, banda 11-49"
label variable p_b4        "Productividad, banda 50-199"
label variable p_b5        "Productividad, banda 200 y más"
label variable r53         "Razón 200+ / 11-49"
label variable r43         "Razón 50-199 / 11-49"
label variable r53_med     "Razón 200+ / 11-49, medianas de planta"
label variable r43_med     "Razón 50-199 / 11-49, medianas de planta"
format p_b3 p_b4 p_b5 %14.0f
format r53 r43 r53_med r43_med %6.2f
display as text _n "{hline 72}"
display as text "La brecha por tamaño en manufactura: valor agregado contra ventas"
display as text "{hline 72}"
list anio fuente sin_metales r43 r53 r43_med r53_med, noobs abbreviate(18)
export excel using "$OUT/2026.08.11 T_H2 brecha por tamano valor agregado vs ventas.xlsx", ///
    firstrow(varlabels) replace

* ---- F_H3 --------------------------------------------------------------------
preserve
    keep if sin_metales == 0
    label variable r43 "50 a 199 ocupados"
    label variable r53 "200 y más ocupados"
    graph bar (asis) r43 r53, over(fuente, label(labsize(vsmall))) over(anio) ///
        ytitle("Productividad relativa a la banda" "de 11 a 49 ocupados") ///
        blabel(bar, format(%4.2f) size(vsmall)) ///
        legend(order(1 "50 a 199 ocupados" 2 "200 y más ocupados") ///
               rows(1) size(small) region(lstyle(none))) ///
        note("Fuente: elaboración propia con ENIA (INE) y SII, Estadísticas de Empresas." ///
             "La ENIA mide valor agregado neto por ocupado a nivel de planta; el SII, ventas por" ///
             "trabajador a nivel de empresa, restringido a la sección C (manufactura). La distancia" ///
             "entre las dos barras de un mismo año es la parte de la brecha que era facturación.", ///
             size(vsmall))
    graph export "$OUT/F_H3 brecha por tamano valor agregado vs ventas.png", replace width(2200)
    graph export "$OUT/F_H3 brecha por tamano valor agregado vs ventas.pdf", replace
restore

* ===========================================================================
* 4. Traspaso de productividad a salarios
*    Dos niveles, porque no son el mismo estimando:
*      · planta, con efecto fijo de rama a 3 dígitos → la pregunta de la ENIA
*      · celda rama × banda, con efecto fijo de rama → el análogo exacto de la
*        especificación del bloque F, para que la comparación sea de manzanas con
*        manzanas y no de un nivel de agregación con otro.
* ===========================================================================
tempname trasp
postfile `trasp' int anio byte(nivel sin_metales) double(beta se) long nobs ///
    using "$INTER/enia_traspaso.dta", replace

* ---- 4.1 Nivel planta --------------------------------------------------------
use "$INTER/enia_plantas.dta", clear
drop if missing(lwage) | missing(lprod)

gen byte _use = 1
levelsof anio, local(anios)
foreach a of local anios {
  forvalues sm = 0/1 {
    quietly replace _use = (anio == `a')
    if `sm' == 1 {
        quietly replace _use = 0 if metales_basicos == 1
    }
    quietly count if _use == 1
    if r(N) >= 100 {
        quietly areg lwage lprod [aw = L_tot] if _use == 1, absorb(rama3)
        post `trasp' (`a') (1) (`sm') (_b[lprod]) (_se[lprod]) (e(N))
    }
  }
}

* ---- 4.2 Nivel celda rama × banda -------------------------------------------
* Se exigen al menos 5 plantas con salario utilizable en la celda: una celda definida
* por una o dos plantas no es un promedio de nada y le da un apalancamiento enorme a la
* regresión ponderada.
use "$INTER/puente_productividad_enia.dta", clear
drop if missing(prod) | missing(wage) | prod <= 0 | wage <= 0
keep if n_wage >= 5
gen double lprod = ln(prod)
gen double lwage = ln(wage)

gen byte _use = 1
levelsof anio, local(anios)
foreach a of local anios {
  forvalues sm = 0/1 {
    quietly replace _use = (anio == `a')
    if `sm' == 1 {
        quietly replace _use = 0 if metales_basicos == 1
    }
    quietly count if _use == 1
    if r(N) >= 30 {
        quietly areg lwage lprod [aw = L] if _use == 1, absorb(rama3)
        post `trasp' (`a') (2) (`sm') (_b[lprod]) (_se[lprod]) (e(N))
    }
  }
}

* ---- 4.3 El mismo estimando en el SII, sólo manufactura y a 3 dígitos --------
* El 0,60 / 0,45 / 0,45 del bloque F es de toda la economía y entre rubros. Acá se
* estima la misma especificación que en 4.2 —celdas dentro de una rama a tres dígitos,
* efecto fijo de rama, ponderado por empleo— pero con ventas por trabajador en vez de
* valor agregado por ocupado. La diferencia entre las dos series es, otra vez, lo que
* separa facturar de agregar valor.
*
* Advertencia heredada del bloque F: el tramo se define POR VENTAS, así que ventas por
* trabajador y celda no son independientes. La elasticidad del SII sirve de referencia
* de magnitud, no de parámetro estructural.
if `hay_sii' == 1 {
    use "$INTER/sii_manufactura.dta", clear
    gen double lprod = ln(prod)
    gen double lwage = ln(wage)
    gen byte _use = 1
    levelsof anio, local(asii)
    foreach a of local asii {
        quietly replace _use = (anio == `a')
        quietly count if _use == 1
        if r(N) >= 30 {
            quietly areg lwage lprod [aw = ntrabajadores] if _use == 1, absorb(rama3)
            post `trasp' (`a') (3) (0) (_b[lprod]) (_se[lprod]) (e(N))
        }
    }
}
postclose `trasp'

* ---- 4.4 Tabla y figura ------------------------------------------------------
use "$INTER/enia_traspaso.dta", clear
label define nivlbl 1 "ENIA · planta, efecto fijo de rama" ///
                    2 "ENIA · celda rama × banda, efecto fijo de rama" ///
                    3 "SII · celda rama × tramo de venta, efecto fijo de rama"
label values nivel nivlbl
label define smlbl3 0 "Toda la manufactura" 1 "Sin metales básicos"
label values sin_metales smlbl3
label variable nivel       "Fuente y nivel de observación"
label variable sin_metales "Cobertura"
label variable beta        "Elasticidad del salario a la productividad"
label variable se          "Error estándar"
label variable nobs        "Observaciones"
sort nivel sin_metales anio
format beta se %6.3f
display as text _n "{hline 72}"
display as text "Traspaso de productividad a salarios en manufactura"
display as text "{hline 72}"
list anio nivel sin_metales beta se nobs if inlist(anio, $H_ANIOS), noobs abbreviate(20)
export excel using "$OUT/2026.08.11 T_H3 traspaso de productividad a salarios (ENIA vs SII).xlsx", ///
    firstrow(varlabels) replace

* ---- F_H1 --------------------------------------------------------------------
preserve
    * El SII se estima sobre toda la manufactura; la ENIA, sin metales básicos.
    keep if sin_metales == 1 | nivel == 3
    keep anio nivel beta
    reshape wide beta, i(anio) j(nivel)
    label variable beta1 "ENIA · plantas, dentro de rama"
    label variable beta2 "ENIA · celdas rama × tamaño"

    local lsii ""
    capture confirm variable beta3
    if !_rc {
        local lsii "(connected beta3 anio, msymbol(Th) lpattern(shortdash))"
    }
    twoway (connected beta1 anio, msymbol(O)) ///
           (connected beta2 anio, msymbol(Sh) lpattern(dash)) ///
           `lsii', ///
        yline(0.45, lpattern(dot) lcolor(gs8)) ///
        ylabel(0(0.2)0.8, format(%3.1f) angle(horizontal)) xlabel(1995(5)2025) ///
        xline(2012.5, lpattern(dot) lcolor(gs12)) ///
        ytitle("Elasticidad del salario a la productividad") xtitle("") ///
        legend(order(1 "ENIA · plantas, valor agregado" ///
                     2 "ENIA · celdas rama × tamaño, valor agregado" ///
                     3 "SII · celdas rama × tramo de venta, ventas") ///
               rows(3) size(small) region(lstyle(none))) ///
        note("Fuente: elaboración propia con ENIA 1995-2015 (INE) y SII, Estadísticas de Empresas" ///
             "2005-2024, ambas restringidas a manufactura y con efecto fijo de rama a tres dígitos." ///
             "La ENIA excluye la refinación de metales básicos. La línea de puntos marca el 0,45 de" ///
             "toda la economía en el SII. La vertical señala el cambio de CIIU rev.3 a rev.4.", ///
             size(vsmall))
    graph export "$OUT/F_H1 traspaso de productividad a salarios en manufactura.png", replace width(2200)
    graph export "$OUT/F_H1 traspaso de productividad a salarios en manufactura.pdf", replace
restore

* ===========================================================================
* 5. Lo que el SII no puede ver: quién se queda con la nómina
*    Deciles de productividad DENTRO de cada rama a 3 dígitos, y sobre ellos la razón
*    entre lo que gana un directivo y lo que gana un trabajador de proceso.
* ===========================================================================
use "$INTER/enia_plantas.dta", clear

* La partición de la nómina existe desde 2000 (b022); antes sólo está el total.
keep if anio >= 2000
* Excluida la refinación de metales básicos, por lo mismo de siempre
drop if metales_basicos == 1

* Y sólo las plantas cuyo salario sobrevivió el recorte. Es indispensable: acá todo se
* construye SUMANDO remuneraciones, así que una planta con error de moneda contamina
* su decil entero. Sin este filtro la masa salarial sobre valor agregado de 2015 daba
* 717% en el primer decil y no bajaba de 75% en ninguno, contra el patrón monótono y
* creíble de 2000 (203% en el primero, 19% en el décimo).
quietly count
local n_antes = r(N)
keep if !missing(wage)
quietly count
display as text "Plantas con nómina utilizable: " r(N) " de `n_antes' (" ///
    %4.1f 100*r(N)/`n_antes' "%)."

* Deciles de productividad dentro de rama-año, con igual número de plantas cada uno
bysort anio rama3 (prod): gen byte decil = ceil(10 * _n / _N)
label variable decil "Decil de productividad dentro de la rama"
save "$INTER/enia_plantas_decil.dta", replace

* ---- 5.1 Estructura de la nómina y masa salarial sobre valor agregado --------
* Acá NO se restringe a las plantas que declaran remuneración de directivos: un dueño
* que se paga con retiros aporta cero a la nómina y ese cero es informativo.
collapse (sum) va = k005 L_tot L_dir L_ope L_nop L_con L_sin ///
               R_dir R_ope R_nop R_con R_sub R_sin, by(anio decil)

* La participación del trabajo es REMUNERACIONES DE ASALARIADOS sobre valor agregado,
* o sea R_con/va, que es el mismo objeto que la masa salarial sobre VA de las cuentas
* nacionales con que la UAM compara conglomerados. Lo que se paga a personal
* subcontratado NO va acá: es un servicio comprado, ya descontado al llegar al valor
* agregado, así que sumarlo al numerador mientras el denominador es VA es inconsistente.
*
* Dos razones más para dejar fuera la nómina sin contrato, ambas verificadas en 2015:
*   · b033 (R_sin) es el TOTAL de remuneraciones de trabajadores sin contrato y ya
*     incluye a b030+b031 (R_sub); sumar los dos duplicaba el subcontrato, y de hecho
*     R_sub y R_sin coinciden planta por planta en casi todas las observaciones;
*   · dos plantas de la rama 259 declaran pagos a subcontratados de 115 y 67 veces su
*     propio valor agregado, y con eso el séptimo y el noveno decil de 2015 marcaban
*     161% y 158% de masa sobre VA, rompiendo una serie por lo demás monótona.
* El empleo sin contrato (emp_sin) sí se reporta: viene de un conteo de personas y no
* arrastra ese problema.
gen double ms_va    = 100 * R_con / va
gen double sh_dir   = 100 * R_dir / R_con
gen double sh_ope   = 100 * R_ope / R_con
gen double sh_nop   = 100 * R_nop / R_con
gen double emp_dir  = 100 * L_dir / L_con
gen double emp_sin  = 100 * L_sin / L_tot
gen double prod_med = va / L_tot

label variable ms_va    "Remuneraciones con contrato / valor agregado (%)"
label variable sh_dir   "% de la nómina con contrato a directivos"
label variable sh_ope   "% de la nómina con contrato a trabajadores de proceso"
label variable sh_nop   "% de la nómina con contrato a trabajadores no de proceso"
label variable emp_dir  "Directivos como % del empleo con contrato"
label variable emp_sin  "Personal sin contrato como % del empleo total"
label variable prod_med "Valor agregado por ocupado"
label variable decil    "Decil de productividad dentro de la rama"

keep anio decil prod_med ms_va sh_dir sh_ope sh_nop emp_dir emp_sin
order anio decil prod_med ms_va sh_dir sh_ope sh_nop emp_dir emp_sin
sort anio decil
format ms_va sh_dir sh_ope sh_nop emp_dir emp_sin %6.1f
save "$INTER/enia_nomina_decil.dta", replace

display as text _n "{hline 72}"
display as text "Estructura de la nómina por decil de productividad intra-rama, 2015"
display as text "{hline 72}"
list decil ms_va sh_dir sh_ope sh_nop emp_dir emp_sin if anio == 2015, noobs abbreviate(12)

* ---- 5.2 Razón de remuneración directivo / trabajador de proceso -------------
* Acá sí hay que restringir: la razón sólo está definida donde la planta declara
* remuneración y empleo en las dos categorías. Se informa cuánto se pierde.
use "$INTER/enia_plantas_decil.dta", clear
quietly count
local n_todas = r(N)
keep if L_dir > 0 & L_ope > 0 & R_dir > 0 & R_ope > 0
quietly count
display as text _n "Plantas con las dos remuneraciones declaradas: " r(N) " de `n_todas' (" ///
    %4.1f 100*r(N)/`n_todas' "%)."

gen double w_dir = R_dir / L_dir
gen double w_ope = R_ope / L_ope
gen double razon = w_dir / w_ope

* Recorte del 1% de cada cola de la razón, por año
bysort anio: egen double _r01 = pctile(razon), p(1)
bysort anio: egen double _r99 = pctile(razon), p(99)
drop if razon < _r01 | razon > _r99
drop _r01 _r99

collapse (sum) L_dir L_ope R_dir R_ope (median) razon_med = razon ///
         (count) plantas = razon, by(anio decil)
* Razón agregada: cociente de las remuneraciones medias, ponderado por empleo. Es más
* robusta que el promedio de razones de planta, que lo dominan las plantas chicas.
gen double razon_agg = (R_dir / L_dir) / (R_ope / L_ope)

label variable razon_agg "Razón de remuneración directivo / trabajador de proceso"
label variable razon_med "Mediana de la razón entre plantas"
label variable plantas   "Plantas"
label variable decil     "Decil de productividad dentro de la rama"

keep anio decil plantas razon_agg razon_med
order anio decil plantas razon_agg razon_med
sort anio decil
format razon_agg razon_med %6.2f

display as text _n "{hline 72}"
display as text "Razón directivo/operario por decil de productividad intra-rama, 2015"
display as text "{hline 72}"
list decil plantas razon_agg razon_med if anio == 2015, noobs abbreviate(12)

* Tabla T_H4: las dos mitades juntas
merge 1:1 anio decil using "$INTER/enia_nomina_decil.dta", keep(match) nogenerate
sort anio decil
export excel using "$OUT/2026.08.11 T_H4 razon directivo-operario y nomina por decil.xlsx", ///
    firstrow(varlabels) replace

* ---- F_H2 --------------------------------------------------------------------
* Las dos series que sí son monótonas, y que juntas son el resultado del bloque: subir
* en la distribución de productividad DENTRO de la rama baja lo que se reparte y sube
* la desigualdad con que se reparte. Se grafica la MEDIANA de la razón entre plantas y
* no la agregada, porque la agregada es un cociente de sumas y en 2015 se mueve sin
* orden entre deciles (4,1 a 6,0); las dos están en T_H4.
keep if anio == 2015
twoway (bar ms_va decil, barwidth(0.7) color(gs11)) ///
       (connected razon_med decil, yaxis(2) msymbol(O) lpattern(dash) lwidth(medthick)), ///
    ylabel(0(25)175, axis(1) angle(horizontal)) ///
    ytitle("Remuneraciones con contrato" "sobre valor agregado (%)", axis(1)) ///
    ylabel(0(1)5, axis(2) format(%3.1f) angle(horizontal)) ///
    ytitle("Razón de remuneración" "directivo / operario", axis(2)) ///
    xlabel(1(1)10) xtitle("Decil de productividad dentro de la rama") ///
    legend(order(1 "Participación de las remuneraciones en el valor agregado" ///
                 2 "Razón directivo / trabajador de proceso, mediana (eje der.)") ///
           rows(2) size(small) region(lstyle(none))) ///
    note("Fuente: elaboración propia con ENIA 2015 (INE), plantas de 10 y más ocupados, excluida la" ///
         "refinación de metales básicos. Deciles construidos dentro de cada rama a 3 dígitos. La razón" ///
         "compara la remuneración media de propietarios y personal directivo con la de los trabajadores" ///
         "con contrato asociados al proceso industrial, en la planta mediana de cada decil.", size(vsmall))
graph export "$OUT/F_H2 razon directivo-operario por decil de productividad.png", replace width(2200)
graph export "$OUT/F_H2 razon directivo-operario por decil de productividad.pdf", replace

display as text _n "== Bloque H terminado =="
