# -*- coding: utf-8 -*-
"""
main.py - Lab04: Conventional Commits e Taxa de Merge em Pull Requests Java

Questão central:
  PRs com título no padrão Conventional Commits têm maior taxa de merge?

Uso:
    python main.py                     -> coleta 200 repos + PRs (padrão)
    python main.py --repos 50          -> limita a 50 repositórios
    python main.py --prs-per-repo 100  -> limita PRs por repositório
"""

import argparse
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

import repositories_adapter
import pr_adapter

# Força UTF-8 no Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ──────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────
_DOCS_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
os.makedirs(_DOCS_DIR, exist_ok=True)

DATASET_PATH     = os.path.join(_DOCS_DIR, "prs_dataset.csv")
REPOS_PATH       = os.path.join(_DOCS_DIR, "repos_selected.csv")
TOP_REPOS        = 100    # repositórios Java a coletar
MAX_PRS_PER_REPO = 200    # PRs por repositório (100 MERGED + 100 CLOSED)
MAX_WORKERS      = 3      # threads paralelas

_write_lock = threading.Lock()


# ──────────────────────────────────────────────
# Coleta de um repositório
# ──────────────────────────────────────────────
def _collect_repo(idx: int, total: int, row: dict,
                  already_done: set, all_prs: list) -> int:
    repo_full = row["repo"]
    if repo_full in already_done:
        print(f"  [{idx}/{total}] Pulando {repo_full} (já coletado)")
        return 0

    print(f"  [{idx}/{total}] Coletando PRs de {repo_full}...")
    try:
        prs = pr_adapter.fetch_prs_for_repo(
            owner=row["owner"],
            repo=row["name"],
            max_prs=MAX_PRS_PER_REPO,
        )
    except Exception as e:
        print(f"  [ERROR] Falha em {repo_full}: {e}")
        return 0

    with _write_lock:
        all_prs.extend(prs)
        pd.DataFrame(all_prs).to_csv(DATASET_PATH, index=False, encoding="utf-8-sig")

    print(f"  [{idx}/{total}] {repo_full} -> {len(prs)} PRs "
          f"(total acumulado: {len(all_prs)})")
    return len(prs)


# ──────────────────────────────────────────────
# Orquestração principal
# ──────────────────────────────────────────────
def collect(top_repos: int = TOP_REPOS, max_prs: int = MAX_PRS_PER_REPO):
    global MAX_PRS_PER_REPO
    MAX_PRS_PER_REPO = max_prs

    # ── 1. Repositórios ────────────────────────
    if os.path.exists(REPOS_PATH):
        df_repos = pd.read_csv(REPOS_PATH)
        print(f"[INFO] Usando repos_selected.csv existente ({len(df_repos)} repos).")
    else:
        print("\n[INFO] Coletando repositórios Java populares...\n")
        raw_repos = repositories_adapter.fetch_top_repositories(total=top_repos)
        df_repos = pd.DataFrame(raw_repos)
        df_repos.to_csv(REPOS_PATH, index=False, encoding="utf-8-sig")
        print(f"\n[OK] {len(df_repos)} repositórios salvos em '{REPOS_PATH}'\n")

    df_repos = df_repos.head(top_repos)

    # ── 2. Checkpoint ──────────────────────────
    already_done: set = set()
    all_prs: list = []
    if os.path.exists(DATASET_PATH):
        df_existing = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
        already_done = set(df_existing["repository"].unique())
        all_prs = df_existing.to_dict("records")
        print(f"[INFO] Checkpoint: {len(already_done)} repos já coletados "
              f"({len(all_prs)} PRs).")

    # ── 3. Coleta paralela ─────────────────────
    total = len(df_repos)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                _collect_repo, idx + 1, total, row, already_done, all_prs
            ): row["repo"]
            for idx, row in enumerate(df_repos.to_dict("records"))
        }
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"[ERROR] Worker falhou: {e}")

    # ── 4. Persistir e resumir ─────────────────
    df_final = pd.DataFrame(all_prs)
    df_final.to_csv(DATASET_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[CONCLUÍDO] {len(df_final)} PRs salvos em '{DATASET_PATH}'")
    _print_summary(df_final)


# ──────────────────────────────────────────────
# Resumo
# ──────────────────────────────────────────────
def _print_summary(df: pd.DataFrame):
    print("\n" + "=" * 55)
    print("RESUMO DO DATASET – PULL REQUESTS")
    print("=" * 55)
    print(f"Total de PRs             : {len(df)}")
    print(f"Total de repositórios    : {df['repository'].nunique()}")

    merged = (df["is_merged"] == "Sim").sum()
    closed = (df["is_merged"] == "Não").sum()
    print(f"PRs MERGED               : {merged} ({merged/len(df)*100:.1f}%)")
    print(f"PRs CLOSED (rejeitados)  : {closed} ({closed/len(df)*100:.1f}%)")

    conv = (df["title_is_conventional"] == "Sim").sum()
    print(f"PRs com título CC        : {conv} ({conv/len(df)*100:.1f}%)")

    # Taxa de merge por grupo
    df_conv  = df[df["title_is_conventional"] == "Sim"]
    df_nconv = df[df["title_is_conventional"] == "Não"]
    if len(df_conv) > 0:
        taxa_conv  = (df_conv["is_merged"]  == "Sim").sum() / len(df_conv)  * 100
        taxa_nconv = (df_nconv["is_merged"] == "Sim").sum() / len(df_nconv) * 100 if len(df_nconv) > 0 else 0
        print(f"\nTaxa de merge CC         : {taxa_conv:.1f}%")
        print(f"Taxa de merge Não-CC     : {taxa_nconv:.1f}%")
        print(f"Diferença                : {taxa_conv - taxa_nconv:+.1f} p.p.")

    print("\nDistribuição por tipo CC:")
    print(df["conventional_type"].value_counts().head(12).to_string())
    print("=" * 55 + "\n")


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Lab04 – Coleta PRs Java para análise de Conventional Commits no Power BI"
    )
    parser.add_argument("--repos", type=int, default=TOP_REPOS,
                        help=f"Repositórios a coletar (padrão: {TOP_REPOS})")
    parser.add_argument("--prs-per-repo", type=int, default=MAX_PRS_PER_REPO,
                        help=f"PRs por repositório (padrão: {MAX_PRS_PER_REPO})")
    args = parser.parse_args()

    collect(top_repos=args.repos, max_prs=args.prs_per_repo)


if __name__ == "__main__":
    main()
