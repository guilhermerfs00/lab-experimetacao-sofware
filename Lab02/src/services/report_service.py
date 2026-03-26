import base64
import io
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import pandas as pd


def _build_metric_figure(df: pd.DataFrame, metric: str) -> str:
    """Gera um SVG em base64 para uma metrica, comparando popularidade e maturidade com qualidade."""

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].scatter(df["Estrelas"], df[metric], color="blue", alpha=0.5)
    axes[0].set_title(f"Popularidade vs {metric}")
    axes[0].set_xlabel("Estrelas")
    axes[0].set_ylabel(metric)
    axes[0].grid(True)

    axes[1].scatter(df["Idade"], df[metric], color="green", alpha=0.5)
    axes[1].set_title(f"Maturidade vs {metric}")
    axes[1].set_xlabel("Idade (anos)")
    axes[1].set_ylabel(metric)
    axes[1].grid(True)

    plt.tight_layout()

    svg_output = io.StringIO()
    fig.savefig(svg_output, format="svg")
    svg_output.seek(0)
    encoded_svg = base64.b64encode(svg_output.getvalue().encode("utf-8")).decode("utf-8")
    plt.close(fig)

    return f"data:image/svg+xml;base64,{encoded_svg}"


def plot_graphs(df: pd.DataFrame) -> List[str]:
    """Produz lista de graficos em base64 para embutir diretamente no HTML do relatorio."""

    metrics = ["Média CBO (Classes)", "Média DIT (Classes)", "Média LCOM (Classes)"]
    available_metrics = [metric for metric in metrics if metric in df.columns]
    return [_build_metric_figure(df, metric) for metric in available_metrics]


def generate_html_report(df: pd.DataFrame, graphs: List[str], report_path) -> None:
    """Monta um HTML simples com tabela consolidada e graficos embutidos em base64."""

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatorio de Repositorios</title>
        <style>
            body { font-family: Arial, sans-serif; }
            h1 { color: #2c3e50; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
            .graph { width: 100%; margin-top: 30px; }
        </style>
    </head>
    <body>
        <h1>Relatorio de Repositorios GitHub</h1>
        <h2>Dados dos Repositorios</h2>
        <table>
            <thead>
                <tr>
                    <th>Nome</th>
                    <th>Proprietario</th>
                    <th>Idade</th>
                    <th>Estrelas</th>
                    <th>Pull Requests Aceitos</th>
                    <th>Releases</th>
                    <th>Linhas de Codigo</th>
                    <th>Linhas de Comentario</th>
                    <th>Media CBO (Classes)</th>
                    <th>Media DIT (Classes)</th>
                    <th>Media LCOM (Classes)</th>
                </tr>
            </thead>
            <tbody>
    """

    for _, row in df.iterrows():
        html_content += f"""
        <tr>
            <td>{row.get('Nome', '')}</td>
            <td>{row.get('Proprietário', '')}</td>
            <td>{row.get('Idade', '')}</td>
            <td>{row.get('Estrelas', '')}</td>
            <td>{row.get('Pull Requests Aceitos', '')}</td>
            <td>{row.get('Releases', '')}</td>
            <td>{row.get('Linhas de código', '')}</td>
            <td>{row.get('Linhas de comentário', '')}</td>
            <td>{row.get('Média CBO (Classes)', '')}</td>
            <td>{row.get('Média DIT (Classes)', '')}</td>
            <td>{row.get('Média LCOM (Classes)', '')}</td>
        </tr>
        """

    html_content += """
            </tbody>
        </table>
        <h2>Graficos</h2>
    """

    for index, graph in enumerate(graphs, start=1):
        html_content += f"""
        <div class="graph">
            <h3>Grafico {index}</h3>
            <img src="{graph}" alt="Grafico {index}">
        </div>
        """

    html_content += """
    </body>
    </html>
    """

    report_path.write_text(html_content, encoding="utf-8")

