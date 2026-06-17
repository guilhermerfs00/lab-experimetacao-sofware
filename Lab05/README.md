# Lab05 – GraphQL vs REST: Um Experimento Controlado

Experimento controlado que compara a **API REST** e a **API GraphQL** do GitHub
nas métricas de tempo de resposta (RQ1) e tamanho de payload (RQ2).

---

## Perguntas de Pesquisa

| # | Pergunta |
|---|----------|
| **RQ1** | Respostas às consultas GraphQL são mais **rápidas** que respostas REST? |
| **RQ2** | Respostas às consultas GraphQL têm **tamanho menor** que respostas REST? |

---

## Estrutura do Projeto

```
Lab05/
├── src/
│   ├── main.py              # Orquestrador do experimento
│   ├── rest_adapter.py      # Chamadas à GitHub REST API
│   └── graphql_adapter.py   # Consultas à GitHub GraphQL API
├── docs/
│   └── results.csv          # Dataset gerado pelo experimento
├── dashboard.py             # Dashboard Streamlit (Sprint 3)
├── requirements.txt
├── .env.example
├── Start-Lab05.ps1          # Inicia dashboard + Cloudflare Tunnel
└── Stop-Lab05.ps1           # Encerra os processos
```

---

## Configuração

### 1. Clonar / abrir o projeto e criar o virtualenv

```powershell
cd Lab05
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. Criar o arquivo `.env`

```powershell
Copy-Item .env.example .env
# Edite .env e insira seu GITHUB_TOKEN
```

O token precisa de escopo `public_repo` (read-only).

---

## Execução do Experimento (Sprint 2)

```powershell
cd Lab05
.venv\Scripts\python src/main.py
```

Opções disponíveis:

| Flag | Descrição | Padrão |
|------|-----------|--------|
| `--trials N` | Número de trials por (cenário × API) | 30 |
| `--no-checkpoint` | Reexecuta do zero | — |

O script salva as medições em `docs/results.csv` com checkpoint automático a cada 10 medições.

---

## Dashboard (Sprint 3)

```powershell
cd Lab05
.venv\Scripts\python -m streamlit run dashboard.py
```

Ou com exposição pública via Cloudflare Tunnel:

```powershell
.\Start-Lab05.ps1   # inicia
.\Stop-Lab05.ps1    # encerra
```

---

## Desenho do Experimento

### Hipóteses

**RQ1 – Tempo de Resposta**  
- H₀: tempo(GraphQL) = tempo(REST)  
- H₁: tempo(GraphQL) < tempo(REST)  

**RQ2 – Tamanho da Resposta**  
- H₀: tamanho(GraphQL) = tamanho(REST)  
- H₁: tamanho(GraphQL) < tamanho(REST)  

### Variáveis

| Tipo | Variável | Unidade |
|------|----------|---------|
| Dependente | Tempo de resposta | ms |
| Dependente | Tamanho da resposta | bytes |
| Independente | Tipo de API | REST / GraphQL |

### Cenários (Objetos Experimentais)

| Cenário | REST endpoint | GraphQL equivalente |
|---------|---------------|---------------------|
| `repo_info` | `GET /repos/{owner}/{repo}` | `query { repository(...) { ... } }` |
| `search_repos` | `GET /search/repositories` | `query { search(...) { ... } }` |
| `user_profile` | `GET /users/{login}` | `query { user(...) { ... } }` |
| `repo_issues` | `GET /repos/{owner}/{repo}/issues` | `query { repository { issues { ... } } }` |

### Quantidade de Medições

- **30 trials** por (cenário × API)  
- **4 × 2 × 30 = 240 medições** no total  
- Ordem dos trials aleatorizada (seed fixo para reprodutibilidade)  
- Warm-up de 3 chamadas descartadas antes do início  

### Teste Estatístico

**Mann-Whitney U** (não paramétrico, α = 0,05) com Cliff's delta como medida de efeito.

### Ameaças à Validade

| Tipo | Ameaça | Mitigação |
|------|--------|-----------|
| Interna | Variação de latência de rede | Múltiplos trials; pausa de 1,5 s entre chamadas |
| Interna | Cache do servidor | Headers `Cache-Control: no-cache` |
| Interna | Rate limiting | Token autenticado; pausa entre chamadas |
| Construto | Equivalência REST ↔ GraphQL | Queries GraphQL projetadas para retornar os mesmos campos dos endpoints REST |
| Externa | Generalização | Experimento restrito à GitHub API |
