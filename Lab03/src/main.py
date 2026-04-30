# -*- coding: utf-8 -*-
"""
main.py  -  Lab03: Caracterizando a Atividade de Code Review no GitHub
Execucao:
    python main.py --collect   -> coleta repositorios + PRs e salva prs_dataset.csv
    python main.py --analyse   -> carrega prs_dataset.csv e gera analises / graficos
    python main.py             -> executa coleta + analise
"""

import argparse
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

import repositories_adapter
import pr_adapter
import analysis

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuracoes
DATASET_PATH = "prs_dataset.csv"
REPOS_PATH = "repos_selected.csv"
TOP_REPOS = 200          # numero de repositorios mais populares a avaliar
MAX_PRS_PER_REPO = 200   # limite de PRs coletados por repositorio
MAX_WORKERS = 5          # workers paralelos para coleta de PRs

# Lock global para escrita thread-safe no dataset
_write_lock = threading.Lock()


def _collect_repo(idx: int, total: int, row: dict, already_done: set,
                  all_prs: list, save_path: str) -> int:
    """Coleta PRs de um unico repositorio (executado em worker thread)."""
    repo_full = row["repo"]
    if repo_full in already_done:
        print(f"  [{idx}/{total}] Pulando {repo_full} (ja coletado)")
        return 0

    print(f"  [{idx}/{total}] Coletando PRs de {repo_full}...")
    try:
        prs = pr_adapter.fetch_prs_for_repo(row["owner"], row["name"], max_prs=MAX_PRS_PER_REPO)
    except Exception as e:
        print(f"  [ERROR] Falha ao coletar {repo_full}: {e}. Pulando...")
        prs = []

    with _write_lock:
        all_prs.extend(prs)
        total_so_far = len(all_prs)
        pd.DataFrame(all_prs).to_csv(save_path, index=False)

    print(f"  [{idx}/{total}] {repo_full} -> {len(prs)} PRs (total acumulado: {total_so_far})")
    return len(prs)


def collect():
    """Coleta os repositorios e PRs, salvando o dataset em CSV."""
    print("\n[INFO] Iniciando coleta de repositorios populares...\n")
    raw_repos = repositories_adapter.fetch_top_repositories(total=TOP_REPOS, batch_size=25)

    repos_info = []
    for r in raw_repos:
        node = r["node"]
        repos_info.append({
            "repo": node["nameWithOwner"],
            "owner": node["owner"]["login"],
            "name": node["name"],
            "stars": node["stargazerCount"],
            "total_prs_merged_closed": node["pullRequests"]["totalCount"],
        })

    df_repos = pd.DataFrame(repos_info)
    df_repos.to_csv(REPOS_PATH, index=False)
    print(f"[OK] {len(df_repos)} repositorios selecionados e salvos em '{REPOS_PATH}'")
    print(df_repos[["repo", "stars", "total_prs_merged_closed"]].to_string(index=False))

    # Resume support: load already collected PRs if dataset exists
    if os.path.exists(DATASET_PATH):
        df_existing = pd.read_csv(DATASET_PATH)
        already_done = set(df_existing["repo"].unique())
        all_prs = df_existing.to_dict("records")
        print(f"\n[INFO] Retomando coleta. {len(already_done)} repos ja processados ({len(all_prs)} PRs).")
    else:
        already_done = set()
        all_prs = []

    print(f"\n\n[INFO] Iniciando coleta de Pull Requests com {MAX_WORKERS} workers paralelos...\n")
    total = len(df_repos)
    rows = [row for _, row in df_repos.iterrows()]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                _collect_repo, i + 1, total, rows[i], already_done, all_prs, DATASET_PATH
            ): rows[i]["repo"]
            for i in range(total)
        }
        for future in as_completed(futures):
            repo = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"  [ERROR] Excecao nao tratada em {repo}: {e}")

    with _write_lock:
        df_prs = pd.DataFrame(all_prs)
        df_prs.to_csv(DATASET_PATH, index=False)

    print(f"\n[OK] Dataset salvo em '{DATASET_PATH}' com {len(df_prs)} PRs.\n")
    return df_prs


def analyse(df: pd.DataFrame = None):
    """Carrega o dataset (se necessario) e executa todas as analises."""
    if df is None:
        if not os.path.exists(DATASET_PATH):
            print(f"[WARN] Dataset '{DATASET_PATH}' nao encontrado. Execute com --collect primeiro.")
            return
        df = analysis.load_dataset(DATASET_PATH)

    print(f"\n[INFO] Dataset carregado: {len(df)} PRs de {df['repo'].nunique()} repositorios.\n")

    # Estatisticas descritivas
    analysis.print_medians(df)

    # Correlacoes (8 RQs)
    print("\n" + "=" * 70)
    print("CORRELACOES DE SPEARMAN - RQ01 a RQ08")
    print("=" * 70)
    analysis.run_rq_analysis(df)

    # Graficos
    analysis.plot_boxplots(df)
    analysis.plot_scatter_reviews(df)


def main():
    parser = argparse.ArgumentParser(description="Lab03 - Code Review no GitHub")
    parser.add_argument("--collect", action="store_true", help="Coleta repositorios e PRs")
    parser.add_argument("--analyse", action="store_true", help="Analisa o dataset coletado")
    args = parser.parse_args()

    if args.collect and not args.analyse:
        collect()
    elif args.analyse and not args.collect:
        analyse()
    else:
        # padrao: coleta + analise
        df = collect()
        analyse(df)


if __name__ == "__main__":
    main()

