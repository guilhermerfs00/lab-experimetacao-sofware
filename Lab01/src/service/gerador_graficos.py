import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


class GeradorGraficos:
    def __init__(self, diretorio_saida):
        self.diretorio_saida = diretorio_saida
        os.makedirs(self.diretorio_saida, exist_ok=True)

    def gerar(self, df):
        plt.rcParams.update({"figure.autolayout": True, "font.size": 11})

        self._rq01_idade(df)
        self._rq02_pull_requests(df)
        self._rq03_releases(df)
        self._rq04_atualizacao(df)
        self._rq05_linguagens(df)
        self._rq06_issues_fechadas(df)

    def _rq01_idade(self, df):
        figura, eixo = plt.subplots(figsize=(10, 5))
        eixo.hist(df["Idade (anos)"], bins=20, color="steelblue", edgecolor="white")
        eixo.set_title("RQ01 – Distribuição da Idade dos Repositórios Populares")
        eixo.set_xlabel("Idade (anos)")
        eixo.set_ylabel("Número de Repositórios")
        mediana_idade = df["Idade (anos)"].median()
        eixo.axvline(mediana_idade, color="red", linestyle="--", label=f"Mediana: {mediana_idade:.1f} anos")
        eixo.legend()
        figura.savefig(os.path.join(self.diretorio_saida, "rq01_idade.png"), dpi=150)
        plt.close(figura)
        print("Gráfico RQ01 salvo.")

    def _rq02_pull_requests(self, df):
        figura, eixo = plt.subplots(figsize=(10, 5))
        eixo.hist(df["Pull Requests Aceitos"], bins=30, color="darkorange", edgecolor="white")
        eixo.set_title("RQ02 – Distribuição de Pull Requests Aceitas")
        eixo.set_xlabel("Total de PRs Aceitas")
        eixo.set_ylabel("Número de Repositórios")
        eixo.set_yscale("log")
        mediana_prs = df["Pull Requests Aceitos"].median()
        eixo.axvline(mediana_prs, color="red", linestyle="--", label=f"Mediana: {int(mediana_prs)}")
        eixo.legend()
        figura.savefig(os.path.join(self.diretorio_saida, "rq02_pull_requests.png"), dpi=150)
        plt.close(figura)
        print("Gráfico RQ02 salvo.")

    def _rq03_releases(self, df):
        figura, eixo = plt.subplots(figsize=(10, 5))
        eixo.hist(df["Releases"], bins=30, color="seagreen", edgecolor="white")
        eixo.set_title("RQ03 – Distribuição do Total de Releases")
        eixo.set_xlabel("Total de Releases")
        eixo.set_ylabel("Número de Repositórios")
        eixo.set_yscale("log")
        mediana_releases = df["Releases"].median()
        eixo.axvline(mediana_releases, color="red", linestyle="--", label=f"Mediana: {int(mediana_releases)}")
        eixo.legend()
        figura.savefig(os.path.join(self.diretorio_saida, "rq03_releases.png"), dpi=150)
        plt.close(figura)
        print("Gráfico RQ03 salvo.")

    def _rq04_atualizacao(self, df):
        figura, eixo = plt.subplots(figsize=(10, 5))
        eixo.hist(df["Dias Desde Atualização"], bins=30, color="mediumpurple", edgecolor="white")
        eixo.set_title("RQ04 – Dias Desde a Última Atualização")
        eixo.set_xlabel("Dias")
        eixo.set_ylabel("Número de Repositórios")
        mediana_dias = df["Dias Desde Atualização"].median()
        eixo.axvline(mediana_dias, color="red", linestyle="--", label=f"Mediana: {int(mediana_dias)} dias")
        eixo.legend()
        figura.savefig(os.path.join(self.diretorio_saida, "rq04_atualizacao.png"), dpi=150)
        plt.close(figura)
        print("Gráfico RQ04 salvo.")

    def _rq05_linguagens(self, df):
        top_linguagens = df["Linguagem Principal"].value_counts().head(15)
        figura, eixo = plt.subplots(figsize=(10, 7))
        top_linguagens.sort_values().plot(kind="barh", ax=eixo, color="cornflowerblue", edgecolor="white")
        eixo.set_title("RQ05 – Linguagens Primárias dos Repositórios Populares (Top 15)")
        eixo.set_xlabel("Número de Repositórios")
        eixo.set_ylabel("Linguagem")
        eixo.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        figura.savefig(os.path.join(self.diretorio_saida, "rq05_linguagens.png"), dpi=150)
        plt.close(figura)
        print("Gráfico RQ05 salvo.")

    def _rq06_issues_fechadas(self, df):
        figura, eixo = plt.subplots(figsize=(10, 5))
        eixo.hist(df["Razão Issues Fechadas"], bins=20, color="tomato", edgecolor="white")
        eixo.set_title("RQ06 – Distribuição da Razão de Issues Fechadas")
        eixo.set_xlabel("Proporção de Issues Fechadas (0 a 1)")
        eixo.set_ylabel("Número de Repositórios")
        mediana_proporcao = df["Razão Issues Fechadas"].median()
        eixo.axvline(mediana_proporcao, color="navy", linestyle="--", label=f"Mediana: {mediana_proporcao:.2f}")
        eixo.legend()
        figura.savefig(os.path.join(self.diretorio_saida, "rq06_issues_fechadas.png"), dpi=150)
        plt.close(figura)
        print("Gráfico RQ06 salvo.")

