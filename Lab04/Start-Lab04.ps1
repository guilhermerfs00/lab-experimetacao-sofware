<#
.SYNOPSIS
    Inicia o dashboard Lab04 (Streamlit) e expõe publicamente via Cloudflare Tunnel.

.DESCRIPTION
    1. Ativa o virtualenv do Lab04
    2. Inicia o Streamlit em background na porta 8501
    3. Aguarda o Streamlit estar pronto
    4. Inicia cloudflared quick-tunnel apontando para http://localhost:8501
    5. Exibe a URL pública gerada pelo Cloudflare

.NOTES
    Use Stop-Lab04.ps1 para encerrar os processos.
    PIDs são salvos em .pids para uso pelo script de parada.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"   # apenas durante a inicialização

$LabDir    = $PSScriptRoot
$PidFile   = Join-Path $LabDir ".pids"
$VenvPython = Join-Path $LabDir ".venv\Scripts\python.exe"
$Port      = 8501

# ── Verificações iniciais ─────────────────────────────────────────────────────
if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtualenv não encontrado em '$VenvPython'. Execute 'pip install -r requirements.txt' em um venv antes."
    exit 1
}

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Error "cloudflared não encontrado no PATH. Instale em https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/"
    exit 1
}

# ── Impede duplo start ────────────────────────────────────────────────────────
if (Test-Path $PidFile) {
    Write-Warning "Lab04 parece já estar em execução (arquivo .pids encontrado)."
    Write-Warning "Execute Stop-Lab04.ps1 primeiro ou remova '$PidFile' manualmente."
    exit 1
}

# ── Inicia Streamlit ──────────────────────────────────────────────────────────
Write-Host ">> Iniciando Streamlit na porta $Port..." -ForegroundColor Cyan

$streamlitArgs = @(
    "-m", "streamlit", "run",
    (Join-Path $LabDir "dashboard.py"),
    "--server.port", $Port,
    "--server.headless", "true",
    "--server.address", "127.0.0.1"
)

$streamlitProc = Start-Process `
    -FilePath $VenvPython `
    -ArgumentList $streamlitArgs `
    -WorkingDirectory $LabDir `
    -PassThru `
    -WindowStyle Hidden

Write-Host "   PID Streamlit: $($streamlitProc.Id)" -ForegroundColor Green

# ── Aguarda Streamlit responder ───────────────────────────────────────────────
Write-Host ">> Aguardando Streamlit inicializar..." -ForegroundColor Cyan
$maxWait  = 30   # segundos
$interval = 2
$elapsed  = 0
$ready    = $false

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds $interval
    $elapsed += $interval
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Write-Host "   Aguardando... ($elapsed/$maxWait s)" -ForegroundColor Gray
}

if (-not $ready) {
    Write-Error "Streamlit não respondeu em $maxWait segundos. Verifique erros acima."
    Stop-Process -Id $streamlitProc.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "   Streamlit pronto em http://127.0.0.1:$Port" -ForegroundColor Green

# ── Inicia cloudflared quick-tunnel ──────────────────────────────────────────
Write-Host ">> Iniciando Cloudflare Tunnel..." -ForegroundColor Cyan

$cfLogFile = Join-Path $LabDir ".cloudflared.log"
if (Test-Path $cfLogFile) { Remove-Item $cfLogFile -Force }

$cfProc = Start-Process `
    -FilePath "cloudflared" `
    -ArgumentList "tunnel", "--url", "http://127.0.0.1:$Port" `
    -RedirectStandardError $cfLogFile `
    -PassThru `
    -WindowStyle Hidden

Write-Host "   PID cloudflared: $($cfProc.Id)" -ForegroundColor Green

# ── Aguarda URL pública ───────────────────────────────────────────────────────
Write-Host ">> Aguardando URL pública do Cloudflare..." -ForegroundColor Cyan
$maxWait = 30
$elapsed = 0
$publicUrl = $null

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    if (Test-Path $cfLogFile) {
        $logContent = Get-Content $cfLogFile -Raw -ErrorAction SilentlyContinue
        if ($logContent -match 'https://[a-z0-9\-]+\.trycloudflare\.com') {
            $publicUrl = $Matches[0]
            break
        }
    }
    Write-Host "   Aguardando URL... ($elapsed/$maxWait s)" -ForegroundColor Gray
}

# ── Persiste PIDs ─────────────────────────────────────────────────────────────
[PSCustomObject]@{
    StreamlitPid  = $streamlitProc.Id
    CloudflaredPid = $cfProc.Id
} | ConvertTo-Json | Set-Content -Path $PidFile -Encoding UTF8

# ── Resultado ─────────────────────────────────────────────────────────────────
$urlDisplay   = if ($publicUrl) { $publicUrl } else { "(aguardando — veja '$cfLogFile')" }
$localDisplay = "http://127.0.0.1:$Port"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  Lab04 - ONLINE                                                      ║" -ForegroundColor Yellow
Write-Host "║                                                                      ║" -ForegroundColor Yellow
Write-Host "║  URL pública : $urlDisplay" -ForegroundColor Cyan
Write-Host "║  URL local   : $localDisplay" -ForegroundColor Green
Write-Host "║                                                                      ║" -ForegroundColor Yellow
Write-Host "║  Pressione Ctrl+C para encerrar                                      ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""

if ($publicUrl) {
    Start-Process $publicUrl
}

# ── Mantém terminal aberto monitorando os processos ───────────────────────────
$ErrorActionPreference = "Continue"   # erros no loop não encerram o script
try {
    while ($true) {
        Start-Sleep -Seconds 10

        $slRunning = -not $streamlitProc.HasExited
        $cfRunning = -not $cfProc.HasExited

        # Tenta capturar URL caso ainda não tivesse sido obtida
        if (-not $publicUrl -and (Test-Path $cfLogFile)) {
            $logContent = Get-Content $cfLogFile -Raw -ErrorAction SilentlyContinue
            if ($logContent -match 'https://[a-z0-9\-]+\.trycloudflare\.com') {
                $publicUrl  = $Matches[0]
                $urlDisplay = $publicUrl
                Write-Host ""
                Write-Host "  URL pública disponível: $publicUrl" -ForegroundColor Cyan
                Start-Process $publicUrl
            }
        }

        $timestamp = Get-Date -Format "HH:mm:ss"
        $slStatus  = if ($slRunning) { "OK" } else { "PARADO" }
        $cfStatus  = if ($cfRunning) { "OK" } else { "PARADO" }

        Write-Host "  [$timestamp]  Streamlit: $slStatus  |  cloudflared: $cfStatus  |  $urlDisplay" `
            -ForegroundColor $(if ($slRunning -and $cfRunning) { "DarkGray" } else { "Red" })

        if (-not $slRunning -or -not $cfRunning) {
            Write-Host ""
            Write-Host "  Um dos processos encerrou inesperadamente. Execute .\Stop-Lab04.ps1 para limpar." `
                -ForegroundColor Red
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "  Terminal encerrado. Execute .\Stop-Lab04.ps1 para matar os processos." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "  Pressione Enter para fechar esta janela"
}
