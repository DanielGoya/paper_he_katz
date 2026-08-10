# run_analisis.ps1 — sincroniza el repositorio y corre el pipeline completo.
# Es el punto de entrada del acceso directo «Análisis HE Katz» de la carpeta padre.

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

Write-Host "== Sincronizando el repositorio ==" -ForegroundColor Cyan
$tieneRemoto = (git remote) -ne $null -and (git remote).Count -gt 0
if ($tieneRemoto) {
    git pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "El git pull falló. Revisar conflictos, autenticación o divergencia" -ForegroundColor Red
        Write-Host "ANTES de correr el análisis: el código podría estar desactualizado." -ForegroundColor Red
        Read-Host "Enter para cerrar"
        exit 1
    }
} else {
    Write-Host "El repositorio no tiene remoto configurado; se salta el pull." -ForegroundColor Yellow
}

# Stata: se busca la instalación disponible, de la más nueva a la más antigua
$candidatos = @(
    "C:\Program Files\Stata18\StataMP-64.exe",
    "C:\Program Files\Stata17\StataMP-64.exe",
    "C:\Program Files (x86)\Stata15\StataMP-64.exe"
)
$stata = $candidatos | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $stata) {
    Write-Host "No se encontró Stata en ninguna de las rutas conocidas." -ForegroundColor Red
    Read-Host "Enter para cerrar"
    exit 1
}

Write-Host "== Corriendo el pipeline con $stata ==" -ForegroundColor Cyan
Write-Host "Toma entre 15 y 25 minutos. El log va quedando en datos\scratch\log_master.txt"

$master = Join-Path $repo "src\00_master.do"
$p = Start-Process -FilePath $stata -ArgumentList '/e','do',"`"$master`"" `
                   -WorkingDirectory $repo -PassThru -Wait

if ($p.ExitCode -eq 0) {
    Write-Host "Listo. Las salidas quedaron en el arbol de artefactos del proyecto." -ForegroundColor Green
} else {
    Write-Host "Stata terminó con código $($p.ExitCode). Revisar el log." -ForegroundColor Red
}
Read-Host "Enter para cerrar"
