*! 11_conglomerados_chile.do — réplica y sensibilidades de los conglomerados de Chile
*!
*! Propósito
*! ---------
*! 1. Reproducir en Stata el Ward de la UAM para Chile, 2003 y 2023.
*! 2. Reincorporar únicamente el cobre y cortar Ward en k = 4.
*! 3. Mostrar, una por una, las variaciones discutidas en la nota
*!    2026-08-21-problemas-del-ward-inicial-y-correcciones-probadas.md.
*!
*! Nota de procedencia. El análisis de conglomerados original de este proyecto
*! se implementó en Python, no en Stata (py/20, 25, 26, 40, 45, 46 y 51-52).
*! Este archivo traduce esos procedimientos a Stata 15/Mata. Los demás bloques
*! del capítulo sí viven en do-files de Stata.
*!
*! Uso
*! ---
*!   "C:/Program Files (x86)/Stata15/StataMP-64.exe" /e do ///
*!       "D:/repos/paper_he_katz/src/11_conglomerados_chile.do"
*!
*! Para una exposición, cambiar PAUSAR a 1. Stata se detendrá al terminar cada
*! enfoque; escribir `q` en la ventana de resultados para avanzar.
*!
*! Alcance de la réplica. Es exacta respecto de las tres planillas recibidas de
*! la UAM. No reconstruye todavía el ejercicio desde fuentes primarias.

version 15
clear all
set more off
set seed 20260813

global REPO_ROOT "D:/repos/paper_he_katz"
global SOLO_CONGLOMERADOS 1
do "$REPO_ROOT/config/rutas.do"
global SOLO_CONGLOMERADOS

* Punteros derivados: las planillas UAM son datos propios recibidos y viven en
* raw_local. Se declaran aquí para que este do-file sea autónomo incluso si una
* copia antigua de config/rutas.do todavía no trae estos cuatro globals.
global D_UAM          "$RAW/UAM_Dutrenit"
global D_UAM_INSUMO   "$D_UAM/Chile_datos_Aug08_26_v1.xlsx"
global D_UAM_HCLUST1  "$D_UAM/3a_resultados_hclust_Chile_1_v1.xlsx"
global D_UAM_HCLUST2  "$D_UAM/3b_resultados_hclust_Chile_2_v1.xlsx"

local PAUSAR 0
if `PAUSAR' pause on

capture log close _all
log using "$SCRATCH/log_conglomerados_chile_stata.txt", replace text name(cluster_chile)

local VARS_UAM ///
    x_prod_trabajo x_capital_trabajo x_remunera_prom ///
    x_demanda_externa x_balanza_com x_ingreso_interno x_oferta_externa

local VARS_COMERCIO ///
    x_prod_trabajo x_capital_trabajo x_remunera_prom ///
    x_ingreso_interno x_apertura x_balanza_norm

local SUMABLES valor_agrega vbp remunera empleo fbcf expo impo

display as text _n "{hline 78}"
display as text "Conglomerados de Chile: réplica, cobre y sensibilidades"
display as text "Corrida: " c(current_date) " " c(current_time) " · Stata " c(stata_version)
display as text "{hline 78}"

* =============================================================================
* 0. Motor común. Todo lo que sigue es Stata; los algoritmos especiales van en
*    Mata porque Stata 15 no ofrece Ward ponderado ni PAM ponderado de fábrica.
* =============================================================================

capture program drop dg_variables
program define dg_variables
    version 15
    syntax, Balanza(string) Comercio(integer) Logs(integer)

    capture drop x_prod_trabajo x_capital_trabajo x_remunera_prom
    capture drop x_demanda_externa x_balanza_com x_ingreso_interno
    capture drop x_oferta_externa x_apertura x_balanza_norm

    assert empleo > 0 & empleo < .
    assert vbp > 0 & vbp < .

    generate double x_prod_trabajo    = valor_agrega / empleo
    generate double x_capital_trabajo = fbcf / empleo
    generate double x_remunera_prom   = remunera / empleo
    generate double x_demanda_externa = impo / vbp
    generate double x_ingreso_interno = valor_agrega / vbp
    generate double x_oferta_externa  = expo / vbp

    generate double x_apertura = (expo + impo) / vbp
    generate double x_balanza_norm = 0
    replace x_balanza_norm = (expo - impo) / (expo + impo) if expo + impo > 0

    if "`balanza'" == "nivel" {
        generate double x_balanza_com = expo - impo
    }
    else if "`balanza'" == "vbp" {
        generate double x_balanza_com = (expo - impo) / vbp
    }
    else if "`balanza'" == "norm" {
        generate double x_balanza_com = x_balanza_norm
    }
    else {
        display as error "Balanza() debe ser nivel, vbp o norm."
        exit 198
    }

    * La reparametrización se selecciona mediante el varlist de cada corrida.
    * Comercio(1) queda como comprobación documental: apertura + balanza norm.
    if `comercio' == 1 {
        assert abs(x_balanza_norm - ///
            (x_oferta_externa - x_demanda_externa) / ///
            (x_oferta_externa + x_demanda_externa)) < 1e-10 ///
            if x_oferta_externa + x_demanda_externa > 0
    }

    if `logs' == 1 {
        * Productividad y remuneración: log; cero/negativo se lleva a la mitad
        * del menor valor positivo, igual que py/40_uam_metodo.py.
        foreach v in x_prod_trabajo x_remunera_prom {
            quietly summarize `v' if `v' > 0, meanonly
            if r(N) > 0 {
                local piso = r(min) / 2
                replace `v' = ln(max(`v', `piso'))
            }
        }

        * Ratios no negativos: log(1+x). FBCF queda en niveles por sus ceros y
        * negativos; la balanza normalizada queda en niveles por estar acotada.
        foreach v in x_demanda_externa x_oferta_externa x_apertura {
            quietly summarize `v'
            if r(min) >= 0 replace `v' = ln(1 + `v')
        }
    }
end

capture program drop dg_z_muestral
program define dg_z_muestral
    version 15
    syntax varlist(min=1 numeric), Prefix(string)
    foreach v of local varlist {
        quietly summarize `v'
        generate double `prefix'`v' = (`v' - r(mean)) / r(sd)
    }
end

capture program drop dg_cluster
program define dg_cluster
    version 15
    syntax varlist(min=2 numeric), Generate(name) K(integer) Method(string) ///
        [Metric(string) Weightvar(name) Restarts(integer 50)]

    confirm new variable `generate'
    local method = lower("`method'")
    local metric = lower("`metric'")
    if "`metric'" == "" local metric "euclidean"
    if !inlist("`method'", "ward", "pam") {
        display as error "Method() debe ser ward o pam."
        exit 198
    }
    if "`method'" == "ward" & "`metric'" != "euclidean" {
        display as error "Ward se implementa con distancia euclidiana."
        exit 198
    }
    if "`method'" == "pam" & !inlist("`metric'", "euclidean", "manhattan") {
        display as error "Metric() debe ser euclidean o manhattan."
        exit 198
    }

    generate double `generate' = .
    mata: dg_cluster_store(tokens(st_local("varlist")), ///
        st_local("weightvar"), st_local("generate"), ///
        strtoreal(st_local("k")), st_local("method"), ///
        st_local("metric"), strtoreal(st_local("restarts")))
    recast int `generate'
end

capture program drop dg_comparar
program define dg_comparar, rclass
    version 15
    syntax varlist(min=2 max=2 numeric)
    mata: st_matrix("DG_RAND", dg_rand(st_data(., tokens(st_local("varlist")))))
    return scalar rand = DG_RAND[1,1]
    return scalar ari  = DG_RAND[1,2]
    matrix drop DG_RAND
end

capture program drop dg_eta2
program define dg_eta2, rclass
    version 15
    syntax, Cluster(name) Weight(name) Outcome(name)
    mata: st_numscalar("DG_ETA2", dg_eta2_fun( ///
        st_data(., st_local("outcome")), ///
        st_data(., st_local("cluster")), ///
        st_data(., st_local("weight"))))
    return scalar eta2 = scalar(DG_ETA2)
    scalar drop DG_ETA2
end

capture program drop dg_resumen
program define dg_resumen
    version 15
    syntax, Cluster(name) Titulo(string)
    preserve
        quietly summarize empleo, meanonly
        local T_EMP = r(sum)
        quietly summarize valor_agrega, meanonly
        local T_VA = r(sum)
        quietly summarize expo, meanonly
        local T_X = r(sum)

        generate byte __n = 1
        collapse (sum) n=__n empleo valor_agrega remunera expo, by(`cluster')
        generate double empleo_pct = 100 * empleo / `T_EMP'
        generate double va_pct = 100 * valor_agrega / `T_VA'
        generate double expo_pct = 100 * expo / `T_X'
        generate double productividad = 100 * (valor_agrega / empleo) / (`T_VA' / `T_EMP')
        generate double masa_salarial_va = 100 * remunera / valor_agrega
        sort `cluster'
        format empleo_pct va_pct expo_pct masa_salarial_va %6.1f
        format productividad %7.0f
        display as result _n "`titulo'"
        list `cluster' n empleo_pct va_pct expo_pct productividad ///
            masa_salarial_va, noobs abbreviate(20)
    restore
end

mata:
mata set matastrict on

real scalar dg_argmin(real rowvector x)
{
    real scalar j, b
    b = 1
    for (j=2; j<=cols(x); j++) if (x[j] < x[b]) b = j
    return(b)
}

real matrix dg_standardize(real matrix X, real colvector w, real scalar weighted)
{
    real rowvector mu, sd, vv
    real colvector wn
    real matrix XC

    if (weighted == 0) {
        mu = mean(X)
        XC = X :- mu
        sd = sqrt(colsum(XC:^2) / (rows(X)-1))
    }
    else {
        wn = w / sum(w)
        mu = wn' * X
        XC = X :- mu
        vv = wn' * (XC:^2)
        sd = sqrt(vv / max((1e-12, 1-sum(wn:^2))))
    }
    sd = sd :+ (sd:==0)
    return(XC :/ sd)
}

real colvector dg_relabel(real colvector lab, real colvector w)
{
    real colvector grupos, masa, orden, out
    real scalar g, i
    grupos = uniqrows(sort(lab,1))
    masa = J(rows(grupos),1,.)
    for (g=1; g<=rows(grupos); g++) masa[g] = sum(select(w, lab:==grupos[g]))
    orden = order(-masa,1)
    out = J(rows(lab),1,.)
    for (i=1; i<=rows(orden); i++) {
        out[selectindex(lab:==grupos[orden[i]])] = J(sum(lab:==grupos[orden[i]]),1,i)
    }
    return(out)
}

real colvector dg_ward_cut(real matrix Z, real colvector w, real scalar k)
{
    real matrix C, M
    real colvector mass, keep, labels, orden, idx
    real scalar i, j, a, b, best, cost, newmass, g
    real rowvector dif

    C = Z
    mass = w
    M = I(rows(Z))

    while (rows(C) > k) {
        best = .
        a = b = .
        for (i=1; i<rows(C); i++) {
            for (j=i+1; j<=rows(C); j++) {
                dif = C[i,.] - C[j,.]
                cost = (mass[i]*mass[j]/(mass[i]+mass[j])) * (dif*dif')
                if (missing(best) | cost < best) {
                    best = cost
                    a = i
                    b = j
                }
            }
        }
        newmass = mass[a] + mass[b]
        C[a,.] = (mass[a]*C[a,.] + mass[b]*C[b,.]) / newmass
        mass[a] = newmass
        M[a,.] = M[a,.] + M[b,.]
        keep = selectindex((1::rows(C)):!=b)
        C = C[keep,.]
        mass = mass[keep]
        M = M[keep,.]
    }

    orden = order(-mass,1)
    labels = J(cols(M),1,.)
    for (g=1; g<=k; g++) {
        idx = selectindex(M[orden[g],.]':>0.5)
        labels[idx] = J(rows(idx),1,g)
    }
    return(labels)
}

real matrix dg_distances(real matrix Z, string scalar metric)
{
    real matrix D
    real rowvector d
    real scalar i, j, v
    D = J(rows(Z), rows(Z), 0)
    for (i=1; i<rows(Z); i++) {
        for (j=i+1; j<=rows(Z); j++) {
            d = Z[i,.] - Z[j,.]
            if (metric == "manhattan") v = sum(abs(d))
            else v = sqrt(d*d')
            D[i,j] = D[j,i] = v
        }
    }
    return(D)
}

real scalar dg_pam_cost(real matrix D, real rowvector med, real colvector w)
{
    return(sum(w :* colmin(D[med,.])'))
}

real rowvector dg_pam_swap(real matrix D, real rowvector med, real colvector w)
{
    real scalar current, best, c, pos, h, improved
    real rowvector cand, bestmed
    current = dg_pam_cost(D, med, w)
    do {
        best = current
        bestmed = med
        improved = 0
        for (pos=1; pos<=cols(med); pos++) {
            for (h=1; h<=rows(D); h++) {
                if (sum(med:==h)) continue
                cand = med
                cand[pos] = h
                c = dg_pam_cost(D, cand, w)
                if (c < best-1e-12) {
                    best = c
                    bestmed = cand
                    improved = 1
                }
            }
        }
        if (improved) {
            med = bestmed
            current = best
        }
    } while (improved)
    return(med)
}

real rowvector dg_pam_build(real matrix D, real scalar k, real colvector w)
{
    real rowvector med, costs
    real scalar j, b
    real colvector dmin

    costs = w' * D
    med = dg_argmin(costs)
    dmin = D[med[1],.]'
    while (cols(med) < k) {
        costs = J(1,rows(D),.)
        for (j=1; j<=rows(D); j++) {
            if (sum(med:==j)) continue
            costs[j] = sum(w :* rowmin((dmin, D[j,.]')))
        }
        b = dg_argmin(costs)
        med = med, b
        dmin = rowmin((dmin, D[b,.]'))
    }
    return(med)
}

real colvector dg_pam_cut(real matrix Z, real colvector w, real scalar k,
    string scalar metric, real scalar restarts)
{
    real matrix D
    real rowvector med, cand, ord
    real colvector lab
    real scalar r, best, c, i, g

    D = dg_distances(Z, metric)
    med = dg_pam_swap(D, dg_pam_build(D,k,w), w)
    best = dg_pam_cost(D,med,w)
    for (r=1; r<=restarts; r++) {
        ord = order(runiform(rows(D),1),1)'
        cand = dg_pam_swap(D, ord[1..k], w)
        c = dg_pam_cost(D,cand,w)
        if (c < best-1e-12) {
            med = cand
            best = c
        }
    }

    lab = J(rows(D),1,.)
    for (i=1; i<=rows(D); i++) {
        g = 1
        for (r=2; r<=cols(med); r++) if (D[med[r],i] < D[med[g],i]) g = r
        lab[i] = g
    }
    return(dg_relabel(lab,w))
}

void dg_cluster_store(string rowvector vars, string scalar weightvar,
    string scalar outvar, real scalar k, string scalar method,
    string scalar metric, real scalar restarts)
{
    real matrix X, Z
    real colvector w, lab
    real scalar weighted

    X = st_data(., vars)
    if (weightvar == "") {
        w = J(rows(X),1,1)
        weighted = 0
    }
    else {
        w = st_data(., weightvar)
        weighted = 1
    }
    if (hasmissing(X) | hasmissing(w) | min(w)<=0) {
        errprintf("Datos no finitos o pesos no positivos en dg_cluster.\n")
        exit(459)
    }

    Z = dg_standardize(X,w,weighted)
    if (method == "ward") lab = dg_ward_cut(Z,w,k)
    else lab = dg_pam_cut(Z,w,k,metric,restarts)
    st_store(., st_varindex(outvar), lab)
}

real rowvector dg_rand(real matrix AB)
{
    real colvector a, b, ga, gb
    real scalar i, j, n, total, agree, sij, si, sj, ni, nj, nij, expected, maximum
    a = AB[,1]
    b = AB[,2]
    n = rows(a)
    total = n*(n-1)/2
    agree = 0
    for (i=1; i<n; i++) for (j=i+1; j<=n; j++) ///
        agree = agree + ((a[i]==a[j])==(b[i]==b[j]))

    ga = uniqrows(sort(a,1))
    gb = uniqrows(sort(b,1))
    si = sj = sij = 0
    for (i=1; i<=rows(ga); i++) {
        ni = sum(a:==ga[i])
        si = si + ni*(ni-1)/2
    }
    for (j=1; j<=rows(gb); j++) {
        nj = sum(b:==gb[j])
        sj = sj + nj*(nj-1)/2
    }
    for (i=1; i<=rows(ga); i++) for (j=1; j<=rows(gb); j++) {
        nij = sum((a:==ga[i]) :& (b:==gb[j]))
        sij = sij + nij*(nij-1)/2
    }
    expected = si*sj/total
    maximum = (si+sj)/2
    return((agree/total, (sij-expected)/(maximum-expected)))
}

real scalar dg_eta2_fun(real colvector y, real colvector cl, real colvector w)
{
    real scalar mu, total, between, g, mg
    real colvector grupos, hit
    mu = (w'*y)/sum(w)
    total = sum(w:*(y:-mu):^2)
    grupos = uniqrows(sort(cl,1))
    between = 0
    for (g=1; g<=rows(grupos); g++) {
        hit = cl:==grupos[g]
        mg = (select(w,hit)'*select(y,hit))/sum(select(w,hit))
        between = between + sum(select(w,hit))*(mg-mu)^2
    }
    return(between/total)
}

end


* =============================================================================
* 1. Preparación: insumo completo y subconjuntos que efectivamente agrupó la UAM
* =============================================================================

tempfile insumo full1 full2 bench1 bench2 clas1 clas2 cobre1 cobre2

import excel using "$D_UAM_INSUMO", sheet("Hoja1") firstrow clear
capture destring codigo_3dig, replace
isid periodo codigo_3dig
assert inlist(periodo,1,2)
save "`insumo'", replace

use "`insumo'", clear
keep if periodo == 1
isid codigo_3dig
save "`full1'", replace

use "`insumo'", clear
keep if periodo == 2
isid codigo_3dig
save "`full2'", replace

import excel using "$D_UAM_HCLUST1", sheet("sectores_cluster") firstrow clear
capture destring codigo_3dig, replace
rename cluster cluster_uam
foreach v of local VARS_UAM {
    rename `v' uam_`v'
}
keep codigo_3dig cluster_uam uam_*
isid codigo_3dig
save "`bench1'", replace

import excel using "$D_UAM_HCLUST2", sheet("sectores_cluster") firstrow clear
capture destring codigo_3dig, replace
rename cluster cluster_uam
foreach v of local VARS_UAM {
    rename `v' uam_`v'
}
keep codigo_3dig cluster_uam uam_*
isid codigo_3dig
save "`bench2'", replace

use "`full1'", clear
merge 1:1 codigo_3dig using "`bench1'", keep(match) nogen
save "`clas1'", replace

use "`full2'", clear
merge 1:1 codigo_3dig using "`bench2'", keep(match) nogen
save "`clas2'", replace

* Universo para las extensiones: lo clasificado por la UAM + sólo el cobre.
foreach p in 1 2 {
    if `p' == 1 {
        use "`full1'", clear
        merge 1:1 codigo_3dig using "`bench1'", keep(master match)
    }
    else {
        use "`full2'", clear
        merge 1:1 codigo_3dig using "`bench2'", keep(master match)
    }
    generate byte en_uam = _merge == 3
    generate byte es_cobre = strpos(ustrlower(desc), "cobre") > 0
    count if !en_uam & es_cobre
    assert r(N) == 1
    keep if en_uam | es_cobre
    drop _merge
    if `p' == 1 save "`cobre1'", replace
    else save "`cobre2'", replace
}


* =============================================================================
* 2. RÉPLICA EXACTA DEL WARD RECIBIDO
*    Único cambio respecto de las planillas: el cálculo se hace en Stata/Mata.
* =============================================================================

display as text _n "{hline 78}"
display as result "1. Réplica del Ward original de la UAM"
display as text "Siete variables, z muestral, Ward-euclidiano, sin peso; k=4/2."
display as text "{hline 78}"

foreach p in 1 2 {
    if `p' == 1 {
        use "`clas1'", clear
        local K 4
        local ANIO 2003
    }
    else {
        use "`clas2'", clear
        local K 2
        local ANIO 2023
    }

    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_z_muestral `VARS_UAM', prefix(st_)

    local MAXERR 0
    foreach v of local VARS_UAM {
        generate double __err = abs(st_`v' - uam_`v')
        quietly summarize __err, meanonly
        local MAXERR = max(`MAXERR', r(max))
        drop __err
    }

    dg_cluster `VARS_UAM', generate(c_replica) k(`K') method(ward)
    dg_comparar cluster_uam c_replica

    display as result _n "Chile `ANIO': " _N " actividades"
    display as text "  error máximo en z = " %10.3e `MAXERR'
    display as text "  Rand = " %7.4f r(rand) " · ARI = " %7.4f r(ari)
    assert `MAXERR' < 1e-9
    assert abs(r(ari)-1) < 1e-12
    tabulate cluster_uam c_replica, missing
}

if `PAUSAR' pause "Fin de la réplica. Escriba q para seguir al cobre."


* =============================================================================
* 3. WARD CHILE CON COBRE
*    Se conserva el universo de la UAM y se devuelve sólo el cobre. k=4 en ambos
*    años para que el cobre y los grupos restantes puedan verse por separado.
* =============================================================================

display as text _n "{hline 78}"
display as result "2. Ward de Chile con el cobre reincorporado"
display as text "Misma especificación original; único cambio: vuelve el cobre; k=4."
display as text "{hline 78}"

foreach p in 1 2 {
    if `p' == 1 {
        use "`cobre1'", clear
        local ANIO 2003
    }
    else {
        use "`cobre2'", clear
        local ANIO 2023
    }
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_ward_cobre) k(4) method(ward)
    dg_resumen, cluster(c_ward_cobre) ///
        titulo("Chile `ANIO' · Ward original + cobre · k=4")
    gsort c_ward_cobre -empleo
    list codigo_3dig desc empleo if es_cobre | _n<=8, ///
        sepby(c_ward_cobre) noobs abbreviate(52)
}

if `PAUSAR' pause "Fin del Ward con cobre. Escriba q para iniciar sensibilidades."


* =============================================================================
* 4. VARIACIONES, UNA POR UNA
* =============================================================================

foreach p in 1 2 {
    if `p' == 1 {
        local BASE "`cobre1'"
        local FULL "`full1'"
        local CLAS "`clas1'"
        local ANIO 2003
    }
    else {
        local BASE "`cobre2'"
        local FULL "`full2'"
        local CLAS "`clas2'"
        local ANIO 2023
    }

    display as text _n _n "{hline 78}"
    display as result "SENSIBILIDADES · CHILE `ANIO'"
    display as text "Cada apartado recarga la misma base UAM + cobre."
    display as text "{hline 78}"

    * -------------------------------------------------------------------------
    * 4.1. Sacar UNA variable a la vez. No cambia algoritmo, geometría, niveles,
    *      peso, universo ni k. El ARI se calcula contra las siete variables.
    * -------------------------------------------------------------------------
    display as result _n "4.1. Exclusión de una variable a la vez"
    use "`BASE'", clear
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_siete) k(4) method(ward)

    local j 0
    foreach omit of local VARS_UAM {
        local ++j
        local seis : list VARS_UAM - omit
        dg_cluster `seis', generate(c_sin`j') k(4) method(ward)
        dg_comparar c_siete c_sin`j'
        display as text "  sin `omit'" _col(43) ///
            "Rand=" %6.3f r(rand) "  ARI=" %7.3f r(ari)
    }
    if `PAUSAR' pause "Fin de quitar variables. Escriba q para comercio."

    * -------------------------------------------------------------------------
    * 4.2. Mínima corrección comercial: sólo normalizar el saldo por VBP. Las
    *      otras seis columnas permanecen intactas.
    * -------------------------------------------------------------------------
    display as result _n "4.2. Balanza comercial: nivel -> (X-M)/VBP"
    use "`BASE'", clear
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_bal_nivel) k(4) method(ward)
    dg_variables, balanza(vbp) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_bal_vbp) k(4) method(ward)
    dg_comparar c_bal_nivel c_bal_vbp
    display as text "  ARI respecto del saldo en niveles = " %7.3f r(ari)
    dg_resumen, cluster(c_bal_vbp) ///
        titulo("Chile `ANIO' · sólo balanza/VBP · Ward k=4")
    if `PAUSAR' pause "Fin de balanza/VBP. Escriba q para reparametrización."

    * -------------------------------------------------------------------------
    * 4.3. Reparametrizar comercio: tres columnas parcialmente redundantes pasan
    *      a dos dimensiones: apertura (X+M)/VBP y saldo (X-M)/(X+M).
    * -------------------------------------------------------------------------
    display as result _n "4.3. Reparametrización: apertura + balanza relativa"
    use "`BASE'", clear
    dg_variables, balanza(norm) comercio(1) logs(0)
    dg_cluster `VARS_COMERCIO', generate(c_comercio) k(4) method(ward)
    dg_resumen, cluster(c_comercio) ///
        titulo("Chile `ANIO' · comercio reparametrizado · Ward k=4")
    if `PAUSAR' pause "Fin de comercio. Escriba q para logaritmos."

    * -------------------------------------------------------------------------
    * 4.4. Logaritmos SIN peso: cambia sólo la forma de las variables; mantiene
    *      las siete dimensiones y el saldo en niveles. Es una sensibilidad, no
    *      la especificación recomendada para comparar los dos años.
    * -------------------------------------------------------------------------
    display as result _n "4.4. Transformaciones logarítmicas, sin ponderar"
    use "`BASE'", clear
    dg_variables, balanza(nivel) comercio(0) logs(1)
    dg_cluster `VARS_UAM', generate(c_logs) k(4) method(ward)
    dg_resumen, cluster(c_logs) ///
        titulo("Chile `ANIO' · logs sin peso · Ward k=4")
    if `PAUSAR' pause "Fin de logs. Escriba q para ponderación."

    * -------------------------------------------------------------------------
    * 4.5. Ponderar por empleo, primero dejando la balanza en niveles. El peso
    *      entra en los momentos z Y en la masa del criterio de Ward.
    * -------------------------------------------------------------------------
    display as result _n "4.5. Ponderación por empleo, balanza todavía en niveles"
    use "`BASE'", clear
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_peso) k(4) method(ward) weightvar(empleo)
    dg_resumen, cluster(c_peso) ///
        titulo("Chile `ANIO' · peso de empleo · Ward k=4")

    * Combinación necesaria para la invariancia a clones: peso + saldo intensivo.
    display as result _n "4.5b. Ponderación + balanza/VBP"
    dg_variables, balanza(vbp) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_peso_bal) k(4) method(ward) weightvar(empleo)
    dg_resumen, cluster(c_peso_bal) ///
        titulo("Chile `ANIO' · peso + balanza/VBP · Ward k=4")
    if `PAUSAR' pause "Fin de ponderación. Escriba q para PAM."

    * -------------------------------------------------------------------------
    * 4.6. PAM: primero cambia sólo el algoritmo (PAM euclidiano); después sólo
    *      la métrica dentro de PAM (Manhattan). Ninguna otra corrección entra.
    * -------------------------------------------------------------------------
    display as result _n "4.6. PAM: algoritmo y métrica por separado"
    use "`BASE'", clear
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_ward_ref) k(4) method(ward)
    dg_cluster `VARS_UAM', generate(c_pam_euc) k(4) method(pam) ///
        metric(euclidean) restarts(50)
    dg_cluster `VARS_UAM', generate(c_pam_man) k(4) method(pam) ///
        metric(manhattan) restarts(50)
    dg_comparar c_ward_ref c_pam_euc
    display as text "  Ward euclidiano vs PAM euclidiano: ARI = " %7.3f r(ari)
    dg_comparar c_pam_euc c_pam_man
    display as text "  PAM euclidiano vs PAM Manhattan: ARI = " %7.3f r(ari)
    dg_resumen, cluster(c_pam_man) ///
        titulo("Chile `ANIO' · PAM Manhattan sin ajustes · k=4")
    if `PAUSAR' pause "Fin de PAM sin ajustes. Escriba q para PAM ponderado."

    * -------------------------------------------------------------------------
    * 4.7. PAM + ponderación + balanza relativa, SIN logs. Ésta es la combinación
    *      que, en el diagnóstico posterior, mantuvo al cobre en el enclave.
    * -------------------------------------------------------------------------
    display as result _n "4.7. PAM Manhattan + peso + balanza relativa, sin logs"
    use "`BASE'", clear
    dg_variables, balanza(norm) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_pam_peso) k(4) method(pam) ///
        metric(manhattan) weightvar(empleo) restarts(50)
    dg_resumen, cluster(c_pam_peso) ///
        titulo("Chile `ANIO' · PAM Manhattan + peso + balanza relativa · k=4")

    * La variante con logs se muestra aparte porque fue probada y luego se vio
    * que, en Chile 2003, comprimía precisamente las dimensiones del cobre.
    display as result _n "4.7b. La misma combinación, ahora CON logs"
    dg_variables, balanza(norm) comercio(0) logs(1)
    dg_cluster `VARS_UAM', generate(c_pam_todo) k(4) method(pam) ///
        metric(manhattan) weightvar(empleo) restarts(50)
    dg_comparar c_pam_peso c_pam_todo
    display as text "  Efecto de agregar logs a PAM ponderado: ARI = " %7.3f r(ari)
    dg_resumen, cluster(c_pam_todo) ///
        titulo("Chile `ANIO' · PAM + peso + balanza relativa + logs · k=4")
    if `PAUSAR' pause "Fin de PAM combinado. Escriba q para universo."

    * -------------------------------------------------------------------------
    * 4.8. Sensibilidad al universo: misma especificación Ward original, ahora
    *      sobre TODA la COU. No se mezcla con ninguna otra corrección.
    * -------------------------------------------------------------------------
    display as result _n "4.8. Universo sectorial: COU completa"
    use "`FULL'", clear
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_full) k(4) method(ward)
    dg_resumen, cluster(c_full) ///
        titulo("Chile `ANIO' · COU completa · Ward original k=4")
    generate byte es_cobre_full = strpos(ustrlower(desc), "cobre") > 0
    list codigo_3dig desc c_full empleo if es_cobre_full, noobs
    if `PAUSAR' pause "Fin de universo. Escriba q para elección de k."

    * -------------------------------------------------------------------------
    * 4.9. Elección de k: se fija la especificación y recién entonces se recorre
    *      k. Se muestra η² del log de productividad ponderado por empleo.
    * -------------------------------------------------------------------------
    display as result _n "4.9. k = 3, 4 y 5, condicional a la especificación"
    use "`BASE'", clear
    generate double __lnprod = ln(valor_agrega / empleo)
    dg_variables, balanza(nivel) comercio(0) logs(0)
    foreach K in 3 4 5 {
        dg_cluster `VARS_UAM', generate(c_w`K') k(`K') method(ward)
        dg_eta2, cluster(c_w`K') weight(empleo) outcome(__lnprod)
        display as text "  Ward original, k=`K': eta2(log productividad) = " ///
            %7.3f r(eta2)
    }
    dg_variables, balanza(nivel) comercio(0) logs(0)
    foreach K in 3 4 5 {
        dg_cluster `VARS_UAM', generate(c_m`K') k(`K') method(pam) ///
            metric(manhattan) restarts(50)
        dg_eta2, cluster(c_m`K') weight(empleo) outcome(__lnprod)
        display as text "  PAM Manhattan sin ajustes, k=`K': eta2 = " %7.3f r(eta2)
    }
    if `PAUSAR' pause "Fin de k. Escriba q para unidad de observación."

    * -------------------------------------------------------------------------
    * 4.10. Agregar manufactura a ocho grupos. Se suman MAGNITUDES y se vuelven
    *       a calcular los ratios: nunca se promedian directamente los ratios.
    * -------------------------------------------------------------------------
    display as result _n "4.10. Unidad de observación: manufactura en ocho grupos"
    use "`CLAS'", clear
    generate str80 unidad = "ACT " + string(codigo_3dig)
    if `p' == 2 {
        replace unidad = "MANUF Alimentos" if inrange(codigo_3dig,19,29)
        replace unidad = "MANUF Bebidas" if inrange(codigo_3dig,30,33)
        replace unidad = "MANUF Textil, vestuario, cuero y calzado" if inrange(codigo_3dig,35,38)
        replace unidad = "MANUF Madera, celulosa, papel e imprentas" if inrange(codigo_3dig,39,44)
        replace unidad = "MANUF Química" if inrange(codigo_3dig,46,50)
        replace unidad = "MANUF Plástico y minerales no metálicos" if inrange(codigo_3dig,52,55)
        replace unidad = "MANUF Metálicas básicas y productos metálicos" if inrange(codigo_3dig,56,58)
        replace unidad = "MANUF Muebles, otras manufacturas y reparación" if inlist(codigo_3dig,62,63)
    }
    else {
        replace unidad = "MANUF Alimentos" if inrange(codigo_3dig,11,18) | codigo_3dig==20
        replace unidad = "MANUF Bebidas" if inrange(codigo_3dig,21,24)
        replace unidad = "MANUF Textil, vestuario, cuero y calzado" if inrange(codigo_3dig,26,29)
        replace unidad = "MANUF Madera, celulosa, papel e imprentas" if inrange(codigo_3dig,30,32)
        replace unidad = "MANUF Química" if inlist(codigo_3dig,34,35)
        replace unidad = "MANUF Plástico y minerales no metálicos" if inrange(codigo_3dig,37,39)
        replace unidad = "MANUF Metálicas básicas y productos metálicos" if inrange(codigo_3dig,40,42)
        replace unidad = "MANUF Muebles y otras manufacturas" if inlist(codigo_3dig,46,47)
    }
    collapse (sum) `SUMABLES' (count) n_actividades=codigo_3dig, by(unidad)
    generate long codigo_3dig = _n
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_manuf8) k(4) method(ward)
    dg_resumen, cluster(c_manuf8) ///
        titulo("Chile `ANIO' · manufactura agregada en 8 · Ward k=4")
    if `PAUSAR' pause "Fin de agregación. Escriba q para prueba de clones."

    * -------------------------------------------------------------------------
    * 4.11. Prueba limpia de clones. Partir las cinco actividades de mayor empleo
    *       en tres copias idénticas no cambia la economía. Se contrasta:
    *       a) Ward original sin ponderar;
    *       b) Ward con empleo + balanza/VBP.
    * -------------------------------------------------------------------------
    display as result _n "4.11. Invariancia a una desagregación proporcional"
    tempfile orig`p' clones`p'

    use "`CLAS'", clear
    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_orig_sin) k(4) method(ward)
    dg_variables, balanza(vbp) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_orig_pond) k(4) method(ward) weightvar(empleo)
    keep codigo_3dig c_orig_sin c_orig_pond
    save "`orig`p''", replace

    use "`CLAS'", clear
    gsort -empleo codigo_3dig
    generate byte __veces = cond(_n<=5,3,1)
    expand __veces
    bysort codigo_3dig: generate byte __clon = _n
    foreach v of local SUMABLES {
        replace `v' = `v' / __veces
    }

    dg_variables, balanza(nivel) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_clone_sin) k(4) method(ward)
    dg_variables, balanza(vbp) comercio(0) logs(0)
    dg_cluster `VARS_UAM', generate(c_clone_pond) k(4) method(ward) weightvar(empleo)

    keep if __clon == 1
    merge 1:1 codigo_3dig using "`orig`p''", assert(match) nogen
    dg_comparar c_orig_sin c_clone_sin
    display as text "  sin ponderar: ARI original vs clones = " %7.3f r(ari)
    dg_comparar c_orig_pond c_clone_pond
    display as text "  peso + balanza/VBP: ARI original vs clones = " %7.3f r(ari)
    if `PAUSAR' pause "Fin de Chile `ANIO'. Escriba q para continuar."
}


display as text _n "{hline 78}"
display as result "Do-file terminado."
display as text "El log completo quedó en: $SCRATCH/log_conglomerados_chile_stata.txt"
display as text "Las particiones deben leerse como sensibilidades, no como una única verdad."
display as text "{hline 78}"

log close cluster_chile

