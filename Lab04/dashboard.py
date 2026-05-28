#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard.py - Lab04
Dashboard interativo (Streamlit + Plotly) para análise de Conventional Commits em PRs Java.

Uso:
    cd d:\\lab-experimetacao-sofware\\Lab04
    streamlit run dashboard.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

# ──────────────────────────────────────────────────────────────────────────────
# Configuração da página
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Lab04 – Conventional Commits & PRs",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATASET_PATH = Path(__file__).parent / "docs" / "prs_dataset.csv"

# Paleta
COR_CC     = "#2563EB"   # azul  – CC
COR_NAO_CC = "#F59E0B"   # âmbar – Não-CC
COR_MERGED = "#10B981"   # verde
COR_CLOSED = "#EF4444"   # vermelho

# ──────────────────────────────────────────────────────────────────────────────
# Carregamento e pré-processamento
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Carregando dataset…")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH, on_bad_lines="skip")
    df["is_cc"]     = df["title_is_conventional"].str.strip().str.lower() == "sim"
    df["merged"]    = df["is_merged"].str.strip().str.lower() == "sim"
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df["merged_at"]  = pd.to_datetime(df["merged_at"],  utc=True, errors="coerce")
    df["created_month"] = df["created_at"].dt.to_period("M").astype(str)
    return df


if not DATASET_PATH.exists():
    st.error(f"Dataset não encontrado: `{DATASET_PATH}`\nExecute `python src/main.py` primeiro.")
    st.stop()

df = load_data()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar – filtros
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Filtros")

repos_disponiveis = sorted(df["repository"].unique())
repos_sel = st.sidebar.multiselect(
    "Repositórios",
    options=repos_disponiveis,
    default=[],
    placeholder="Todos os repositórios",
)

tipos_cc = sorted(df.loc[df["is_cc"], "conventional_type"].dropna().unique())
tipos_sel = st.sidebar.multiselect(
    "Tipo CC",
    options=tipos_cc,
    default=[],
    placeholder="Todos os tipos",
)

# Aplica filtros
mask = pd.Series(True, index=df.index)
if repos_sel:
    mask &= df["repository"].isin(repos_sel)
if tipos_sel:
    mask &= df["conventional_type"].isin(tipos_sel)

dff = df[mask].copy()
dff_tempo = dff.copy()

# ──────────────────────────────────────────────────────────────────────────────
# Cabeçalho
# ──────────────────────────────────────────────────────────────────────────────
st.title("Conventional Commits & Pull Requests Java")
st.caption(
    f"Dataset: **{len(dff):,} PRs** | **{dff['repository'].nunique()} repositórios** | "
    f"Fonte: GitHub API"
)
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Introdução
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("Sobre este estudo — Conventional Commits, Perguntas de Pesquisa e Metodologia", expanded=True):

    st.markdown("""
    ## O que são Conventional Commits?

    [Conventional Commits](https://www.conventionalcommits.org/) é uma convenção leve para mensagens de commit
    que define um conjunto de regras para criar um histórico de commits **explícito e legível**.
    A estrutura básica de uma mensagem é:

    ```
    <tipo>[escopo opcional]: <descrição>

    [corpo opcional]

    [rodapé(s) opcional(is)]
    ```

    Os **tipos** mais comuns são `feat` (nova funcionalidade), `fix` (correção de bug), `docs`, `refactor`,
    `test`, `chore`, `ci` e `perf`.

    A adoção da convenção traz benefícios diretos ao fluxo de desenvolvimento: geração automática de
    *changelogs*, versionamento semântico automatizado (SemVer) e maior rastreabilidade entre issues,
    commits e PRs.

    ---

    ## Perguntas de Pesquisa (RQs)

    Este estudo investiga o impacto do uso de Conventional Commits em **Pull Requests de projetos Java**
    hospedados no GitHub, respondendo quatro perguntas de pesquisa:

    | # | Pergunta | Hipótese |
    |---|----------|----------|
    | **RQ1** | Qual a frequência de adoção de Conventional Commits em PRs de projetos Java populares? | Projetos mais ativos tendem a padronizar as mensagens ao longo do tempo. |
    | **RQ2** | PRs com título no formato CC têm maior taxa de merge do que PRs sem CC? | A clareza do título pode facilitar a revisão e aprovação. |
    | **RQ3** | PRs com CC são fechados (merged ou closed) mais rapidamente do que PRs sem CC? | Títulos padronizados reduzem o ciclo de revisão. |
    | **RQ4** | Quais tipos de CC estão associados a maior número de revisões e commits por PR? | Tipos como `feat` e `fix` tendem a demandar mais iterações. |

    ---

    ## Metodologia

    ### Coleta de dados
    - **Fonte:** via GitHub GraphQL API.    - **Período:** PRs criados até fevereiro de 2026.    - **Critério de seleção:** repositórios Java com ≥ 1 000 estrelas, excluindo forks e arquivados.
    - **Variáveis coletadas:** título, estado (merged/closed), datas de criação e fechamento,
      número de commits, contagem de revisões.

    ### Classificação de Conventional Commits
    O título de cada PR foi verificado contra a regex oficial da especificação CC
    (`^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\\(.+\\))?!?: .+`).
    PRs que satisfazem a regex são marcados como **Convencional (CC)**; os demais como **Não Convencional**.

    ### Análise estatística
    - **Com que frequência Conventional Commits são adotados em PRs de projetos Java populares?**
    - **PRs com Conventional Commits têm maior taxa de merge do que PRs sem CC?**
    - **PRs com Conventional Commits são fechados mais rapidamente do que PRs sem CC?**
    - **Quais tipos de Conventional Commits estão associados a maior número de revisões e commits por PR?**

    ### Ferramentas
    `Python 3.11` · `pandas` · `scipy` · `plotly` · `streamlit`
    """)

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# KPIs
# ──────────────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

total       = len(dff)
n_cc        = dff["is_cc"].sum()
n_merged    = dff["merged"].sum()
taxa_merge  = n_merged / total if total else 0
taxa_cc     = n_cc / total if total else 0

k1.metric("Total PRs",           f"{total:,}")
k2.metric("PRs Convencionais",   f"{n_cc:,}", f"{taxa_cc:.1%}")
k3.metric("PRs Merged",          f"{n_merged:,}", f"{taxa_merge:.1%}")
k4.metric("Repositórios",        dff["repository"].nunique())
k5.metric("PRs Breaking Change", int((dff["is_breaking"].str.lower() == "sim").sum()))

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ1 – Frequência de Conventional Commits
# ──────────────────────────────────────────────────────────────────────────────
st.header("RQ1 – Com que frequência Conventional Commits são adotados em PRs de projetos Java populares?")
rq1_col1, rq1_col2 = st.columns(2)

with rq1_col1:
    # Pizza CC vs Não-CC
    pizza_data = pd.DataFrame({
        "Tipo":  ["Convencional", "Não Convencional"],
        "Count": [n_cc, total - n_cc],
    })
    fig_pizza = px.pie(
        pizza_data, names="Tipo", values="Count",
        color="Tipo",
        color_discrete_map={"Convencional": COR_CC, "Não Convencional": COR_NAO_CC},
        title="Distribuição CC vs Não-CC",
        hole=0.45,
    )
    fig_pizza.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_pizza, use_container_width=True)

with rq1_col2:
    # Barras por tipo convencional
    tipo_counts = (
        dff.loc[dff["is_cc"], "conventional_type"]
        .value_counts()
        .reset_index()
    )
    tipo_counts.columns = ["Tipo", "Count"]
    fig_tipo = px.bar(
        tipo_counts, x="Count", y="Tipo", orientation="h",
        color="Count", color_continuous_scale="Blues",
        title="PRs Convencionais por Tipo",
        labels={"Count": "Nº de PRs", "Tipo": "Tipo"},
    )
    fig_tipo.update_layout(showlegend=False, coloraxis_showscale=False,
                            yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_tipo, use_container_width=True)

# Evolução temporal
cc_mensal = (
    dff.groupby(["created_month", "is_cc"])
    .size()
    .reset_index(name="Count")
)
cc_mensal["Categoria"] = cc_mensal["is_cc"].map({True: "Convencional", False: "Não Convencional"})
cc_mensal = cc_mensal.sort_values("created_month")

fig_temporal = px.line(
    cc_mensal, x="created_month", y="Count", color="Categoria",
    color_discrete_map={"Convencional": COR_CC, "Não Convencional": COR_NAO_CC},
    title="Evolução Temporal de PRs por Categoria",
    labels={"created_month": "Mês", "Count": "Nº de PRs"},
    markers=True,
)
fig_temporal.update_xaxes(tickangle=45)
st.plotly_chart(fig_temporal, use_container_width=True)

st.caption(
    "O gráfico de pizza mostra a proporção geral entre PRs com e sem Conventional Commits no dataset. "
    "As barras detalham quais tipos (feat, fix, chore…) são mais usados entre os PRs convencionais. "
    "A linha temporal revela se a adoção do padrão cresceu, diminuiu ou se manteve estável ao longo dos meses até fevereiro de 2026."
)
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ2 – Taxa de Merge
# ──────────────────────────────────────────────────────────────────────────────
st.header("RQ2 – PRs com Conventional Commits têm maior taxa de merge do que PRs sem CC?")
rq2_col1, rq2_col2 = st.columns(2)

cc_merge = dff.groupby("is_cc")["merged"].agg(["sum", "count"]).reset_index()
cc_merge.columns = ["is_cc", "Merged", "Total"]
cc_merge["Taxa"] = cc_merge["Merged"] / cc_merge["Total"]
cc_merge["Categoria"] = cc_merge["is_cc"].map({True: "Convencional", False: "Não Convencional"})

with rq2_col1:
    fig_merge = px.bar(
        cc_merge, x="Categoria", y="Taxa",
        color="Categoria",
        color_discrete_map={"Convencional": COR_CC, "Não Convencional": COR_NAO_CC},
        title="Taxa de Merge por Categoria",
        text=cc_merge["Taxa"].map("{:.1%}".format),
        labels={"Taxa": "Taxa de Merge"},
    )
    fig_merge.update_traces(textposition="outside")
    fig_merge.update_layout(showlegend=False, yaxis_tickformat=".0%", yaxis_range=[0, 1])
    st.plotly_chart(fig_merge, use_container_width=True)

with rq2_col2:
    # Stacked bar: merged/closed por tipo CC
    tipo_merge = (
        dff.loc[dff["is_cc"]]
        .groupby(["conventional_type", "merged"])
        .size()
        .reset_index(name="Count")
    )
    tipo_merge["Estado"] = tipo_merge["merged"].map({True: "Merged", False: "Closed"})
    fig_tipo_merge = px.bar(
        tipo_merge, x="conventional_type", y="Count", color="Estado",
        color_discrete_map={"Merged": COR_MERGED, "Closed": COR_CLOSED},
        title="Merge/Closed por Tipo Convencional",
        barmode="stack",
        labels={"conventional_type": "Tipo CC", "Count": "Nº de PRs"},
    )
    fig_tipo_merge.update_xaxes(tickangle=35)
    st.plotly_chart(fig_tipo_merge, use_container_width=True)

# Teste estatístico Qui-quadrado
tab_cont = pd.crosstab(dff["is_cc"], dff["merged"])
chi2, p_valor, dof, _ = stats.chi2_contingency(tab_cont)
diferenca_pp = (cc_merge.loc[cc_merge["is_cc"] == True, "Taxa"].values[0] -
                cc_merge.loc[cc_merge["is_cc"] == False, "Taxa"].values[0]) * 100

col_stat1, col_stat2, col_stat3 = st.columns(3)

st.caption(
    "As barras comparam a taxa de merge entre PRs convencionais e não convencionais. "
    "O gráfico empilhado detalha, dentro de cada tipo CC, a proporção de PRs aceitos (merged) e rejeitados (closed). "
    f"O teste Qui-quadrado (χ²\u2009=\u2009{chi2:.2f}, p\u2009=\u2009{p_valor:.4f}) indica se a diferença de {diferenca_pp:+.1f}\u202fp.p. na taxa de merge é estatisticamente significativa."
)
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ3 – Tempo até o Merge
# ──────────────────────────────────────────────────────────────────────────────
st.header("RQ3 – PRs com Conventional Commits são fechados mais rapidamente do que PRs sem CC?")

cc_tempo  = dff_tempo.loc[dff_tempo["is_cc"],   "time_to_close_hours"].dropna()
ncc_tempo = dff_tempo.loc[~dff_tempo["is_cc"],  "time_to_close_hours"].dropna()

# Escala logarítmica: exibe toda a distribuição sem clipar outliers
fig_box = go.Figure()
fig_box.add_trace(go.Box(
    y=cc_tempo,
    name="Com CC",
    marker_color=COR_CC,
    boxmean=True,
    whiskerwidth=0.5,
))
fig_box.add_trace(go.Box(
    y=ncc_tempo,
    name="Sem CC",
    marker_color=COR_NAO_CC,
    boxmean=True,
    whiskerwidth=0.5,
))
fig_box.update_layout(
    title="Tempo de Fechamento por Categoria de PR (escala logarítmica)",
    yaxis=dict(
        title="Horas até fechar o PR (log)",
        type="log",
        tickvals=[1, 6, 24, 168, 720, 4320, 8760],
        ticktext=["1 h", "6 h", "1 dia", "1 sem", "1 mês", "6 meses", "1 ano"],
    ),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_box, use_container_width=True)

# Métricas resumidas
t_stat, p_mann = stats.mannwhitneyu(cc_tempo, ncc_tempo, alternative="two-sided")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Mediana CC (h)",     f"{cc_tempo.median():.1f}")
m2.metric("Mediana Sem CC (h)", f"{ncc_tempo.median():.1f}")
m3.metric("Mann-Whitney U",     f"{t_stat:,.0f}")
m4.metric("p-valor",            f"{p_mann:.4f}",
          delta="significativo" if p_mann < 0.05 else "não significativo",
          delta_color="normal" if p_mann < 0.05 else "off")

st.caption(
    "O boxplot usa escala logarítmica no eixo Y, permitindo visualizar toda a distribuição — de PRs fechados em horas até os que levaram meses — sem cortar outliers. "
    "A linha central é a mediana, a caixa é o IQR (P25–P75), o ponto interno é a média. "
    f"Teste Mann-Whitney U (não-paramétrico): mediana CC = {cc_tempo.median():.1f} h vs Sem CC = {ncc_tempo.median():.1f} h "
    f"(p = {p_mann:.4f}{'  → diferença estatisticamente significativa.' if p_mann < 0.05 else '  → diferença não estatisticamente significativa.'})."
)
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ4 – Adoção por Repositório e Métricas de Qualidade
# ──────────────────────────────────────────────────────────────────────────────
st.header("RQ4 – Quais tipos de Conventional Commits estão associados a maior número de revisões e commits por PR?")

repo_stats = (
    dff.groupby("repository")
    .agg(
        total=("pr_number", "count"),
        cc=("is_cc", "sum"),
        merged=("merged", "sum"),
        avg_reviews=("review_count", "mean"),
        avg_commits=("commits_count", "mean"),
    )
    .reset_index()
)
repo_stats["pct_cc"]    = repo_stats["cc"]     / repo_stats["total"]
repo_stats["pct_merge"] = repo_stats["merged"] / repo_stats["total"]
repo_stats["repo_short"] = repo_stats["repository"].str.split("/").str[-1]

if True:
    top20 = repo_stats.nlargest(20, "pct_cc")
    fig_adocao = px.bar(
        top20, x="pct_cc", y="repo_short", orientation="h",
        color="pct_cc", color_continuous_scale="Blues",
        title="Top 20 Repos – % PRs com CC",
        labels={"pct_cc": "% CC", "repo_short": "Repositório"},
        text=top20["pct_cc"].map("{:.0%}".format),
    )
    fig_adocao.update_layout(coloraxis_showscale=False,
                              yaxis={"categoryorder": "total ascending"})
    fig_adocao.update_traces(textposition="outside")
    st.plotly_chart(fig_adocao, use_container_width=True)

# Comparação de métricas de qualidade CC vs Não-CC
st.subheader("Métricas de Qualidade: CC vs Não-CC")
metricas = ["review_count", "commits_count", "comment_count", "changed_files"]
labels   = ["Reviews",      "Commits",       "Comentários",   "Arquivos alterados"]

qual_df = (
    dff.groupby("is_cc")[metricas]
    .median()
    .T
    .reset_index()
)
qual_df.columns = ["Métrica", "Não Convencional", "Convencional"]
qual_df["Métrica"] = labels

fig_qual = go.Figure()
fig_qual.add_trace(go.Bar(
    name="Convencional",
    x=qual_df["Métrica"], y=qual_df["Convencional"],
    marker_color=COR_CC,
))
fig_qual.add_trace(go.Bar(
    name="Não Convencional",
    x=qual_df["Métrica"], y=qual_df["Não Convencional"],
    marker_color=COR_NAO_CC,
))
fig_qual.update_layout(
    barmode="group",
    title="Mediana das Métricas de Qualidade por Categoria",
    yaxis_title="Valor mediano",
)
st.plotly_chart(fig_qual, use_container_width=True)

st.caption(
    "O ranking mostra os 20 repositórios com maior proporção de PRs convencionais. "
    "O scatter relaciona adoção de CC com taxa de merge — cada ponto é um repositório, "
    "o tamanho indica volume de PRs e a cor reflete a média de revisões. "
    "As barras agrupadas comparam a mediana de reviews, commits, comentários e arquivos alterados "
    "entre PRs convencionais e não convencionais, revelando se o padrão está associado a PRs mais elaborados."
)

# ──────────────────────────────────────────────────────────────────────────────
# Tabela interativa
# ──────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("📋 Dataset Filtrado")
cols_exibir = [
    "repository", "pr_number", "pr_title", "is_merged",
    "time_to_close_hours", "title_is_conventional", "conventional_type",
    "review_count", "commits_count", "changed_files",
]
st.dataframe(
    dff[cols_exibir].rename(columns={
        "repository": "Repositório", "pr_number": "PR#", "pr_title": "Título",
        "is_merged": "Merged", "time_to_close_hours": "Tempo (h)",
        "title_is_conventional": "É CC", "conventional_type": "Tipo CC",
        "review_count": "Reviews", "commits_count": "Commits",
        "changed_files": "Arquivos",
    }),
    use_container_width=True,
    height=400,
)
