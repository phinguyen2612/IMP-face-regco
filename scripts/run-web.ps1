param([string]$BindAddress = '127.0.0.1', [string]$PublicOrigin = '')

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location (Join-Path $root 'apps/web')
if (-not (Test-Path -LiteralPath 'node_modules')) { throw 'Run .\scripts\setup-local.ps1 first; web dependencies are missing.' }
$env:FR_DEV_API_URL = 'http://127.0.0.1:8000'
if ($PublicOrigin) { $env:FR_PREVIEW_PUBLIC_ORIGIN = $PublicOrigin }
& npm run dev -- --host $BindAddress --strictPort
if ($LASTEXITCODE -ne 0) { throw "Web development server stopped with exit code $LASTEXITCODE." }
