<#
.SYNOPSIS
    Inicia o dashboard Lab05 (Streamlit) e expõe publicamente via Cloudflare Tunnel.

.DESCRIPTION
    1. Ativa o virtualenv do Lab05
    2. Inicia o Streamlit em background na porta 8505
    3. Aguarda o Streamlit estar pronto
    4. Inicia cloudflared quick-tunnel apontando para http://localhost:8505
    5. Exibe a URL pública gerada pelo Cloudflare

.NOTES
    Use Stop-Lab05.ps1 para encerrar os processos.
    PIDs são salvos em .pids para uso pelo script de parada.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$LabDir     = $PSScriptRoot
$PidFile    = Join-Path $LabDir ".pids"
$VenvPython = Join-Path $LabDir ".venv\Scripts\python.exe"
$Port       = 8505

# ── Verificações iniciais ─────────────────────────────────────────────────────
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtualenv não encontrado em '$VenvPython'. Crie o venv e instale os requisitos:
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Error "cloudflared não encontrado no PATH. Instale em https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/"
    exit 1
}

# ── Impede duplo start ────────────────────────────────────────────────────────
if (Test-Path $PidFile) {
    Write-Warning "Lab05 parece já estar em execução (arquivo .pids encontrado)."
    Write-Warning "Execute Stop-Lab05.ps1 primeiro ou remova '$PidFile' manualmente."
    exit 1
}

# ── Inicia Streamlit ──────────────────────────────────────────────────────────
Write-Host ">> Iniciando Streamlit na porta $Port..." -ForegroundColor Cyan

$streamlitArgs = @(
    "-m", "streamlit", "run",
    (Join-Path $LabDir "dashboard.py"),
    "--server.port", $Port,
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false"
)

$streamlitProc = Start-Process -FilePath $VenvPython `
    -ArgumentList $streamlitArgs `
    -WorkingDirectory $LabDir `
    -PassThru -WindowStyle Hidden

Write-Host "   Streamlit PID: $($streamlitProc.Id)" -ForegroundColor Green

# ── Aguarda Streamlit estar pronto ────────────────────────────────────────────
Write-Host ">> Aguardando Streamlit inicializar..." -ForegroundColor Cyan
$maxWait = 30
$elapsed = 0
do {
    Start-Sleep -Seconds 1
    $elapsed++
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$Port" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        break
    } catch { }
} while ($elapsed -lt $maxWait)

if ($elapsed -ge $maxWait) {
    Write-Warning "Streamlit demorou mais de ${maxWait}s para responder. Verifique o processo manualmente."
}

# ── Inicia Cloudflare Tunnel ──────────────────────────────────────────────────
Write-Host ">> Iniciando Cloudflare Tunnel..." -ForegroundColor Cyan

$cfLogFile = Join-Path $LabDir ".cloudflared.log"
$cfProc = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://localhost:$Port" `
    -RedirectStandardError $cfLogFile `
    -PassThru -WindowStyle Hidden

Write-Host "   cloudflared PID: $($cfProc.Id)" -ForegroundColor Green

# ── Aguarda URL pública ───────────────────────────────────────────────────────
Write-Host ">> Aguardando URL pública do Cloudflare..." -ForegroundColor Cyan
$publicUrl = $null
$waited = 0
while (-not $publicUrl -and $waited -lt 20) {
    Start-Sleep -Seconds 1
    $waited++
    if (Test-Path $cfLogFile) {
        $logContent = Get-Content $cfLogFile -Raw -ErrorAction SilentlyContinue
        if ($logContent -match "https://[a-z0-9\-]+\.trycloudflare\.com") {
            $publicUrl = $Matches[0]
        }
    }
}

# ── Salva PIDs ────────────────────────────────────────────────────────────────
@{
    StreamlitPid   = $streamlitProc.Id
    CloudflaredPid = $cfProc.Id
} | ConvertTo-Json | Set-Content $PidFile

# ── Resultado ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "======================================================" -ForegroundColor Yellow
Write-Host " Lab05 – GraphQL vs REST Dashboard" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Yellow
Write-Host " Local : http://localhost:$Port" -ForegroundColor Green
if ($publicUrl) {
    Write-Host " Público: $publicUrl" -ForegroundColor Green
} else {
    Write-Host " URL pública: verifique '$cfLogFile'" -ForegroundColor Yellow
}
Write-Host "======================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Execute Stop-Lab05.ps1 para encerrar." -ForegroundColor Cyan
