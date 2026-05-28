<#
.SYNOPSIS
    Para o dashboard Lab04 (Streamlit) e o Cloudflare Tunnel.

.DESCRIPTION
    Lê os PIDs salvos por Start-Lab04.ps1 e encerra os processos
    Streamlit e cloudflared. Remove os arquivos temporários (.pids, .cloudflared.log).
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "SilentlyContinue"

$LabDir  = $PSScriptRoot
$PidFile = Join-Path $LabDir ".pids"
$CfLog   = Join-Path $LabDir ".cloudflared.log"

if (-not (Test-Path $PidFile)) {
    Write-Warning "Arquivo .pids não encontrado. Lab04 não parece estar em execução."
    exit 0
}

$pids = Get-Content $PidFile -Raw | ConvertFrom-Json

# ── Para Streamlit ────────────────────────────────────────────────────────────
if ($pids.StreamlitPid) {
    $proc = Get-Process -Id $pids.StreamlitPid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $pids.StreamlitPid -Force
        Write-Host ">> Streamlit (PID $($pids.StreamlitPid)) encerrado." -ForegroundColor Cyan
    } else {
        Write-Host ">> Streamlit (PID $($pids.StreamlitPid)) já não estava em execução." -ForegroundColor Gray
    }
}

# ── Para cloudflared ──────────────────────────────────────────────────────────
if ($pids.CloudflaredPid) {
    $proc = Get-Process -Id $pids.CloudflaredPid -ErrorAction SilentlyContinue
    if ($proc) {
        Stop-Process -Id $pids.CloudflaredPid -Force
        Write-Host ">> cloudflared (PID $($pids.CloudflaredPid)) encerrado." -ForegroundColor Cyan
    } else {
        Write-Host ">> cloudflared (PID $($pids.CloudflaredPid)) já não estava em execução." -ForegroundColor Gray
    }
}

# Garantia: mata qualquer processo cloudflared remanescente
Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force

# ── Limpa arquivos temporários ────────────────────────────────────────────────
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
Remove-Item $CfLog   -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Lab04 encerrado com sucesso." -ForegroundColor Green
