import argparse
import pandas as pd

from adapters.github_graphql_adapter import fetch_repositories
from config.settings import load_settings
from services.repository_analysis_service import process_repositories
from services.report_service import generate_html_report, plot_graphs


def _parse_args():
    """Centraliza configuracao dos argumentos CLI para controlar intervalo e verbosidade da coleta."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0, help="Indice de inicio")
    parser.add_argument("--end", type=int, default=1000, help="Indice final")
    parser.add_argument("--quiet", action="store_true", help="Suprimir a saida no terminal")
    parser.add_argument("--demo", action="store_true", help="Modo demo: gera metricas fake sem executar CK real")
    return parser.parse_args()


def _configure_pandas_display():
    """Padroniza opcoes de exibicao para facilitar depuracao local com DataFrames extensos."""

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)


def main():
    """Orquestra o pipeline do Lab02: coleta, processamento de qualidade e geracao de relatorio HTML."""

    args = _parse_args()
    settings = load_settings()

    if not settings.token:
        raise RuntimeError("Token nao configurado. Defina TOKEN ou GITHUB_TOKEN no ambiente/.env.")

    if not args.quiet:
        print("Iniciando a coleta de dados dos repositorios...")

    repositories = fetch_repositories(args.start, args.end, settings, quiet=args.quiet)
    if not repositories:
        if not args.quiet:
            print("Nenhum repositorio retornado pela consulta.")
        return

    df = process_repositories(repositories, settings, quiet=args.quiet, demo_mode=args.demo)
    if df.empty:
        if not args.quiet:
            print("Nenhum repositorio valido apos processamento.")
        return

    _configure_pandas_display()

    if not args.quiet:
        print(df.to_string())

    graphs = plot_graphs(df)
    report_path = settings.reports_dir / "report.html"
    generate_html_report(df, graphs, report_path)

    if not args.quiet:
        print(f"Relatorio gerado em: {report_path}")


if __name__ == "__main__":
    main()
