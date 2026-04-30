# -*- coding: utf-8 -*-
"""
generate_report.py
Gera o relatorio final do Lab03 em PDF usando fpdf2.
"""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

GRAPHS_DIR = os.path.abspath("../graphs")
DOCS_DIR = os.path.abspath("../docs")
OUTPUT_PDF = os.path.join(DOCS_DIR, "Relatorio-LAB03.pdf")

# ── Dados de medianas ──────────────────────────────────────────────────────────
MEDIANS = {
    "MERGED": {
        "Arquivos Alterados":       2.0,
        "Linhas Alteradas":        29.0,
        "Tempo de Analise (h)":    29.64,
        "Tamanho da Descricao":   542.0,
        "Participantes":            2.0,
        "Comentarios":              1.0,
        "Nr de Revisoes":           1.0,
    },
    "CLOSED": {
        "Arquivos Alterados":       1.0,
        "Linhas Alteradas":        18.0,
        "Tempo de Analise (h)":   356.46,
        "Tamanho da Descricao":   235.0,
        "Participantes":            3.0,
        "Comentarios":              1.0,
        "Nr de Revisoes":           1.0,
    },
}

# ── Resultados Spearman ─────────────────────────────────────────────────────────
RQ_RESULTS = [
    ("RQ01",  "Tamanho (arquivos) x Status do PR",   +0.0734, 0.0,     True),
    ("RQ01b", "Tamanho (linhas) x Status do PR",      +0.0391, 0.0,     True),
    ("RQ02",  "Tempo de Analise x Status do PR",      -0.2170, 0.0,     True),
    ("RQ03",  "Descricao x Status do PR",             +0.1165, 0.0,     True),
    ("RQ04",  "Participantes x Status do PR",         -0.1089, 0.0,     True),
    ("RQ04b", "Comentarios x Status do PR",           -0.0313, 0.0,     True),
    ("RQ05",  "Tamanho (arquivos) x Nr Revisoes",    +0.2467, 0.0,     True),
    ("RQ05b", "Tamanho (linhas) x Nr Revisoes",      +0.2942, 0.0,     True),
    ("RQ06",  "Tempo de Analise x Nr Revisoes",      +0.1346, 0.0,     True),
    ("RQ07",  "Descricao x Nr Revisoes",             +0.1940, 0.0,     True),
    ("RQ08",  "Participantes x Nr Revisoes",         +0.3454, 0.0,     True),
    ("RQ08b", "Comentarios x Nr Revisoes",           +0.3101, 0.0,     True),
]


class ReportPDF(FPDF):
    TITLE_COLOR  = (33, 37, 41)
    ACCENT_COLOR = (33, 150, 243)
    MERGED_COLOR = (33, 150, 243)
    CLOSED_COLOR = (244, 67, 54)

    def header(self):
        self.set_fill_color(*self.ACCENT_COLOR)
        self.rect(0, 0, 210, 14, "F")
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 3)
        self.cell(0, 8, "LAB03 - Caracterizando a Atividade de Code Review no GitHub", align="L")
        self.set_text_color(*self.TITLE_COLOR)
        self.ln(14)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f"Pagina {self.page_no()}", align="C")

    # ── helpers ──────────────────────────────────────────────────────────────

    def chapter_title(self, text):
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*self.ACCENT_COLOR)
        self.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*self.ACCENT_COLOR)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), 210 - self.r_margin, self.get_y())
        self.ln(3)
        self.set_text_color(*self.TITLE_COLOR)

    def section_title(self, text):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*self.TITLE_COLOR)

    def body(self, text, indent=0):
        self.set_font("Helvetica", "", 10)
        orig_margin = self.l_margin
        if indent:
            self.set_left_margin(orig_margin + indent)
            self.set_x(orig_margin + indent)
        self.multi_cell(0, 5.5, text)
        if indent:
            self.set_left_margin(orig_margin)
            self.set_x(orig_margin)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_x(self.l_margin + 4)
        self.multi_cell(0, 5.5, "- " + text)

    def add_image_centered(self, path, w=170):
        if not os.path.exists(path):
            self.body(f"[Imagem nao encontrada: {path}]")
            return
        x = (210 - w) / 2
        self.image(path, x=x, w=w)
        self.ln(3)

    def add_image_half(self, path_l, path_r, w=88):
        exists_l = os.path.exists(path_l)
        exists_r = os.path.exists(path_r)
        y = self.get_y()
        if exists_l:
            self.image(path_l, x=self.l_margin, y=y, w=w)
        if exists_r:
            self.image(path_r, x=self.l_margin + w + 4, y=y, w=w)
        h_approx = w * 5 / 7
        self.set_y(y + h_approx + 3)

    def kv(self, key, value, color=None):
        self.set_font("Helvetica", "B", 10)
        self.cell(70, 6, key + ":", new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_font("Helvetica", "", 10)
        if color:
            self.set_text_color(*color)
        self.cell(0, 6, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*self.TITLE_COLOR)


# ──────────────────────────────────────────────────────────────────────────────
# Conteudo
# ──────────────────────────────────────────────────────────────────────────────

def build_pdf():
    os.makedirs(DOCS_DIR, exist_ok=True)
    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=15, top=18, right=15)

    # ── CAPA ────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(18)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*ReportPDF.ACCENT_COLOR)
    pdf.multi_cell(0, 12, "Caracterizando a Atividade de\nCode Review no GitHub", align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "Laboratorio de Experimentacao de Software - LAB03", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Engenharia de Software  |  6 Periodo", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, "Prof. Joao Paulo Carneiro Aramuni", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)
    pdf.set_text_color(*ReportPDF.TITLE_COLOR)

    # Dataset overview box
    pdf.set_fill_color(240, 248, 255)
    pdf.set_draw_color(*ReportPDF.ACCENT_COLOR)
    pdf.set_line_width(0.3)
    pdf.rect(pdf.l_margin, pdf.get_y(), 180, 40, "DF")
    pdf.set_xy(pdf.l_margin + 5, pdf.get_y() + 5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Resumo do Dataset", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(pdf.l_margin + 5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "  Total de PRs analisados:  28.187", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(pdf.l_margin + 5)
    pdf.cell(0, 6, "  Repositorios:  200 mais populares do GitHub (>=100 PRs merged/closed)",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(pdf.l_margin + 5)
    pdf.cell(0, 6, "  Filtros:  status MERGED ou CLOSED  |  >=1 revisao  |  analise >1 hora",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(18)

    # Distribuicao de status
    pdf.add_image_centered(os.path.join(GRAPHS_DIR, "status_distribution.png"), w=90)

    # ── 1. INTRODUCAO ───────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("1. Introducao")
    pdf.body(
        "A pratica de code review consolidou-se como etapa fundamental nos processos ageis de "
        "desenvolvimento de software. No GitHub, as revisoes ocorrem por meio de Pull Requests (PRs): "
        "um desenvolvedor submete alteracoes que sao inspecionadas por revisores antes de serem "
        "integradas a branch principal. Ao final, o PR pode ser aceito (MERGED) ou rejeitado (CLOSED)."
    )
    pdf.ln(2)
    pdf.body(
        "Este laboratorio analisa os PRs submetidos aos 200 repositorios mais populares do GitHub, "
        "buscando identificar quais variaveis influenciam (i) o resultado final da revisao (MERGED vs. "
        "CLOSED) e (ii) o numero de revisoes realizadas."
    )

    pdf.section_title("1.1 Hipoteses Iniciais")
    hypotheses = [
        ("H1 - Tamanho",      "PRs maiores (mais arquivos/linhas) tendem a ser rejeitados com mais frequencia, pois sao mais dificeis de revisar."),
        ("H2 - Tempo",        "PRs com tempo de analise mais longo tendem a ser rejeitados; longa duracao indica dificuldade de consenso."),
        ("H3 - Descricao",    "PRs com descricoes mais longas tendem a ser aprovados, pois revelam mais contexto ao revisor."),
        ("H4 - Interacoes",   "PRs com mais participantes/comentarios tem maior chance de serem rejeitados (mais conflito)."),
        ("H5-H8 - Revisoes",  "PRs maiores, com mais interacoes e descricoes detalhadas tendem a receber mais revisoes."),
    ]
    for title, text in hypotheses:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, title + ":", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(0, 6, text)
        pdf.ln(1)

    pdf.section_title("1.2 Questoes de Pesquisa")
    rqs = [
        "RQ01 - Relacao entre tamanho dos PRs e o status final (MERGED/CLOSED)?",
        "RQ02 - Relacao entre tempo de analise e o status final?",
        "RQ03 - Relacao entre tamanho da descricao e o status final?",
        "RQ04 - Relacao entre interacoes nos PRs e o status final?",
        "RQ05 - Relacao entre tamanho dos PRs e o numero de revisoes?",
        "RQ06 - Relacao entre tempo de analise e o numero de revisoes?",
        "RQ07 - Relacao entre tamanho da descricao e o numero de revisoes?",
        "RQ08 - Relacao entre interacoes nos PRs e o numero de revisoes?",
    ]
    for rq in rqs:
        pdf.bullet(rq)

    # ── 2. METODOLOGIA ──────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("2. Metodologia")

    pdf.section_title("2.1 Criacao do Dataset")
    steps = [
        "Selecao dos 200 repositorios mais populares (por estrelas) via GitHub GraphQL API.",
        "Filtro: repositorios com pelo menos 100 PRs (MERGED + CLOSED).",
        "Coleta de PRs com status MERGED ou CLOSED e pelo menos 1 revisao.",
        "Remocao de PRs automaticos: intervalo entre criacao e fechamento < 1 hora.",
        "Extracao das metricas: arquivos alterados, linhas add/removidas, tempo de analise, "
        "tamanho da descricao, participantes, comentarios e numero de revisoes.",
    ]
    for s in steps:
        pdf.bullet(s)

    pdf.ln(2)
    pdf.section_title("2.2 Metricas Coletadas")
    metrics_table = [
        ("changed_files",       "Tamanho",      "Numero de arquivos alterados"),
        ("total_lines_changed", "Tamanho",      "Total de linhas adicionadas + removidas"),
        ("analysis_time_hours", "Tempo",        "Horas entre criacao e fechamento/merge"),
        ("description_length",  "Descricao",    "Caracteres no corpo do PR (markdown)"),
        ("participants",        "Interacoes",   "Numero de participantes unicos"),
        ("comments",            "Interacoes",   "Numero de comentarios"),
        ("review_count",        "Target (B)",   "Numero de revisoes realizadas"),
    ]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*ReportPDF.ACCENT_COLOR)
    pdf.set_text_color(255, 255, 255)
    col_w = [55, 35, 90]
    for h, w in zip(["Campo", "Dimensao", "Descricao"], col_w):
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*ReportPDF.TITLE_COLOR)
    fill = False
    for row in metrics_table:
        pdf.set_fill_color(235, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)
        for val, w in zip(row, col_w):
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(w, 6, val, border=1, fill=True)
        pdf.ln()
        fill = not fill

    pdf.ln(4)
    pdf.section_title("2.3 Teste Estatistico - Correlacao de Spearman")
    pdf.body(
        "Optou-se pelo coeficiente de correlacao de Spearman (rho) por se tratar de um teste nao "
        "parametrico, adequado a dados que nao seguem distribuicao normal - como e comum em "
        "metricas de software (distribuicoes altamente assimetricas com caudas longas). "
        "O teste avalia a relacao monotonica entre variaveis ordinais/continuas sem pressupor "
        "linearidade. Adotou-se p < 0,05 como limiar de significancia estatistica."
    )

    # ── 3. RESULTADOS ───────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("3. Resultados")

    pdf.section_title("3.1 Visao Geral das Medianas")
    pdf.add_image_centered(os.path.join(GRAPHS_DIR, "medians_comparison.png"), w=175)

    # Tabela de medianas
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*ReportPDF.ACCENT_COLOR)
    pdf.set_text_color(255, 255, 255)
    col_w2 = [75, 45, 45]
    for h, w in zip(["Metrica", "MERGED (mediana)", "CLOSED (mediana)"], col_w2):
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*ReportPDF.TITLE_COLOR)
    fill = False
    for metric in MEDIANS["MERGED"]:
        pdf.set_fill_color(235, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_w2[0], 6, metric, border=1, fill=True)
        pdf.set_text_color(*ReportPDF.MERGED_COLOR)
        pdf.cell(col_w2[1], 6, str(MEDIANS["MERGED"][metric]), border=1, fill=True, align="C")
        pdf.set_text_color(*ReportPDF.CLOSED_COLOR)
        pdf.cell(col_w2[2], 6, str(MEDIANS["CLOSED"][metric]), border=1, fill=True, align="C")
        pdf.set_text_color(*ReportPDF.TITLE_COLOR)
        pdf.ln()
        fill = not fill

    # Resumo Spearman
    pdf.ln(5)
    pdf.section_title("3.2 Resumo dos Coeficientes de Spearman")
    pdf.add_image_centered(os.path.join(GRAPHS_DIR, "spearman_summary.png"), w=175)

    # Tabela detalhada
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*ReportPDF.ACCENT_COLOR)
    pdf.set_text_color(255, 255, 255)
    col_w3 = [18, 80, 25, 27, 35]
    for h, w in zip(["RQ", "Relacao", "rho", "p-valor", "Sig. (p<0.05)"], col_w3):
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*ReportPDF.TITLE_COLOR)
    fill = False
    for rq_id, rel, rho, pval, sig in RQ_RESULTS:
        bg = (235, 245, 255) if fill else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_w3[0], 6, rq_id, border=1, fill=True, align="C")
        pdf.cell(col_w3[1], 6, rel,   border=1, fill=True)
        rho_color = ReportPDF.MERGED_COLOR if rho > 0 else ReportPDF.CLOSED_COLOR
        pdf.set_text_color(*rho_color)
        pdf.cell(col_w3[2], 6, f"{rho:+.4f}", border=1, fill=True, align="C")
        pdf.set_text_color(*ReportPDF.TITLE_COLOR)
        pdf.cell(col_w3[3], 6, f"{pval:.2e}", border=1, fill=True, align="C")
        sig_color = (0, 150, 0) if sig else (200, 0, 0)
        pdf.set_text_color(*sig_color)
        pdf.cell(col_w3[4], 6, "SIM" if sig else "NAO", border=1, fill=True, align="C")
        pdf.set_text_color(*ReportPDF.TITLE_COLOR)
        pdf.ln()
        fill = not fill

    # ── 4. ANALISE POR RQ ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("4. Analise por Questao de Pesquisa")

    pdf.section_title("RQ01 - Tamanho dos PRs x Status (MERGED/CLOSED)")
    pdf.add_image_half(
        os.path.join(GRAPHS_DIR, "RQ01_boxplot.png"),
        os.path.join(GRAPHS_DIR, "RQ01b_boxplot.png"),
    )
    pdf.body(
        "PRs MERGED apresentam ligeiramente mais arquivos alterados (mediana 2 vs 1) e mais linhas "
        "(mediana 29 vs 18). O coeficiente rho = +0,073 e rho = +0,039, ambos significativos (p~0), "
        "indicam correlacao positiva fraca: PRs ligeiramente maiores tendem a ser aceitos, contrariando "
        "parcialmente a hipotese H1. O efeito e pequeno, sugerindo que o tamanho isolado nao e fator "
        "decisivo para rejeicao."
    )

    pdf.section_title("RQ02 - Tempo de Analise x Status")
    pdf.add_image_centered(os.path.join(GRAPHS_DIR, "RQ02_boxplot.png"), w=120)
    pdf.body(
        "PRs CLOSED levam muito mais tempo ate o fechamento (mediana ~356 h) em comparacao a PRs "
        "MERGED (mediana ~30 h). O coeficiente rho = -0,217 confirma correlacao negativa moderada: "
        "quanto maior o tempo de analise, maior a probabilidade de rejeicao. Isso corrobora a hipotese H2: "
        "PRs que demoram muito tendem a ser abandonados ou rejeitados."
    )

    pdf.add_page()
    pdf.section_title("RQ03 - Descricao dos PRs x Status")
    pdf.add_image_centered(os.path.join(GRAPHS_DIR, "RQ03_boxplot.png"), w=120)
    pdf.body(
        "PRs MERGED possuem descricoes significativamente mais longas (mediana 542 chars vs 235 chars). "
        "rho = +0,117 (p~0) indica correlacao positiva fraca a moderada, confirmando H3: descricoes mais "
        "ricas facilitam a aprovacao do PR ao fornecer contexto ao revisor."
    )

    pdf.section_title("RQ04 - Interacoes (Participantes e Comentarios) x Status")
    pdf.add_image_half(
        os.path.join(GRAPHS_DIR, "RQ04_boxplot.png"),
        os.path.join(GRAPHS_DIR, "RQ04b_boxplot.png"),
    )
    pdf.body(
        "PRs CLOSED tem mais participantes (mediana 3 vs 2) e mesmo numero de comentarios (mediana 1). "
        "rho(participantes) = -0,109 e rho(comentarios) = -0,031, ambos significativos. Mais participantes "
        "envolvidos esta associado a maior probabilidade de rejeicao, possivelmente indicando mais "
        "conflitos. O efeito dos comentarios e muito fraco."
    )

    pdf.add_page()
    pdf.section_title("RQ05 - Tamanho dos PRs x Nr de Revisoes")
    pdf.add_image_half(
        os.path.join(GRAPHS_DIR, "RQ05_scatter.png"),
        os.path.join(GRAPHS_DIR, "RQ05b_scatter.png"),
    )
    pdf.body(
        "PRs com mais arquivos (rho = +0,247) e mais linhas (rho = +0,294) tendem a receber mais revisoes. "
        "Correlacao positiva fraca a moderada, estatisticamente significativa: PRs maiores exigem mais "
        "ciclos de revisao, alinhando-se a hipotese H5."
    )

    pdf.section_title("RQ06 - Tempo de Analise x Nr de Revisoes")
    pdf.add_image_centered(os.path.join(GRAPHS_DIR, "RQ06_scatter.png"), w=120)
    pdf.body(
        "rho = +0,135 (p~0): PRs com analise mais longa recebem ligeiramente mais revisoes. "
        "A correlacao e fraca mas significativa, sugerindo que o tempo reflete iteracoes adicionais "
        "de ajuste no codigo."
    )

    pdf.add_page()
    pdf.section_title("RQ07 - Descricao dos PRs x Nr de Revisoes")
    pdf.add_image_centered(os.path.join(GRAPHS_DIR, "RQ07_scatter.png"), w=120)
    pdf.body(
        "rho = +0,194: descricoes mais longas correlacionam-se positivamente com mais revisoes. "
        "PRs melhor documentados parecem atrair mais atencao dos revisores, gerando mais ciclos "
        "de analise."
    )

    pdf.section_title("RQ08 - Interacoes x Nr de Revisoes")
    pdf.add_image_half(
        os.path.join(GRAPHS_DIR, "RQ08_scatter.png"),
        os.path.join(GRAPHS_DIR, "RQ08b_scatter.png"),
    )
    pdf.body(
        "Participantes (rho = +0,345) e comentarios (rho = +0,310) apresentam as correlacoes mais fortes "
        "do estudo. Mais interacoes humanas estao fortemente associadas a mais revisoes: cada revisao pode "
        "gerar novos comentarios e atrair novos participantes."
    )

    # ── 5. DISCUSSAO ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("5. Discussao")

    pdf.section_title("5.1 Confrontando Hipoteses com Resultados")
    discussions = [
        ("H1 - Tamanho x Status",
         "Parcialmente refutada. Esperava-se que PRs maiores fossem rejeitados com mais frequencia, "
         "mas os resultados mostram correlacao positiva fraca (mais arquivos/linhas -> maior chance de "
         "aprovacao). Isso pode indicar que contribuicoes substanciais sao mais valorizadas."),
        ("H2 - Tempo x Status",
         "Confirmada. PRs com maior tempo de analise tendem a ser rejeitados (rho = -0,217). "
         "PRs CLOSED levam em media 12x mais tempo que PRs MERGED, sugerindo que a falta de progresso "
         "ou dificuldade de consenso leva ao fechamento."),
        ("H3 - Descricao x Status",
         "Confirmada. Descricoes mais longas estao associadas a maiores chances de aprovacao. "
         "Uma boa documentacao do PR reduz a friccao do processo de revisao."),
        ("H4 - Interacoes x Status",
         "Parcialmente confirmada. Mais participantes -> maior chance de rejeicao, mas comentarios "
         "apresentam efeito muito fraco. Possivelmente mais participantes indicam controversia."),
        ("H5-H8 - Revisoes",
         "Todas confirmadas. As correlacoes sao positivas e significativas. O maior efeito e das "
         "interacoes (participantes e comentarios), seguido pelo tamanho."),
    ]
    for title, text in discussions:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.body(text, indent=4)
        pdf.ln(1)

    pdf.section_title("5.2 Insights")
    insights = [
        "O tempo de analise e o fator mais fortemente associado a rejeicao (rho = -0,217).",
        "Interacoes (participantes, comentarios) sao os fatores mais correlacionados ao numero de revisoes.",
        "Todos os coeficientes sao estatisticamente significativos (p~0), mas de magnitude fraca a moderada.",
        "O processo de revisao e multidimensional; variaveis qualitativas nao capturadas podem ter impacto maior.",
    ]
    for ins in insights:
        pdf.bullet(ins)

    # ── 6. CONCLUSAO ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("6. Conclusao")
    pdf.body(
        "Este laboratorio analisou 28.187 Pull Requests dos 200 repositorios mais populares do GitHub, "
        "investigando como tamanho, tempo, descricao e interacoes se relacionam com o status final do PR "
        "e com o numero de revisoes realizadas."
    )
    pdf.ln(2)
    pdf.body(
        "Os resultados indicam que: (i) o tempo de analise e o indicador mais forte de rejeicao; "
        "(ii) descricoes mais completas favorecem a aprovacao; (iii) interacoes humanas sao os melhores "
        "preditores do numero de revisoes; e (iv) o tamanho do PR tem efeito pequeno sobre o resultado final."
    )
    pdf.ln(2)
    pdf.body(
        "Como sugestao para trabalhos futuros: (a) incorporar variaveis qualitativas como historico do "
        "autor e sentimento dos comentarios; (b) comparar resultados entre diferentes linguagens de "
        "programacao; (c) aplicar modelos de machine learning para predicao do resultado de PRs."
    )

    pdf.ln(4)
    pdf.section_title("Confronto com Literatura")
    pdf.body(
        "Os resultados sao consistentes com Gousios et al. (2014) [An Exploratory Study of the Pull-Based "
        "Software Development Model], que identificaram que a probabilidade de merge esta associada ao "
        "historico do contribuidor e ao tamanho do PR. Kalliamvakou et al. (2014) tambem destacaram que "
        "PRs com mais discussao tendem a levar mais tempo e tem menor taxa de aprovacao, corroborando "
        "nosso achado de correlacao negativa entre participantes e status (rho = -0,109)."
    )

    # ── OUTPUT ──────────────────────────────────────────────────────────────
    pdf.output(OUTPUT_PDF)
    print(f"[OK] Relatorio gerado em: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()

