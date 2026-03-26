from adapters.github_graphql_adapter import fetch_repositories
from config.settings import load_settings
from services.repository_analysis_service import process_repositories
from services.report_service import generate_html_report as _generate_html_report
from services.report_service import plot_graphs


def fetchRepositories(start, end):
    settings = load_settings()
    return fetch_repositories(start, end, settings, quiet=False)


def processData(repositories):
    settings = load_settings()
    return process_repositories(repositories, settings, quiet=False)


def plotGraphs(df, output_dir="Lab02/reports"):
    return plot_graphs(df)


def generate_html_report(df, graphs, report_path="Lab02/reports/report.html"):

    _generate_html_report(df, graphs, report_path)

