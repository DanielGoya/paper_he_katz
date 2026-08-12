#requires -Version 5.1
# Crea (o actualiza) el entorno virtual de este repo en .venv. Idempotente: si el
# venv ya existe, solo sincroniza las dependencias.
#
# POR QUE EXISTE. Los scripts de py/ se invocan por RUTA (.venv\Scripts\python.exe)
# y nunca por el nombre `python`. `python` a secas es "lo que este primero en el
# PATH hoy", y eso lo cambia cualquier instalador. El venv fija interprete Y
# version sin tocar el PATH. Misma convencion que gestor_de_proyectos.
#
# El resto del repo es Stata y no depende de esto: run_analisis.ps1 corre sin venv.
#
# Mensajes sin acentos a proposito: PowerShell 5.1 lee mal UTF-8 sin BOM.

[CmdletBinding()]
param(
    # Borra el venv y lo vuelve a crear desde cero (por ejemplo, para cambiar de
    # version de Python).
    [switch]$Recrear
)

# 'Continue' a proposito, no 'Stop'. Con 'Stop', PowerShell 5.1 convierte en
# NativeCommandError terminante cualquier linea que uv o pip escriban en stderr
# —uv anuncia ahi el interprete que eligio— y aborta el script aunque el comando
# haya salido con codigo 0. Verificado en ESCRITORIO el 2026-08-12. El control de
# errores va por $LASTEXITCODE, que ya estaba en cada llamada.
$ErrorActionPreference = 'Continue'

# Version del interprete FIJADA para este repo. Vive aca, no en el PATH.
$VersionPython = '3.14'

$repo = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $repo '.venv'
$py   = Join-Path $venv 'Scripts\python.exe'
$reqs = Join-Path $repo 'requirements.txt'

if ($Recrear -and (Test-Path -LiteralPath $venv)) {
    Write-Host "== Borrando el venv existente en $venv"
    Remove-Item -LiteralPath $venv -Recurse -Force
}

$uv = Get-Command uv -ErrorAction SilentlyContinue

if (-not (Test-Path -LiteralPath $py)) {
    # Una corrida abortada deja el directorio a medio armar, y uv se niega a
    # escribir encima ("A directory already exists"). Si hay directorio pero no
    # interprete, el entorno esta incompleto y se descarta.
    if (Test-Path -LiteralPath $venv) {
        Write-Host "== Entorno incompleto en $venv : se descarta y se rehace"
        Remove-Item -LiteralPath $venv -Recurse -Force
    }
    Write-Host "== Creando .venv con Python $VersionPython"
    if ($uv) {
        & uv venv --python $VersionPython $venv
    } else {
        & py "-$VersionPython" -m venv $venv
    }
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno en $venv." }
}

if (-not (Test-Path -LiteralPath $py)) {
    throw "El entorno quedo incompleto: falta $py."
}

$versionReal = (& $py -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
if ($versionReal -ne $VersionPython) {
    Write-Warning "El venv es Python $versionReal y este repo fija $VersionPython. Volver a correr con -Recrear."
}

if (Test-Path -LiteralPath $reqs) {
    Write-Host "== Instalando dependencias de requirements.txt"
    if ($uv) {
        & uv pip install --python $py -r $reqs
    } else {
        & $py -m pip install --upgrade -r $reqs
    }
    if ($LASTEXITCODE -ne 0) { throw "La instalacion de dependencias fallo." }
}

Write-Host ''
Write-Host "Entorno listo: $py (Python $versionReal)" -ForegroundColor Green
Write-Host 'Los scripts de py/ lo usan por ruta absoluta; no hace falta activarlo.'
