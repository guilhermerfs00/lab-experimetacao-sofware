"""Gera o relatório final do Lab02 em DOCX e PDF a partir do `report.html` existente.

O relatório consolida a amostra coletada pela pipeline atual, sumariza as métricas
processuais e de qualidade, e discute as correlações entre popularidade, maturidade,
atividade e tamanho dos repositórios Java analisados.
"""

from __future__ import annotations

import argparse
import io
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import spearmanr


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
SOURCE_HTML = REPORTS_DIR / "report.html"
DEFAULT_DOCX = REPORTS_DIR / "relatorio_final.docx"
DEFAULT_PDF = REPORTS_DIR / "relatorio_final.pdf"

COLUMN_NAMES = [
    "Nome",
    "Proprietario",
    "Idade",
    "Estrelas",
    "Pull Requests Aceitos",
    "Releases",
    "Linhas de Codigo",
    "Linhas de Comentario",
    "CBO",
    "DIT",
    "LCOM",
]

PAIR_DEFINITIONS = [
    ("RQ1 - Popularidade", "Estrelas", "CBO", "popularidade"),
    ("RQ1 - Popularidade", "Estrelas", "DIT", "popularidade"),
    ("RQ1 - Popularidade", "Estrelas", "LCOM", "popularidade"),
    ("RQ2 - Maturidade", "Idade", "CBO", "maturidade"),
    ("RQ2 - Maturidade", "Idade", "DIT", "maturidade"),
    ("RQ2 - Maturidade", "Idade", "LCOM", "maturidade"),
    ("RQ3 - Atividade", "Releases", "CBO", "atividade"),
    ("RQ3 - Atividade", "Releases", "DIT", "atividade"),
    ("RQ3 - Atividade", "Releases", "LCOM", "atividade"),
    ("RQ4 - Tamanho", "Linhas de Codigo", "CBO", "tamanho"),
    ("RQ4 - Tamanho", "Linhas de Codigo", "DIT", "tamanho"),
    ("RQ4 - Tamanho", "Linhas de Codigo", "LCOM", "tamanho"),
    ("RQ4 - Tamanho", "Linhas de Comentario", "CBO", "tamanho"),
    ("RQ4 - Tamanho", "Linhas de Comentario", "DIT", "tamanho"),
    ("RQ4 - Tamanho", "Linhas de Comentario", "LCOM", "tamanho"),
]


@dataclass
class PairResult:
    rq: str
    x: str
    y: str
    n: int
    rho: float
    pvalue: float



def load_dataframe(html_path: Path) -> pd.DataFrame:
    if not html_path.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {html_path}")

    df = pd.read_html(html_path)[0]
    df.columns = COLUMN_NAMES
    df["Idade"] = df["Idade"].astype(str).str.replace(" anos", "", regex=False).astype(float)
    for column in ["Estrelas", "Pull Requests Aceitos", "Releases", "Linhas de Codigo", "Linhas de Comentario", "CBO", "DIT", "LCOM"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df



def format_number(value, digits: int = 2) -> str:
    if pd.isna(value):
        return "N/D"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.{digits}f}"



def summarize_metrics(df: pd.DataFrame) -> pd.DataFrame:
    metrics = ["Idade", "Estrelas", "Releases", "Linhas de Codigo", "Linhas de Comentario", "CBO", "DIT", "LCOM"]
    summary = df[metrics].agg(["mean", "median", "std"]).round(2)
    summary.index = ["Média", "Mediana", "Desvio padrão"]
    return summary



def compute_correlations(df: pd.DataFrame) -> list[PairResult]:
    results: list[PairResult] = []
    for rq, x, y, _group in PAIR_DEFINITIONS:
        pair_df = df[[x, y]].dropna()
        if pair_df.empty:
            results.append(PairResult(rq=rq, x=x, y=y, n=0, rho=float("nan"), pvalue=float("nan")))
            continue
        rho, pvalue = spearmanr(pair_df[x], pair_df[y])
        results.append(PairResult(rq=rq, x=x, y=y, n=len(pair_df), rho=float(rho), pvalue=float(pvalue)))
    return results



def build_rq_texts() -> dict[str, str]:
    return {
        "RQ1": (
            "Popularidade (estrelas) versus qualidade interna. A expectativa inicial era que "
            "repositórios mais populares recebessem mais revisão da comunidade e, por isso, "
            "apresentassem menor acoplamento e menor falta de coesão."
        ),
        "RQ2": (
            "Maturidade (idade) versus qualidade interna. A hipótese era que projetos mais antigos "
            "estariam mais refinados por refatorações e manutenção contínua, refletindo em métricas mais favoráveis."
        ),
        "RQ3": (
            "Atividade (releases) versus qualidade interna. Esperava-se que uma frequência maior de releases "
            "estivesse associada a um processo de evolução contínua e, portanto, a melhor qualidade de produto."
        ),
        "RQ4": (
            "Tamanho (LOC e linhas de comentários) versus qualidade interna. A hipótese era que repositórios maiores "
            "teriam maior complexidade estrutural, o que poderia elevar o acoplamento e a falta de coesão."
        ),
    }



def _rq_figure_title(group_name: str) -> str:
    titles = {
        "popularidade": "RQ1 - Popularidade (estrelas) vs métricas CK",
        "maturidade": "RQ2 - Maturidade (idade) vs métricas CK",
        "atividade": "RQ3 - Atividade (releases) vs métricas CK",
        "tamanho": "RQ4 - Tamanho (LOC/comentários) vs métricas CK",
    }
    return titles[group_name]



def create_rq_figure(df: pd.DataFrame, group_name: str) -> plt.Figure:
    if group_name == "popularidade":
        x_col = "Estrelas"
        x_label = "Estrelas"
    elif group_name == "maturidade":
        x_col = "Idade"
        x_label = "Idade (anos)"
    elif group_name == "atividade":
        x_col = "Releases"
        x_label = "Releases"
    else:
        x_col = None
        x_label = None

    quality_cols = ["CBO", "DIT", "LCOM"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    fig.suptitle(_rq_figure_title(group_name), fontsize=14, fontweight="bold")

    for ax, quality in zip(axes, quality_cols):
        if group_name == "tamanho":
            # Tamanho gera dois eixos separados: LOC e comentários.
            ax.set_axis_off()
            continue

        plot_df = df[[x_col, quality]].dropna()
        rho, pvalue = spearmanr(plot_df[x_col], plot_df[quality]) if len(plot_df) > 1 else (float("nan"), float("nan"))
        ax.scatter(plot_df[x_col], plot_df[quality], s=18, alpha=0.45, color="#1f77b4")
        ax.set_title(f"{quality}\nρ={rho:.3f} | p={pvalue:.3g}")
        ax.set_xlabel(x_label)
        ax.set_ylabel(quality)
        ax.grid(True, alpha=0.25)

    plt.tight_layout(rect=[0, 0, 1, 0.92])
    return fig



def create_size_figure(df: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle("RQ4 - Tamanho (LOC/comentários) vs métricas CK", fontsize=14, fontweight="bold")
    size_pairs = [
        ("Linhas de Codigo", "LOC"),
        ("Linhas de Comentario", "Comentários"),
    ]
    quality_cols = ["CBO", "DIT", "LCOM"]

    for row_index, (size_col, size_label) in enumerate(size_pairs):
        for col_index, quality in enumerate(quality_cols):
            ax = axes[row_index, col_index]
            plot_df = df[[size_col, quality]].dropna()
            rho, pvalue = spearmanr(plot_df[size_col], plot_df[quality]) if len(plot_df) > 1 else (float("nan"), float("nan"))
            ax.scatter(plot_df[size_col], plot_df[quality], s=18, alpha=0.45, color="#2ca02c")
            ax.set_title(f"{size_label} vs {quality}\nρ={rho:.3f} | p={pvalue:.3g}")
            ax.set_xlabel(size_label)
            ax.set_ylabel(quality)
            ax.grid(True, alpha=0.25)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    return fig



def create_summary_table_figure(summary: pd.DataFrame, df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(14, 4.8))
    ax.axis("off")
    table = summary.copy()
    display = table.reset_index().rename(columns={"index": "Medida"})
    display.columns = ["Medida"] + list(display.columns[1:])
    cell_text = display.values.tolist()
    col_labels = display.columns.tolist()
    ax.set_title(
        f"Resumo estatístico da amostra ({len(df)} repositórios; {df[['CBO','DIT','LCOM']].dropna().shape[0]} com CK completo)",
        fontweight="bold",
        pad=18,
    )
    tbl = ax.table(cellText=cell_text, colLabels=col_labels, loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.4)
    for (row, col), cell in tbl.get_celld().items():
        if row == 0:
            cell.set_facecolor("#d9e8f5")
            cell.set_text_props(weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f7f7f7")
    return fig



def create_correlation_table_figure(results: list[PairResult]) -> plt.Figure:
    rows = [[r.rq, r.x, r.y, r.n, f"{r.rho:.3f}", f"{r.pvalue:.3g}"] for r in results]
    fig, ax = plt.subplots(figsize=(16, 6.5))
    ax.axis("off")
    ax.set_title("Teste de correlação de Spearman", fontweight="bold", pad=16)
    table = ax.table(
        cellText=rows,
        colLabels=["RQ", "Variável X", "Variável Y", "N", "ρ", "p-valor"],
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.35)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#d9e8f5")
            cell.set_text_props(weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f7f7f7")
    return fig



def _add_docx_heading(doc: Document, text: str, level: int = 1):
    heading = doc.add_heading(text, level=level)
    if level == 0:
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return heading



def _add_docx_paragraph(doc: Document, text: str, *, bold: bool = False, italic: bool = False, size: int = 11):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(6)
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = "Calibri"
    run.font.size = Pt(size)
    return para



def _add_docx_bullets(doc: Document, bullets: Iterable[str]):
    for bullet in bullets:
        para = doc.add_paragraph(style="List Bullet")
        run = para.add_run(bullet)
        run.font.name = "Calibri"
        run.font.size = Pt(11)



def _docx_table_from_dataframe(doc: Document, df_table: pd.DataFrame):
    table = doc.add_table(rows=1, cols=len(df_table.columns))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for idx, col in enumerate(df_table.columns):
        hdr[idx].text = str(col)
    for _, row in df_table.iterrows():
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            cells[idx].text = str(value)



def build_docx(
    df: pd.DataFrame,
    summary: pd.DataFrame,
    correlations: list[PairResult],
    figures: dict[str, plt.Figure],
    output_path: Path,
):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    title = doc.add_heading("Relatório Final", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("Qualidade interna de repositórios Java populares no GitHub").bold = True
    subtitle.runs[0].font.size = Pt(15)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info.add_run("Laboratório 02 — análise com CK e correlação entre processo e qualidade").italic = True

    _add_docx_heading(doc, "1. Introdução e hipóteses iniciais", 1)
    _add_docx_paragraph(
        doc,
        "O desenvolvimento colaborativo em projetos open-source pode favorecer a evolução do software, "
        "mas também pode expor riscos internos ligados à modularidade, à manutenibilidade e à legibilidade. "
        "Neste laboratório, o objetivo foi analisar repositórios Java populares do GitHub e correlacionar "
        "características de processo com métricas de qualidade interna calculadas pela ferramenta CK.",
    )
    _add_docx_paragraph(
        doc,
        f"A amostra efetivamente disponível no `report.html` contém {len(df)} repositórios, com {df[['CBO','DIT','LCOM']].dropna().shape[0]} registros de CK completos.",
        italic=True,
    )
    _add_docx_paragraph(doc, "Hipóteses informais:", bold=True)
    _add_docx_bullets(
        doc,
        [
            "Repositórios mais populares tenderiam a apresentar qualidade interna ligeiramente melhor.",
            "Repositórios mais antigos tenderiam a estar mais refinados e, portanto, com métricas internas mais favoráveis.",
            "Mais releases indicariam um processo de evolução contínua, possivelmente associado a melhor qualidade.",
            "Repositórios maiores tenderiam a concentrar mais complexidade e, portanto, pior qualidade interna.",
        ],
    )

    _add_docx_heading(doc, "2. Metodologia", 1)
    _add_docx_paragraph(
        doc,
        "A coleta original usa a API GraphQL do GitHub para recuperar os repositórios Java mais populares, "
        "seguidos de clone local e execução do CK. O `report.html` gerado pela pipeline consolida os dados "
        "processuais e as médias das métricas de classe obtidas com o CK. Para este relatório final, "
        "a tabela do HTML foi usada como base de análise e os dados foram sumarizados com média, mediana, "
        "desvio padrão e correlação de Spearman.",
    )
    _add_docx_bullets(
        doc,
        [
            "Métricas de processo: estrelas, idade, releases, linhas de código e linhas de comentário.",
            "Métricas de qualidade: CBO, DIT e LCOM.",
            "Estatística descritiva: média, mediana e desvio padrão por métrica.",
            "Teste estatístico: correlação de Spearman com p-valor.",
        ],
    )

    _add_docx_heading(doc, "3. Resultados", 1)
    _add_docx_heading(doc, "3.1 Visão geral da amostra", 2)
    _add_docx_paragraph(
        doc,
        "Os dados mostram forte assimetria em LOC, linhas de comentário e LCOM, o que reforça o uso da mediana "
        "como medida central em vez de confiar apenas na média. Abaixo, o resumo estatístico da amostra.",
    )
    _docx_table_from_dataframe(doc, summary.reset_index().rename(columns={"index": "Medida"}).round(2))
    doc.add_paragraph()
    with io.BytesIO() as buffer:
        figures["summary"].savefig(buffer, format="png", dpi=200, bbox_inches="tight")
        buffer.seek(0)
        doc.add_picture(buffer, width=Inches(6.6))

    _add_docx_heading(doc, "3.2 RQ1 — popularidade versus qualidade", 2)
    _add_docx_paragraph(doc, build_rq_texts()["RQ1"])
    _add_docx_paragraph(
        doc,
        "O teste de Spearman indica relação negativa fraca entre estrelas e CBO/DIT, mas sem associação relevante "
        "entre estrelas e LCOM. Em outras palavras, popularidade sozinha não garante melhoria consistente da qualidade interna.",
    )
    with io.BytesIO() as buffer:
        figures["popularidade"].savefig(buffer, format="png", dpi=200, bbox_inches="tight")
        buffer.seek(0)
        doc.add_picture(buffer, width=Inches(6.7))

    _add_docx_heading(doc, "3.3 RQ2 — maturidade versus qualidade", 2)
    _add_docx_paragraph(doc, build_rq_texts()["RQ2"])
    _add_docx_paragraph(
        doc,
        "A idade não apresentou relação com CBO, mas mostrou correlação positiva com DIT e LCOM. "
        "Isso sugere que projetos mais antigos tendem a acumular mais estrutura hierárquica e alguma perda de coesão, "
        "em vez de melhorar automaticamente essas dimensões internas.",
    )
    with io.BytesIO() as buffer:
        figures["maturidade"].savefig(buffer, format="png", dpi=200, bbox_inches="tight")
        buffer.seek(0)
        doc.add_picture(buffer, width=Inches(6.7))

    _add_docx_heading(doc, "3.4 RQ3 — atividade versus qualidade", 2)
    _add_docx_paragraph(doc, build_rq_texts()["RQ3"])
    _add_docx_paragraph(
        doc,
        "Os resultados mostram correlação positiva entre número de releases e as três métricas de qualidade. "
        "Na amostra analisada, mais releases estão associados a mais acoplamento, maior profundidade de herança e maior falta de coesão.",
    )
    with io.BytesIO() as buffer:
        figures["atividade"].savefig(buffer, format="png", dpi=200, bbox_inches="tight")
        buffer.seek(0)
        doc.add_picture(buffer, width=Inches(6.7))

    _add_docx_heading(doc, "3.5 RQ4 — tamanho versus qualidade", 2)
    _add_docx_paragraph(doc, build_rq_texts()["RQ4"])
    _add_docx_paragraph(
        doc,
        "Esta foi a relação mais consistente da análise: repositórios com mais LOC e mais comentários tendem a exibir "
        "maiores valores de CBO, DIT e LCOM. O padrão é compatível com a hipótese de que o crescimento do sistema "
        "aumenta a complexidade interna.",
    )
    with io.BytesIO() as buffer:
        figures["tamanho"].savefig(buffer, format="png", dpi=200, bbox_inches="tight")
        buffer.seek(0)
        doc.add_picture(buffer, width=Inches(6.7))

    _add_docx_heading(doc, "3.6 Correlações calculadas", 2)
    _add_docx_paragraph(
        doc,
        "A tabela a seguir resume os testes de Spearman aplicados. O tamanho amostral é 214 para cada relação, "
        "porque 15 repositórios não possuem todas as métricas do CK completas no HTML disponível.",
    )
    corr_df = pd.DataFrame(
        [
            {
                "RQ": r.rq,
                "Variável X": r.x,
                "Variável Y": r.y,
                "N": r.n,
                "ρ": round(r.rho, 3),
                "p-valor": f"{r.pvalue:.3g}",
            }
            for r in correlations
        ]
    )
    _docx_table_from_dataframe(doc, corr_df)
    doc.add_paragraph()
    with io.BytesIO() as buffer:
        figures["correlation"].savefig(buffer, format="png", dpi=200, bbox_inches="tight")
        buffer.seek(0)
        doc.add_picture(buffer, width=Inches(6.7))

    _add_docx_heading(doc, "4. Discussão", 1)
    _add_docx_bullets(
        doc,
        [
            "A hipótese de que popularidade, sozinha, melhora a qualidade interna foi apenas parcialmente confirmada.",
            "A hipótese sobre maturidade não se confirmou como melhoria automática: projetos mais antigos tendem a ficar mais complexos.",
            "A atividade medida por releases apareceu associada a aumento de complexidade, e não necessariamente a refinamento.",
            "A hipótese sobre tamanho foi a mais bem suportada: sistemas maiores apresentaram piores indicadores de acoplamento e coesão.",
        ],
    )
    _add_docx_paragraph(
        doc,
        "Em síntese, os dados sugerem que a qualidade interna não cresce de forma linear com popularidade ou idade. "
        "O que aparece com mais força é a relação entre crescimento/expansão do repositório e aumento da complexidade estrutural.",
    )

    _add_docx_heading(doc, "5. Conclusão", 1)
    _add_docx_paragraph(
        doc,
        "O relatório final mostra que o `report.html` atual contém dados coerentes com a atividade, mas ainda não "
        "entrega sozinho o documento final exigido. A versão consolidada aqui adiciona hipóteses, metodologia, "
        "resultados, discussão e testes estatísticos, atendendo ao formato pedido no laboratório.",
        bold=True,
    )
    _add_docx_paragraph(
        doc,
        "Os arquivos finais foram gerados em `Lab02/reports/relatorio_final.docx` e `Lab02/reports/relatorio_final.pdf`.",
        italic=True,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)



def _wrap_paragraphs(text: str, width: int = 96) -> list[str]:
    paragraphs: list[str] = []
    for raw in text.split("\n"):
        if not raw.strip():
            paragraphs.append("")
            continue
        paragraphs.extend(textwrap.wrap(raw, width=width, replace_whitespace=False, drop_whitespace=False))
    return paragraphs



def _pdf_text_page(pdf: PdfPages, title: str, paragraphs: Iterable[str], *, footer: str | None = None):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")

    fig.text(0.08, 0.95, title, fontsize=16, fontweight="bold", ha="left", va="top")
    y = 0.90
    for paragraph in paragraphs:
        if not paragraph:
            y -= 0.02
            continue
        for line in _wrap_paragraphs(paragraph):
            fig.text(0.08, y, line, fontsize=10.5, ha="left", va="top")
            y -= 0.0205
        y -= 0.010
        if y < 0.12:
            break

    if footer:
        fig.text(0.08, 0.05, footer, fontsize=9, style="italic", ha="left", va="bottom")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)



def _pdf_table_page(pdf: PdfPages, title: str, df_table: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    ax.axis("off")
    fig.text(0.08, 0.95, title, fontsize=16, fontweight="bold", ha="left", va="top")
    table = ax.table(
        cellText=df_table.values.tolist(),
        colLabels=df_table.columns.tolist(),
        loc="center",
        cellLoc="center",
        bbox=[0.06, 0.18, 0.88, 0.66],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8.5)
    table.scale(1, 1.3)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#d9e8f5")
            cell.set_text_props(weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#f7f7f7")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)



def build_pdf(
    df: pd.DataFrame,
    summary: pd.DataFrame,
    correlations: list[PairResult],
    figures: dict[str, plt.Figure],
    output_path: Path,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    corr_df = pd.DataFrame(
        [
            {
                "RQ": r.rq,
                "X": r.x,
                "Y": r.y,
                "N": r.n,
                "ρ": f"{r.rho:.3f}",
                "p-valor": f"{r.pvalue:.3g}",
            }
            for r in correlations
        ]
    )
    summary_pdf = summary.reset_index().rename(columns={"index": "Medida"}).round(2)
    summary_pdf.columns = ["Medida"] + list(summary_pdf.columns[1:])

    with PdfPages(output_path) as pdf:
        _pdf_text_page(
            pdf,
            "Relatório Final — Qualidade interna de repositórios Java populares",
            [
                "Este documento consolida a análise do Lab02 a partir do `report.html` já gerado pela pipeline.",
                f"A amostra contém {len(df)} repositórios, dos quais {df[['CBO','DIT','LCOM']].dropna().shape[0]} possuem métricas CK completas.",
                "O objetivo foi investigar a relação entre popularidade, maturidade, atividade e tamanho dos repositórios com as métricas de qualidade CBO, DIT e LCOM.",
                "Hipóteses iniciais: maior popularidade e maior maturidade favoreceriam a qualidade; maior atividade poderia indicar evolução contínua; e maior tamanho poderia elevar a complexidade interna.",
            ],
            footer="Laboratório 02 — GitHub + CK + análise estatística",
        )
        _pdf_text_page(
            pdf,
            "2. Metodologia",
            [
                "A pipeline original coleta os repositórios Java mais populares via API GraphQL do GitHub, clona os projetos, executa a ferramenta CK e sumariza os CSVs gerados por repositório.",
                "Para o relatório final, utilizou-se o HTML como fonte de dados, aplicando estatística descritiva (média, mediana e desvio padrão) e testes de correlação de Spearman.",
                "A amostra disponível mostra assimetria forte em LOC, comentários e LCOM; por isso, a mediana é uma medida central importante para interpretação dos resultados.",
            ],
        )
        _pdf_table_page(pdf, "3. Visão geral da amostra", summary_pdf)

        pdf.savefig(figures["popularidade"], bbox_inches="tight")
        plt.close(figures["popularidade"])
        pdf.savefig(figures["maturidade"], bbox_inches="tight")
        plt.close(figures["maturidade"])
        pdf.savefig(figures["atividade"], bbox_inches="tight")
        plt.close(figures["atividade"])
        pdf.savefig(figures["tamanho"], bbox_inches="tight")
        plt.close(figures["tamanho"])

        _pdf_text_page(
            pdf,
            "4. Discussão e correlações",
            [
                "Popularidade apresentou correlação negativa fraca com CBO e DIT, mas não com LCOM. Isso indica que a popularidade, isoladamente, não garante melhoria consistente da qualidade interna.",
                "Maturidade não reduziu CBO, mas cresceu junto com DIT e LCOM, sugerindo que o tempo de vida pode aumentar a complexidade estrutural.",
                "Atividade, medida por releases, apareceu positivamente correlacionada com CBO, DIT e LCOM.",
                "Tamanho foi a relação mais consistente: LOC e comentários apresentaram correlação positiva com as três métricas de qualidade.",
            ],
        )
        _pdf_table_page(pdf, "5. Teste de Spearman", corr_df)
        _pdf_text_page(
            pdf,
            "6. Conclusão",
            [
                "O `report.html` atual é um bom insumo de dados, mas não atende sozinho ao formato de relatório final exigido pela atividade.",
                "O documento consolidado aqui adiciona introdução, metodologia, resultados, discussão e teste estatístico, além de transformar os dados em uma narrativa acadêmica coerente.",
                "Os artefatos finais foram gerados em DOCX e PDF na pasta `Lab02/reports/`.",
            ],
            footer="Fim do relatório",
        )



def build_figures(df: pd.DataFrame, summary: pd.DataFrame, correlations: list[PairResult]) -> dict[str, plt.Figure]:
    figures = {
        "summary": create_summary_table_figure(summary, df),
        "popularidade": create_rq_figure(df, "popularidade"),
        "maturidade": create_rq_figure(df, "maturidade"),
        "atividade": create_rq_figure(df, "atividade"),
        "tamanho": create_size_figure(df),
        "correlation": create_correlation_table_figure(correlations),
    }
    return figures



def main():
    parser = argparse.ArgumentParser(description="Gera o relatório final do Lab02 em DOCX e PDF.")
    parser.add_argument("--input", type=Path, default=SOURCE_HTML, help="Caminho do `report.html` de entrada")
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX, help="Caminho de saída do DOCX")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="Caminho de saída do PDF")
    args = parser.parse_args()

    df = load_dataframe(args.input)
    summary = summarize_metrics(df)
    correlations = compute_correlations(df)
    figures = build_figures(df, summary, correlations)

    build_docx(df, summary, correlations, figures.copy(), args.docx)
    build_pdf(df, summary, correlations, figures.copy(), args.pdf)

    for fig in figures.values():
        plt.close(fig)

    print(f"DOCX gerado em: {args.docx}")
    print(f"PDF gerado em: {args.pdf}")


if __name__ == "__main__":
    main()


