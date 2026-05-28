# Stop-Lab05.ps1 — Para o dashboard do Lab05
$procs = Get-Process -Name "streamlit" -ErrorAction SilentlyContinue
if ($procs) {
    $procs | Stop-Process -Force
    Write-Host "Dashboard Lab05 encerrado."
} else {
    Write-Host "Nenhum processo streamlit encontrado."
}
