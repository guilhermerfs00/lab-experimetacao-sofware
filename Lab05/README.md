# Lab05 — GraphQL vs REST: Experimento Controlado

Experimento controlado que compara a **GitHub REST API** e a **GitHub GraphQL API v4** nas métricas de tempo de resposta (ms) e tamanho da resposta (bytes), em quatro cenários de consulta.

---

## Questões de Pesquisa

| # | Questão | Hipótese alternativa (H₁) |
|---|---------|--------------------------|
| **RQ1** | Consultas GraphQL respondem mais rápido que REST? | Tempo GraphQL < Tempo REST |
| **RQ2** | Respostas GraphQL são menores que REST? | Tamanho GraphQL < Tamanho REST |

---

## Estrutura do Projeto

```
Lab05/
├── .env                    ← token GitHub (não versionar)
├── .streamlit/
│   └── config.toml         ← tema do dashboard
├── docs/
│   └── results.csv         ← dataset gerado pela coleta
├── src/
│   ├── main.py             ← orquestra o experimento
│   ├── rest_adapter.py     ← chamadas à REST API
│   └── graphql_adapter.py  ← chamadas à GraphQL API
├── dashboard.py            ← dashboard Streamlit
├── requirements.txt
├── Start-Lab05.ps1
└── Stop-Lab05.ps1
```

---

## Pré-requisitos

- Python 3.10 ou superior
- Token pessoal do GitHub com escopo `public_repo` (somente leitura)
  - Gere em: **github.com → Settings → Developer settings → Personal access tokens → Tokens (classic)**

---

## Passo a Passo

### 1. Clonar o repositório

```bash
git clone https://github.com/guilhermerfs00/lab-experimetacao-sofware.git
cd lab-experimetacao-sofware/Lab05
```

### 2. Configurar o token do GitHub

Edite o arquivo `.env` na raiz do Lab05:

```env
GITHUB_TOKEN=ghp_SEU_TOKEN_AQUI
```

> ⚠️ Nunca versione o `.env`. Ele já está no `.gitignore`.

### 3. Criar o ambiente virtual e instalar dependências

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Executar a coleta de dados

```powershell
python src/main.py
```

O script executa **30 trials por combinação (cenário × API)** = 240 medições totais, com pausa de 1,5 s entre chamadas para respeitar o rate-limit do GitHub.

Ao final, o arquivo `docs/results.csv` será gerado com as colunas:

| Coluna | Descrição |
|--------|-----------|
| `scenario` | Identificador do cenário (`repo_info`, `search_repos`, `user_profile`, `repo_issues`) |
| `api_type` | `REST` ou `GraphQL` |
| `trial_index` | Índice do trial (0–29) |
| `response_time_ms` | Tempo de resposta em milissegundos |
| `response_size_bytes` | Tamanho da resposta em bytes |
| `http_status` | Código HTTP da resposta |
| `owner` / `repo` | Repositório usado no trial (quando aplicável) |
| `language` | Linguagem usada na busca (quando aplicável) |
| `login` | Usuário consultado (quando aplicável) |

Opções do script:

```powershell
python src/main.py --trials 50        # número customizado de trials
python src/main.py --no-checkpoint    # ignora checkpoint e recomeça do zero
```

### 5. Iniciar o dashboard

#### Opção A — Script PowerShell (recomendado)

```powershell
.\Start-Lab05.ps1
```

#### Opção B — Manual

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run dashboard.py
```

O dashboard abrirá em **http://localhost:8501**.

### 6. Encerrar o dashboard

```powershell
.\Stop-Lab05.ps1
```

---

## Cenários do Experimento

| Cenário | Descrição | Objeto experimental |
|---------|-----------|---------------------|
| `repo_info` | Metadados de repositório | 10 repositórios populares |
| `search_repos` | Busca de repositórios por linguagem | 5 linguagens (Python, JS, TS, Go, Rust) |
| `user_profile` | Perfil de usuário | 10 usuários populares |
| `repo_issues` | Issues abertas de repositório | 10 repositórios populares |

---

## Seções do Dashboard

| Seção | Conteúdo |
|-------|----------|
| **Visão Geral** | KPIs: total de medições, Δ mediana GraphQL − REST |
| **RQ1 – Tempo de Resposta** | Barras agrupadas por cenário + tabela estatística |
| **RQ2 – Tamanho da Resposta** | Barras agrupadas por cenário + tabela estatística |
| **Análise Estatística** | Teste Mann-Whitney U, p-valor, Cliff's δ, interpretação automática |
| **Dispersão** | Scatter Tempo × Tamanho por medição individual |
| **Evolução por Trial** | Linha temporal de cada métrica por cenário |
| **Dados Brutos** | Tabela completa filtrada |

---

## Metodologia Estatística

- **Teste**: Mann-Whitney U (não paramétrico, bicaudal)
- **Nível de significância**: α = 0,05
- **Tamanho de efeito**: Cliff's δ
  - |δ| < 0,15 → negligenciável
  - 0,15 ≤ |δ| < 0,33 → pequeno
  - 0,33 ≤ |δ| < 0,47 → médio
  - |δ| ≥ 0,47 → grande
- **Remoção de outliers** (opcional no dashboard): método IQR × 1,5

---

## Dependências

| Pacote | Versão |
|--------|--------|
| `python-dotenv` | 1.0.1 |
| `requests` | 2.32.3 |
| `pandas` | 2.2.2 |
| `scipy` | ≥ 1.13.0 |
| `streamlit` | ≥ 1.35.0 |
| `plotly` | ≥ 5.22.0 |
