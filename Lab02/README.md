# *Laboratório 02 - Características de repositórios populares*  

## *Objetivo*  

Este projeto tem como objetivo analisar a qualidade interna de repositórios Java open-source no GitHub, correlacionando-a com características do processo de desenvolvimento, como popularidade, maturidade, atividade e tamanho. Serão coletados dados dos 1.000 repositórios Java mais populares, utilizando métricas de qualidade (CBO, DIT, LCOM) obtidas com a ferramenta CK e métricas de processo (estrelas, linhas de código, releases, idade). O estudo busca responder quatro questões de pesquisa, identificando relações entre essas métricas para entender como práticas colaborativas impactam a qualidade do software.  

---

## *Questões de Pesquisa*  

- Qual a relação entre a popularidade dos repositórios e as suas características de
qualidade?   
- Qual a relação entre a maturidade do repositórios e as suas características de
qualidade ?  
- Qual a relação entre a atividade dos repositórios e as suas características de
qualidade?  
- Qual a relação entre o tamanho dos repositórios e as suas características de
qualidade?  

---

## *Configuração de variáveis de ambiente*  

O script de coleta requer um *token de autenticação* do GitHub.

Crie um arquivo `.env` em `Lab02/` usando os nomes abaixo:

```env
GITHUB_TOKEN=seu_token_aqui
GITHUB_API_URL=https://api.github.com/graphql
CK_REPO_PATH=D:\lab-experimetacao-sofware\Lab02\src\ck-0.7.1-SNAPSHOT-jar-with-dependencies.jar
```

> Compatibilidade: o código também aceita `TOKEN`, `API_URL` e `CK_REPO_URL`.
> Se `GITHUB_API_URL` estiver como `https://api.github.com`, o código ajusta automaticamente para `https://api.github.com/graphql`.


Caso precise gerar um token, siga os passos:  
1. Acesse [GitHub Developer Settings](https://github.com/settings/tokens).  
2. Clique em *"Generate new token (classic)"*.  
3. Selecione as permissões:  
   - repo → Acesso a repositórios públicos  
   - read:org → Acesso a informações organizacionais (se necessário)  
4. Copie o token gerado e adicione ao projeto.  

---

## *Sprints do Projeto*  

### *Sprint 1 - Coleta de Dados e Análise Inicial*  

*Objetivos:*  
- Coletar *1000 repositórios Java* populares via *API do GitHub*.  
- Clonar os repositórios coletados automaticamente.  
- Extrair métricas de código usando a ferramenta *CK*.  
- Organizar e armazenar os dados coletados para análise.  

*Dependências:*  
```powershell
  pip install --quiet json5 python-dotenv matplotlib pandas requests GitPython pygount scipy python-docx
```

### *Como Executar*

- Execute a partir da raiz do repositório (evita problemas de path):
```powershell
Set-Location "D:\lab-experimetacao-sofware"
python .\Lab02\install_dependencies.py
python .\Lab02\src\main.py --start 0 --end 1000 --resume
```

- Para retomar de onde parou (caso tenha interrompido), basta usar `--resume`:
```powershell
python .\Lab02\src\main.py --start 0 --end 1000 --resume
```

- Para suprimir saída detalhada:
```powershell
python .\Lab02\src\main.py --start 0 --end 1000 --resume --quiet
```

- Para gerar apenas o relatório final a partir de dados já coletados:
```powershell
python .\Lab02\gerar_relatorio_final.py
```

### *Funcionalidades de desempenho*

- **Checkpoint incremental**: resultados parciais são salvos em `workdir/results_checkpoint.csv` após cada lote; use `--resume` para retomar.
- **Paralelismo CK**: por padrão, utiliza `cpu_count - 1` workers simultâneos (configurável com `--max-workers-ck` ou variável `CK_MAX_WORKERS`).
- **Batch size 100**: busca até 100 repositórios por chamada GraphQL (máximo permitido pela API).
- **JVM otimizada**: CK roda com `-Xmx4g -XX:+UseG1GC -XX:+ParallelRefProcEnabled` (configurável via variável `CK_JVM_FLAGS`).
- **Clone raso**: apenas `depth=1`, branch principal, sem tags.

### *Variáveis de ambiente opcionais*

| Variável              | Padrão       | Descrição                                |
|-----------------------|--------------|------------------------------------------|
| `CK_MAX_WORKERS`      | cpu-1        | Workers paralelos para executar o CK     |
| `CK_TIMEOUT_SECONDS`  | 600          | Timeout por repositório (segundos)       |
| `CK_JVM_FLAGS`        | -Xmx4g ...   | Flags da JVM ao executar o JAR do CK     |
| `GITHUB_BATCH_SIZE`   | 100          | Repositórios por página GraphQL          |

### *Estrutura de pastas geradas* 

- `Lab02/workdir/clones/`: clones temporários dos repositórios analisados.
- `Lab02/workdir/ck_output/`: CSVs temporários gerados pelo CK por repositório.
- `Lab02/workdir/results_checkpoint.csv`: checkpoint incremental com dados já processados.
- `Lab02/workdir/cursor_checkpoint.json`: cursor de paginação do GraphQL para retomada.
- `Lab02/reports/report.html`: relatório HTML com tabela, estatísticas e gráficos.
- `Lab02/reports/dados_brutos.csv`: CSV bruto com todas as medições dos repositórios.
- `Lab02/reports/relatorio_final.docx` e `Lab02/reports/relatorio_final.pdf`: versão final consolidada do relatório.
- `Lab02/reports/rq01_popularidade_vs_ck.png` ... `rq04_tamanho_vs_ck.png`: gráficos de correlação.

- Caso queira consultar os resultados da nossa pipeline, acesse: [Pipeline](https://github.com/DrumondGit/labExperimetacaoSofware/actions/runs/14023141025)
---