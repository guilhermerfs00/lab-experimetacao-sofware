import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd

from adapters.github_graphql_adapter import fetch_repositories
from config.settings import load_settings
from services.repository_analysis_service import process_single_repository


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0, help="Indice inicial da busca")
    parser.add_argument("--end", type=int, default=1000, help="Indice final da busca")
    parser.add_argument("--demo", action="store_true", help="Gera metricas fake sem executar CK real")
    parser.add_argument("--quiet", action="store_true", help="Reduz logs no terminal")
    return parser.parse_args()


def _to_list_rows(repositories: List[Dict]) -> List[Dict]:
    rows = []
    for item in repositories:
        node = item.get("node", {})
        owner = node.get("owner", {}).get("login", "")
        name = node.get("name", "")
        rows.append(
            {
                "Nome": name,
                "Proprietario": owner,
                "Url": f"https://github.com/{owner}/{name}" if owner and name else "",
                "Estrelas": node.get("stargazerCount", 0),
                "Data Criacao": node.get("createdAt", ""),
                "Data Atualizacao": node.get("updatedAt", ""),
                "Linguagem Principal": (node.get("primaryLanguage") or {}).get("name", ""),
                "Pull Requests Aceitos": (node.get("pullRequests") or {}).get("totalCount", 0),
                "Releases": (node.get("releases") or {}).get("totalCount", 0),
                "Issues Abertas": (node.get("openIssues") or {}).get("totalCount", 0),
                "Issues Fechadas": (node.get("closedIssues") or {}).get("totalCount", 0),
            }
        )
    return rows


def _salvar_lista_1000(repositories: List[Dict], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "repositorios_java_1000.csv"
    pd.DataFrame(_to_list_rows(repositories)).to_csv(csv_path, index=False, encoding="utf-8-sig")
    return csv_path


def _coletar_primeiro_resultado_de_metricas(repositories: List[Dict], settings, demo_mode: bool, quiet: bool) -> Dict:
    for repository in repositories:
        node = repository.get("node")
        if not node:
            continue
        row = process_single_repository(node, settings, quiet=quiet, demo_mode=demo_mode)
        if row is not None:
            return row
    return {}


def _salvar_csv_um_repositorio(row: Dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "metricas_1_repositorio.csv"
    pd.DataFrame([row]).to_csv(csv_path, index=False, encoding="utf-8-sig")
    return csv_path


def main():
    args = _parse_args()
    settings = load_settings()

    if not settings.token:
        raise RuntimeError("Token nao configurado. Defina TOKEN ou GITHUB_TOKEN no ambiente/.env.")

    repositories = fetch_repositories(args.start, args.end, settings, quiet=args.quiet)
    if not repositories:
        raise RuntimeError("Nenhum repositorio retornado pela consulta.")

    output_dir = settings.reports_dir
    lista_csv = _salvar_lista_1000(repositories, output_dir)

    row = _coletar_primeiro_resultado_de_metricas(
        repositories=repositories,
        settings=settings,
        demo_mode=args.demo,
        quiet=args.quiet,
    )
    if not row:
        raise RuntimeError("Nao foi possivel coletar metricas de nenhum repositorio nesta execucao.")

    metricas_csv = _salvar_csv_um_repositorio(row, output_dir)

    print(f"Lista gerada em: {lista_csv}")
    print(f"Metricas de 1 repositorio em: {metricas_csv}")


if __name__ == "__main__":
    main()

