from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd

from adapters.git_repository_adapter import (
    build_repo_url,
    clean_repo_name,
    clone_repo,
    count_java_lines,
    has_java_files,
    remove_path,
)
from adapters.quality_metrics_adapter import run_ck, summarize_ck_results
from config.settings import Settings


def calculate_repo_age_years(creation_date: str) -> float:
    """Converte data de criacao do GitHub para idade aproximada do repositorio em anos."""

    repo_age = datetime.now(timezone.utc) - pd.to_datetime(creation_date)
    return round(float(repo_age.days / 365.25), 1)


def _build_repo_row(node: Dict, repo_age: float, code_lines: int, comment_lines: int, quality_metrics: Dict) -> Dict:
    """Consolida os dados de processo e qualidade em uma linha do DataFrame final."""

    return {
        "Nome": node["name"],
        "Proprietário": node["owner"]["login"],
        "Idade": repo_age,
        "Estrelas": node["stargazerCount"],
        "Pull Requests Aceitos": node["pullRequests"]["totalCount"],
        "Releases": node["releases"]["totalCount"],
        "Linhas de código": code_lines,
        "Linhas de comentário": comment_lines,
        **quality_metrics,
    }


def process_single_repository(node: Dict, settings: Settings, quiet: bool = False, demo_mode: bool = False) -> Optional[Dict]:
    """Executa o fluxo completo para um repositorio: clone, contagem Java, CK e agregacao de resultados.
    
    Args:
        node: dados do repositorio da API GraphQL
        settings: configuracoes compartilhadas (paths, token, etc)
        quiet: suprime mensagens de log
        demo_mode: se True, gera metricas fake em vez de executar CK real (util para validacao sem JAR)
    """

    repo_name = node["name"]
    owner = node["owner"]["login"]
    local_repo_name = clean_repo_name(repo_name)

    repo_url = build_repo_url(owner, repo_name)
    repo_path = settings.repo_base_dir / local_repo_name
    metrics_output_path = settings.repo_base_dir / "_ck_output" / local_repo_name

    try:
        clone_repo(repo_path, repo_url)

        if not has_java_files(repo_path):
            if not quiet:
                print(f"Repositorio ignorado (sem .java): {owner}/{repo_name}")
            return None

        code_lines, comment_lines = count_java_lines(repo_path)
        run_ck(repo_path, metrics_output_path, settings.ck_jar_path, demo_mode=demo_mode)
        quality_metrics = summarize_ck_results(metrics_output_path)
        repo_age = calculate_repo_age_years(node["createdAt"])

        return _build_repo_row(node, repo_age, code_lines, comment_lines, quality_metrics)

    except Exception as exc:
        if not quiet:
            print(f"Falha ao processar {owner}/{repo_name}: {exc}")
        return None
    finally:
        remove_path(repo_path)
        remove_path(metrics_output_path)


def process_repositories(repositories: List[Dict], settings: Settings, quiet: bool = False, demo_mode: bool = False) -> pd.DataFrame:
    """Processa todos os repositorios coletados e retorna DataFrame pronto para relatorio e graficos.
    
    Args:
        repositories: lista de edges GraphQL retornados pela coleta
        settings: configuracoes compartilhadas
        quiet: suprime logs
        demo_mode: se True, gera metricas fake em vez de executar CK real
    """

    rows = []
    for repo in repositories:
        node = repo.get("node")
        if not node:
            continue

        row = process_single_repository(node, settings, quiet=quiet, demo_mode=demo_mode)
        if row is not None:
            rows.append(row)

    return pd.DataFrame(rows)

