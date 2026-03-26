# Laboratorio 02 - Qualidade de Repositorios Java Populares

## Objetivo
Analisar qualidade interna de repositorios Java populares no GitHub e correlacionar com sinais de processo (estrelas, idade, releases e atividade).

Pipeline atual do `Lab02`:
1. Coleta repositorios via GraphQL do GitHub.
2. Clona localmente cada repositorio.
3. Executa CK para extrair metricas de qualidade.
4. Agrega resultados em `pandas`.
5. Gera relatorio HTML com tabela e graficos.

## Estrutura principal
- `src/main.py`: ponto de entrada do pipeline.
- `src/config/settings.py`: leitura de `.env` e resolucao de caminhos.
- `src/adapters/github_graphql_adapter.py`: integracao com API GraphQL.
- `src/adapters/git_repository_adapter.py`: clone/remocao/contagem de linhas Java.
- `src/adapters/quality_metrics_adapter.py`: execucao e sumarizacao do CK.
- `src/services/repository_analysis_service.py`: orquestracao por repositorio.
- `src/services/report_service.py`: geracao de graficos e HTML.
- `src/repositories_adapter.py` e `src/quality_metrics_adapter.py`: wrappers legados para compatibilidade.

## Pre-requisitos
- Python 3.11+
- Java instalado e disponivel no `PATH` (necessario para `java -jar` do CK)
- Token do GitHub com acesso de leitura em repositorios publicos

## Configuracao de ambiente
Crie um arquivo `.env` em `Lab02/` (ou no root do repo) com pelo menos:

```env
TOKEN=ghp_seu_token_aqui
API_URL=https://api.github.com/graphql
CK_REPO_URL=Lab02/src/ck-0.7.1-SNAPSHOT.jar
```

Tambem sao aceitos aliases antigos:
- `GITHUB_TOKEN` no lugar de `TOKEN`
- `GITHUB_API_URL` no lugar de `API_URL`
- `CK_REPO_PATH` no lugar de `CK_REPO_URL`

## Instalacao
No PowerShell, execute a partir de `Lab02`:

```powershell
Set-Location "D:\lab-experimetacao-sofware\Lab02"
python .\install_dependencies.py
```

## Execucao
Recomendado executar a partir do root do repositorio para manter caminhos previsiveis:

```powershell
Set-Location "D:\lab-experimetacao-sofware"
python .\Lab02\src\main.py --start 0 --end 1000 --quiet
```

### Modo Demo (para validacao sem CK com dependencias)
Se o JAR do CK com dependências não estiver disponível, use:

```powershell
python .\Lab02\src\main.py --start 0 --end 10 --demo
```

Neste modo, o sistema gera metricas fake em vez de executar o CK real, permitindo validacao do fluxo completo de coleta, processamento e relatório.

### Argumentos CLI
- `--start`: indice inicial da faixa de repositorios.
- `--end`: indice final da faixa de repositorios.
- `--quiet`: reduz logs no terminal.
- `--demo`: modo demo com metricas fake (util para validacao quando CK real nao esta disponivel).

## Saidas geradas
- Relatorio final: `Lab02/reports/report.html`
- Diretorios temporarios de clone/CK: `Lab02/src/repo/` (removidos ao fim do processamento)

## Observacoes
- Nao existe suite automatizada de testes no projeto no momento.
- Validacao pratica: conferir se o `report.html` foi gerado com tabela populada e graficos embutidos.

### Configuracao do CK
- O CK requer a versao com dependencias embutidas (`*-jar-with-dependencies.jar`)
- Se nao estiver disponivel, use `--demo` para validar o fluxo com metricas fake.
- Para baixar o CK correto, acesse: https://github.com/mauricioaniche/ck/releases

