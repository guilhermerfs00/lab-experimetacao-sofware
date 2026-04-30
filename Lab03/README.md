# Lab03 – Caracterizando a Atividade de Code Review no GitHub

## Introdução

A prática de **code review** é essencial nos processos ágeis de desenvolvimento de software. No GitHub, ela acontece através de **Pull Requests (PRs)**: um colaborador submete código, revisores inspecionam, comentam e ao final aprovam (MERGED) ou rejeitam (CLOSED) a contribuição.

Este laboratório analisa a atividade de code review em repositórios populares do GitHub, identificando variáveis que influenciam no **merge de um PR** e no **número de revisões recebidas**.

---

## Hipóteses Iniciais (Lab03S02)

| RQ | Pergunta | Hipótese |
|----|----------|----------|
| RQ01 | Tamanho × Status do PR | PRs maiores (mais arquivos/linhas) têm menor chance de merge — são mais difíceis de revisar. |
| RQ02 | Tempo de Análise × Status do PR | PRs com discussão muito longa tendem a ser fechados sem merge. |
| RQ03 | Descrição × Status do PR | PRs com descrições mais detalhadas têm maior chance de merge, pois facilitam a revisão. |
| RQ04 | Interações × Status do PR | Mais comentários/participantes podem indicar controvérsia, levando a mais rejeições. |
| RQ05 | Tamanho × Nº de Revisões | PRs maiores exigem mais rodadas de revisão. |
| RQ06 | Tempo de Análise × Nº de Revisões | PRs com mais revisões ficam abertos por mais tempo. |
| RQ07 | Descrição × Nº de Revisões | Descrições curtas geram mais dúvidas, levando a mais revisões. |
| RQ08 | Interações × Nº de Revisões | Mais participantes e comentários correlacionam com mais revisões formais. |

---

## Metodologia

### 1. Criação do Dataset

- **Repositórios**: os 200 mais populares do GitHub (>10 000 estrelas), com ≥ 100 PRs (MERGED + CLOSED).
- **Filtros de PR**:
  - Estado: MERGED ou CLOSED
  - Pelo menos **1 revisão** (`reviews.totalCount >= 1`)
  - Tempo de análise **> 1 hora** (exclui automações/bots)

### 2. Métricas Coletadas por PR

| Dimensão | Métrica | Campo no Dataset |
|----------|---------|-----------------|
| Tamanho | Nº de arquivos alterados | `changed_files` |
| Tamanho | Linhas adicionadas + removidas | `total_lines_changed` |
| Tempo | Horas entre criação e merge/close | `analysis_time_hours` |
| Descrição | Nº de caracteres do corpo do PR | `description_length` |
| Interações | Nº de participantes | `participants` |
| Interações | Nº de comentários | `comments` |
| Revisões | Total de revisões recebidas | `review_count` |
| Status | MERGED (1) / CLOSED (0) | `state` |

### 3. Teste Estatístico

Utilizamos o **Teste de Correlação de Spearman (ρ)** pois:
- É **não-paramétrico**: não pressupõe distribuição normal (PRs seguem distribuições assimétricas com cauda longa).
- É **robusto a outliers**: métricas como linhas alteradas possuem valores extremos.
- É adequado para variáveis ordinais e contínuas assimétricas.

Nível de significância: **α = 0,05** (p-valor < 0,05).

---

## Estrutura dos Arquivos

```
Lab03/
├── requirements.txt
├── README.md
├── src/
│   ├── main.py                  # Orquestrador principal (coleta + análise)
│   ├── repositories_adapter.py  # Busca os 200 repositórios mais populares
│   ├── pr_adapter.py            # Coleta e filtra PRs com todas as métricas
│   ├── analysis.py              # Correlações de Spearman + gráficos combinados
│   ├── generate_graphs.py       # Gera gráficos individuais por RQ
│   └── generate_report.py       # Gera o relatório final em PDF
├── graphs/                      # Gráficos individuais gerados
└── docs/                        # Relatório PDF e CSVs de resultados
```

---

## Como Executar

### 1. Pré-requisitos

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Instalar fpdf2 (necessário para gerar o relatório PDF)
pip install fpdf2
```

Crie um arquivo `.env` na pasta `src/` com seu token do GitHub:

```
GITHUB_TOKEN=ghp_seu_token_aqui
```

---

### 2. Coleta de Dados (`main.py`)

Todos os comandos devem ser executados dentro da pasta `src/`:

```bash
cd src
```

| Comando | Descrição |
|---------|-----------|
| `python main.py` | Execução completa: coleta repositórios + PRs + análise |
| `python main.py --collect` | Apenas coleta os repositórios e PRs (salva `prs_dataset.csv`) |
| `python main.py --analyse` | Apenas analisa o dataset existente (gera CSVs e gráficos combinados) |
| `python main.py --collect --analyse` | Coleta e analisa em sequência (equivalente ao padrão) |

**Exemplos:**

```bash
# Coleta completa (200 repositórios + PRs)
python main.py --collect

# Analisa dataset já coletado (gera correlações de Spearman e gráficos)
python main.py --analyse

# Pipeline completo: coleta + análise
python main.py
```

> **Retomada automática:** se `prs_dataset.csv` já existir, a coleta retoma de onde parou (repositórios já coletados são ignorados).

---

### 3. Geração de Gráficos Individuais (`generate_graphs.py`)

Gera **15 gráficos separados** (um por RQ/métrica) salvos em `Lab03/graphs/`:

```bash
python generate_graphs.py
```

**Gráficos gerados:**

| Arquivo | Tipo | Conteúdo |
|---------|------|----------|
| `status_distribution.png` | Pizza | Distribuição MERGED vs CLOSED |
| `medians_comparison.png` | Barras | Medianas das métricas por status |
| `spearman_summary.png` | Barras | Todos os coeficientes ρ de Spearman por RQ |
| `RQ01_boxplot.png` | Boxplot | Arquivos alterados × Status do PR |
| `RQ01b_boxplot.png` | Boxplot | Linhas alteradas × Status do PR |
| `RQ02_boxplot.png` | Boxplot | Tempo de análise × Status do PR |
| `RQ03_boxplot.png` | Boxplot | Tamanho da descrição × Status do PR |
| `RQ04_boxplot.png` | Boxplot | Participantes × Status do PR |
| `RQ04b_boxplot.png` | Boxplot | Comentários × Status do PR |
| `RQ05_scatter.png` | Scatter | Arquivos alterados × Nº de revisões |
| `RQ05b_scatter.png` | Scatter | Linhas alteradas × Nº de revisões |
| `RQ06_scatter.png` | Scatter | Tempo de análise × Nº de revisões |
| `RQ07_scatter.png` | Scatter | Tamanho da descrição × Nº de revisões |
| `RQ08_scatter.png` | Scatter | Participantes × Nº de revisões |
| `RQ08b_scatter.png` | Scatter | Comentários × Nº de revisões |

---

### 4. Geração do Relatório PDF (`generate_report.py`)

Gera o relatório final completo em `Lab03/docs/Relatorio-LAB03.pdf`:

```bash
python generate_report.py
```

**Conteúdo do relatório:**
- Capa com resumo do dataset
- Introdução com hipóteses iniciais e questões de pesquisa
- Metodologia (coleta, métricas, justificativa do Spearman)
- Resultados com tabelas de medianas e coeficientes ρ
- Análise individual por RQ (RQ01–RQ08) com gráficos embutidos
- Discussão confrontando hipóteses com resultados
- Conclusão e confronto com literatura científica

---

### 5. Geração do Relatório Word/DOCX (`generate_docx.py`)

Gera o mesmo relatório em formato `.docx` (editável no Word/LibreOffice) em `Lab03/docs/Relatorio-LAB03.docx`:

```bash
# Instalar dependência (apenas uma vez)
pip install python-docx

# Gerar o .docx
python generate_docx.py
```

**O arquivo `.docx` contém:**
- Capa estilizada com título, instituição e professor
- Box de resumo do dataset
- Todas as seções do relatório (Introdução, Metodologia, Resultados, Análise por RQ, Discussão e Conclusão)
- Tabelas formatadas com cores (medianas e coeficientes de Spearman)
- Todos os 15 gráficos embutidos (boxplots e scatter plots por RQ)
- Texto em cores indicando valores positivos/negativos e significância estatística

---

### 6. Pipeline Completo (ordem recomendada)

```bash
cd src

# 1. Instalar dependências
pip install -r ../requirements.txt
pip install fpdf2 python-docx

# 2. Coletar dados do GitHub
python main.py --collect

# 3. Executar análise estatística (correlações de Spearman)
python main.py --analyse

# 4. Gerar gráficos individuais por RQ
python generate_graphs.py

# 5. Gerar relatório final em PDF
python generate_report.py

# 6. Gerar relatório final em Word (.docx)
python generate_docx.py
```

---

### 7. Saídas Geradas

| Arquivo | Localização | Descrição |
|---------|-------------|-----------|
| `repos_selected.csv` | `src/` | Lista dos repositórios selecionados |
| `prs_dataset.csv` | `src/` | Dataset completo com todas as métricas por PR |
| `rq_results.csv` | `docs/` | Resultados das correlações de Spearman (RQ01–RQ08) |
| `medians.csv` | `docs/` | Medianas das métricas separadas por MERGED/CLOSED |
| `Relatorio-LAB03.pdf` | `docs/` | Relatório final em PDF |
| `Relatorio-LAB03.docx` | `docs/` | Relatório final editável em Word/LibreOffice |
| `status_distribution.png` | `graphs/` | Distribuição dos PRs por status |
| `medians_comparison.png` | `graphs/` | Comparação de medianas MERGED vs CLOSED |
| `spearman_summary.png` | `graphs/` | Resumo de todos os coeficientes de Spearman |
| `RQ01_boxplot.png` … `RQ08b_scatter.png` | `graphs/` | Gráficos individuais por RQ (15 arquivos) |

---

## Questões de Pesquisa

### Dimensão A – Feedback Final (Status do PR: MERGED vs CLOSED)

- **RQ01** – Relação entre **tamanho** dos PRs e o feedback final
- **RQ02** – Relação entre **tempo de análise** e o feedback final
- **RQ03** – Relação entre **descrição** dos PRs e o feedback final
- **RQ04** – Relação entre **interações** nos PRs e o feedback final

### Dimensão B – Número de Revisões

- **RQ05** – Relação entre **tamanho** dos PRs e o número de revisões
- **RQ06** – Relação entre **tempo de análise** e o número de revisões
- **RQ07** – Relação entre **descrição** dos PRs e o número de revisões
- **RQ08** – Relação entre **interações** nos PRs e o número de revisões

---

## Processo de Desenvolvimento

- **Lab03S01**: Seleção dos repositórios + Script de coleta de PRs e métricas ✅
- **Lab03S02**: Dataset completo + Primeira versão do relatório com hipóteses ✅
- **Lab03S03**: Análise e visualização de dados + Relatório final em PDF ✅
