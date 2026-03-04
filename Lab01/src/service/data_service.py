import os
import pandas as pd
from datetime import datetime, timezone

from .gerador_graficos import GeradorGraficos
from .csv_resultados import CsvResultados

DIRETORIO_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "graphs")
os.makedirs(DIRETORIO_SAIDA, exist_ok=True)

DATA_HORA_ATUAL = datetime.now(timezone.utc)


def processarDados(repositorios):
    lista_repos = []

    for repositorio in repositorios:
        node = repositorio['node']

        data_criacao     = datetime.fromisoformat(node['createdAt'].replace("Z", "+00:00"))
        data_atualizacao = datetime.fromisoformat(node['updatedAt'].replace("Z", "+00:00"))

        idade_em_anos        = round((DATA_HORA_ATUAL - data_criacao).days / 365.25, 2)
        dias_desde_atualizacao = (DATA_HORA_ATUAL - data_atualizacao).days

        total_issues    = node['totalIssues']['totalCount']
        issues_fechadas = node['closedIssues']['totalCount']
        proporcao_issues_fechadas = round(issues_fechadas / total_issues, 4) if total_issues > 0 else 0.0

        lista_repos.append({
            "Nome": node['name'],
            "Proprietário": node['owner']['login'],
            "Estrelas": node['stargazerCount'],
            "Data de Criação": node['createdAt'],
            "Idade (anos)": idade_em_anos,
            "Pull Requests Aceitos": node['pullRequests']['totalCount'],
            "Releases": node['releases']['totalCount'],
            "Última Atualização": node['updatedAt'],
            "Dias Desde Atualização": dias_desde_atualizacao,
            "Linguagem Principal": node['primaryLanguage']['name'] if node['primaryLanguage'] else "Desconhecida",
            "Total de Issues": total_issues,
            "Issues Fechadas": issues_fechadas,
            "Razão Issues Fechadas": proporcao_issues_fechadas,
        })

    return pd.DataFrame(lista_repos)


def salvarResultados(df):
    salvador = CsvResultados(DIRETORIO_SAIDA)
    salvador.salvar(df)


def gerarGraficos(df):
    gerador = GeradorGraficos(DIRETORIO_SAIDA)
    gerador.gerar(df)
