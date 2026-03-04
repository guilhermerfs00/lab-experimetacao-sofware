import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime, timezone

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "graphs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

NOW = datetime.now(timezone.utc)


def processData(repositories):
    repoList = []

    for repo in repositories:
        node = repo['node']

        criado_em = datetime.fromisoformat(node['createdAt'].replace("Z", "+00:00"))
        atualizado_em = datetime.fromisoformat(node['updatedAt'].replace("Z", "+00:00"))

        idade_anos = round((NOW - criado_em).days / 365.25, 2)
        dias_atualizacao = (NOW - atualizado_em).days

        total_issues = node['totalIssues']['totalCount']
        closed_issues = node['closedIssues']['totalCount']
        closed_ratio = round(closed_issues / total_issues, 4) if total_issues > 0 else 0.0

        repoList.append({
            "Nome": node['name'],
            "Proprietário": node['owner']['login'],
            "Estrelas": node['stargazerCount'],
            "Data de Criação": node['createdAt'],
            "Idade (anos)": idade_anos,
            "Pull Requests Aceitos": node['pullRequests']['totalCount'],
            "Releases": node['releases']['totalCount'],
            "Última Atualização": node['updatedAt'],
            "Dias Desde Atualização": dias_atualizacao,
            "Linguagem Principal": node['primaryLanguage']['name'] if node['primaryLanguage'] else "Desconhecida",
            "Total de Issues": total_issues,
            "Issues Fechadas": closed_issues,
            "Razão Issues Fechadas": closed_ratio,
        })

    return pd.DataFrame(repoList)


def saveResults(df):
    csv_path = os.path.join(OUTPUT_DIR, "repositorios.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nDados salvos em: {csv_path}")


def generateGraphs(df):
    plt.rcParams.update({"figure.autolayout": True, "font.size": 11})

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(df["Idade (anos)"], bins=20, color="steelblue", edgecolor="white")
    ax.set_title("RQ01 – Distribuição da Idade dos Repositórios Populares")
    ax.set_xlabel("Idade (anos)")
    ax.set_ylabel("Número de Repositórios")
    median_age = df["Idade (anos)"].median()
    ax.axvline(median_age, color="red", linestyle="--", label=f"Mediana: {median_age:.1f} anos")
    ax.legend()
    fig.savefig(os.path.join(OUTPUT_DIR, "rq01_idade.png"), dpi=150)
    plt.close(fig)
    print("Gráfico RQ01 salvo.")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(df["Pull Requests Aceitos"], bins=30, color="darkorange", edgecolor="white")
    ax.set_title("RQ02 – Distribuição de Pull Requests Aceitas")
    ax.set_xlabel("Total de PRs Aceitas")
    ax.set_ylabel("Número de Repositórios")
    ax.set_yscale("log")
    median_pr = df["Pull Requests Aceitos"].median()
    ax.axvline(median_pr, color="red", linestyle="--", label=f"Mediana: {int(median_pr)}")
    ax.legend()
    fig.savefig(os.path.join(OUTPUT_DIR, "rq02_pull_requests.png"), dpi=150)
    plt.close(fig)
    print("Gráfico RQ02 salvo.")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(df["Releases"], bins=30, color="seagreen", edgecolor="white")
    ax.set_title("RQ03 – Distribuição do Total de Releases")
    ax.set_xlabel("Total de Releases")
    ax.set_ylabel("Número de Repositórios")
    ax.set_yscale("log")
    median_rel = df["Releases"].median()
    ax.axvline(median_rel, color="red", linestyle="--", label=f"Mediana: {int(median_rel)}")
    ax.legend()
    fig.savefig(os.path.join(OUTPUT_DIR, "rq03_releases.png"), dpi=150)
    plt.close(fig)
    print("Gráfico RQ03 salvo.")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(df["Dias Desde Atualização"], bins=30, color="mediumpurple", edgecolor="white")
    ax.set_title("RQ04 – Dias Desde a Última Atualização")
    ax.set_xlabel("Dias")
    ax.set_ylabel("Número de Repositórios")
    median_upd = df["Dias Desde Atualização"].median()
    ax.axvline(median_upd, color="red", linestyle="--", label=f"Mediana: {int(median_upd)} dias")
    ax.legend()
    fig.savefig(os.path.join(OUTPUT_DIR, "rq04_atualizacao.png"), dpi=150)
    plt.close(fig)
    print("Gráfico RQ04 salvo.")

    lang_counts = df["Linguagem Principal"].value_counts().head(15)
    fig, ax = plt.subplots(figsize=(10, 7))
    lang_counts.sort_values().plot(kind="barh", ax=ax, color="cornflowerblue", edgecolor="white")
    ax.set_title("RQ05 – Linguagens Primárias dos Repositórios Populares (Top 15)")
    ax.set_xlabel("Número de Repositórios")
    ax.set_ylabel("Linguagem")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    fig.savefig(os.path.join(OUTPUT_DIR, "rq05_linguagens.png"), dpi=150)
    plt.close(fig)
    print("Gráfico RQ05 salvo.")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(df["Razão Issues Fechadas"], bins=20, color="tomato", edgecolor="white")
    ax.set_title("RQ06 – Distribuição da Razão de Issues Fechadas")
    ax.set_xlabel("Proporção de Issues Fechadas (0 a 1)")
    ax.set_ylabel("Número de Repositórios")
    median_iss = df["Razão Issues Fechadas"].median()
    ax.axvline(median_iss, color="navy", linestyle="--", label=f"Mediana: {median_iss:.2f}")
    ax.legend()
    fig.savefig(os.path.join(OUTPUT_DIR, "rq06_issues_fechadas.png"), dpi=150)
    plt.close(fig)
    print("Gráfico RQ06 salvo.")


def printReport(df):
    total = len(df)
    print("\n" + "=" * 60)
    print(f"  RELATÓRIO FINAL – {total} repositórios analisados")
    print("=" * 60)
    print(f"RQ01 – Idade (mediana):                  {df['Idade (anos)'].median():.2f} anos")
    print(f"RQ02 – Pull Requests Aceitas (mediana):  {df['Pull Requests Aceitos'].median():.0f}")
    print(f"RQ03 – Releases (mediana):               {df['Releases'].median():.0f}")
    print(f"RQ04 – Dias desde atualização (mediana): {df['Dias Desde Atualização'].median():.0f} dias")
    top_lang = df["Linguagem Principal"].value_counts().idxmax()
    print(f"RQ05 – Linguagem mais frequente:         {top_lang}")
    print(f"RQ06 – Razão issues fechadas (mediana):  {df['Razão Issues Fechadas'].median():.2%}")
    print("=" * 60)
