# AGENTS Guide

## Scope and repo map
- This repository contains lab deliverables; active code is in `Lab01/` and `Lab02/`.
- `Lab03/`, `Lab04/`, and `Lab05/` currently only contain placeholder `README.md` files.
- Treat each lab as an independent runnable project with its own dependencies and outputs.

## Big-picture architecture
- **Lab01 flow** (`Lab01/src/main.py`): GraphQL fetch -> dataframe transformation -> CSV export -> PNG chart generation.
- **Lab01 boundaries**:
  - API client: `Lab01/src/client/github_client.py`
  - Data shaping + orchestration: `Lab01/src/service/data_service.py`
  - Output writers: `Lab01/src/service/csv_resultados.py`, `Lab01/src/service/gerador_graficos.py`
- **Lab02 flow** (`Lab02/src/main.py`): GraphQL fetch (Java repos) -> clone repos locally -> run CK metric extraction -> aggregate in pandas -> HTML report with embedded graphs.
- **Lab02 boundaries**:
  - Repo/process orchestration: `Lab02/src/repositories_adapter.py`
  - CK execution + CSV summarization: `Lab02/src/quality_metrics_adapter.py`

## Critical workflows (current behavior)
```powershell
# Lab01 setup + run (from repo root)
Set-Location "D:\lab-experimetacao-sofware\Lab01"
python install_dependencies.py
python .\src\main.py
python .\gerar_relatorio.py
```
```powershell
# Lab02 setup + run (from repo root due path construction in repositories_adapter.py)
Set-Location "D:\lab-experimetacao-sofware"
python .\Lab02\install_dependencies.py
python .\Lab02\src\main.py --start 0 --end 1000 --quiet
```
- No automated test suite is present (`**/*test*` not found); validation is done by checking generated artifacts.

## Project-specific conventions and gotchas
- Portuguese naming is the norm for symbols, columns, and log messages (for example `processar_dados`, `Razão Issues Fechadas`).
- Output locations are fixed and should be preserved:
  - `Lab01/graphs/repositorios.csv` and `Lab01/graphs/rq0*.png`
  - `Lab02/reports/report.html`
- `Lab01/src/client/github_client.py` uses `tamanho_lote = 3` and `total_repositorios = 1000`, so the loop currently runs `1000 // 3` batches.
- `Lab02/src/repositories_adapter.py` expects env vars `TOKEN`, `API_URL`, and `CK_REPO_URL`; `Lab02/.env.exemple` uses `GITHUB_TOKEN`/`GITHUB_API_URL`/`CK_REPO_PATH` names.
- `Lab02/src/repositories_adapter.py` builds clone paths from `os.getcwd()` plus `\\Lab02\\src\\repo`; running from `Lab02/src` creates wrong nested paths.

## Integrations and external dependencies
- GitHub GraphQL API is called directly with `requests.post(...)` in both labs.
- Local git clone operations use `GitPython` (`Repo.clone_from(...)`) in Lab02.
- CK metrics are executed via Java JAR in `Lab02/src/quality_metrics_adapter.py` (`java -jar ...`).
- Python analytics stack: `pandas`, `matplotlib`, `pygount`, `python-dotenv`.

## Editing guidance for agents
- Keep generated CSV column names stable; chart/report code depends on exact labels.
- When changing fetch logic, preserve pagination cursor handling and educational-repo filtering in Lab02.
- Prefer small, lab-scoped edits; cross-lab shared modules do not exist yet.
- If adjusting runtime paths or env vars, update both code and corresponding README/example env files together.
