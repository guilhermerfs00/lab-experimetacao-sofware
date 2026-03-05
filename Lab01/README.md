# Relatório Final – Características de Repositórios Populares

## INTRODUÇÃO E HIPÓTESES INICIAIS

Neste estudo, analisamos os 1.000 repositórios com maior número de estrelas na plataforma, observando métricas como: idade do repositório, volume de contribuições externas, frequência de releases, linguagem e taxa de fechamento de issues.

O objetivo é verificar se repositórios mais populares tendem a ser mais antigos, atrair mais contribuições de terceiros, manter um ritmo maior de lançamentos e atualizar-se com mais regularidade, além de identificar se há concentração em linguagens amplamente adotadas. Também investigamos se a popularidade de uma linguagem se relaciona com maior contribuição externa, mais releases e maior frequência de atualizações.
Com base na intuição sobre projetos open-source populares, formulamos as seguintes hipóteses:

- **H1:** Repositórios populares tendem a ser mais antigos, com uma idade mediana superior a 5 anos.
- **H2:** Projetos populares recebem uma quantidade significativa de contribuições externas, com pelo menos 1.000 pull requests aceitas em mediana.
- **H3:** Repositórios populares lançam releases com alta frequência, tendo um total mediano de mais de 10 releases ao longo de sua existência.
- **H4:** Projetos amplamente utilizados são frequentemente atualizados, com um tempo mediano desde a última atualização inferior a 30 dias.
- **H5:** Repositórios populares tendem a ser escritos nas linguagens de programação mais utilizadas, como JavaScript, Python e TypeScript, representando pelo menos 50% do total.
- **H6:** Projetos populares possuem um alto percentual de issues fechadas, com pelo menos 70% das issues resolvidas.
- **H7 (bônus):** Repositórios escritos em linguagens populares recebem 20% mais pull requests, lançam 15% mais releases e são atualizados com maior frequência do que aqueles escritos em linguagens menos comuns.

Essas hipóteses serão avaliadas por meio da coleta e análise dos dados extraídos da API GraphQL do GitHub, permitindo a identificação de padrões e tendências entre os projetos mais populares da plataforma.

---

## METODOLOGIA

### Coleta de Dados
Utilizamos a API GraphQL do GitHub para obter informações sobre os 1.000 repositórios com mais estrelas. A consulta busca repositórios com mais de 10.000 estrelas, ordenados por quantidade de estrelas, e utiliza **paginação via cursor** para percorrer todos os resultados em lotes.

Para cada repositório, são coletados os seguintes campos:
- Nome e proprietário
- Data de criação e última atualização
- Quantidade de estrelas
- Linguagem primária
- Total de pull requests aceitas (merged)
- Total de releases
- Total de issues e issues fechadas

### Armazenamento
Os dados extraídos são processados e salvos em um arquivo `.csv` (`graphs/repositorios.csv`) para facilitar a análise e reprodução dos resultados.

## ESTRUTURA DO PROJETO

```
Lab01/
├── README.md                        # Este relatório
├── requirements.txt                 # Dependências do projeto
├── install_dependencies.py          # Script de instalação de dependências
├── graphs/                          # Gráficos e dados gerados
│   ├── repositorios.csv             # Dados coletados (1000 repositórios)
│   ├── rq01_idade.png
│   ├── rq02_pull_requests.png
│   ├── rq03_releases.png
│   ├── rq04_atualizacao.png
│   ├── rq05_linguagens.png
│   └── rq06_issues_fechadas.png
└── src/                             # Código-fonte
    ├── main.py                      # Ponto de entrada
    ├── client/
    │   └── github_client.py         # Consulta GraphQL com paginação
    └── service/
        ├── data_service.py          # Processamento dos dados
        ├── csv_resultados.py        # Exportação para CSV
        └── gerador_graficos.py      # Geração dos gráficos
```

## COMO EXECUTAR

1. Crie um arquivo `.env` na raiz do projeto com seu token do GitHub:
   ```
   GITHUB_TOKEN=ghp_seuTokenAqui
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute o script principal:
   ```bash
   cd src
   python main.py
   ```

Os resultados serão salvos no diretório `graphs/`.
