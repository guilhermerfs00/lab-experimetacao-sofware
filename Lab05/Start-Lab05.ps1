# Start-Lab05.ps1 — Inicia o dashboard do Lab05
Set-Location $PSScriptRoot

# Cria venv se não existir
if (-not (Test-Path ".venv")) {
    Write-Host "Criando ambiente virtual…"
    python -m venv .venv
}

# Ativa o venv
. .\.venv\Scripts\Activate.ps1

# Instala dependências
pip install -r requirements.txt -q

# Inicia o Streamlit
Write-Host "Iniciando dashboard em http://localhost:8501"
streamlit run dashboard.py --server.port 8501
