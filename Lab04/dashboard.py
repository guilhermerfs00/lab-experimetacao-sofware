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

st.sidebar.markdown("---")
cap_tempo = st.sidebar.slider(
    "Cap tempo de fechamento (h) — outliers",
    min_value=24, max_value=8760, value=2160, step=24,
    help="PRs com tempo acima deste valor são excluídos dos gráficos de tempo.",
)

# Aplica filtros
mask = pd.Series(True, index=df.index)
if repos_sel:
    mask &= df["repository"].isin(repos_sel)
if tipos_sel:
    mask &= df["conventional_type"].isin(tipos_sel)

dff = df[mask].copy()
dff_tempo = dff[dff["time_to_close_hours"] <= cap_tempo].copy()

# ──────────────────────────────────────────────────────────────────────────────
# Cabeçalho
# ──────────────────────────────────────────────────────────────────────────────
st.title("🔀 Conventional Commits & Pull Requests Java")
st.caption(
    f"Dataset: **{len(dff):,} PRs** | **{dff['repository'].nunique()} repositórios** | "
    f"Fonte: GitHub API"
)
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
st.header("RQ1 – Frequência de Conventional Commits")
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
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ2 – Taxa de Merge
# ──────────────────────────────────────────────────────────────────────────────
st.header("RQ2 – Taxa de Merge: CC vs Não-CC")
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
col_stat1.metric("Diferença na taxa de merge", f"{diferenca_pp:+.1f} p.p.",
                 help="CC minus Não-CC")
col_stat2.metric("Qui-quadrado (χ²)", f"{chi2:.2f}")
col_stat3.metric("p-valor", f"{p_valor:.4f}",
                 delta="Significativo (p<0.05)" if p_valor < 0.05 else "Não significativo",
                 delta_color="normal" if p_valor < 0.05 else "off")
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ3 – Tempo até o Merge
# ──────────────────────────────────────────────────────────────────────────────
st.header(f"RQ3 – Tempo até Fechamento (cap: {cap_tempo:,}h)")
rq3_col1, rq3_col2 = st.columns(2)

cc_tempo  = dff_tempo.loc[dff_tempo["is_cc"],   "time_to_close_hours"].dropna()
ncc_tempo = dff_tempo.loc[~dff_tempo["is_cc"],  "time_to_close_hours"].dropna()

with rq3_col1:
    fig_box = go.Figure()
    fig_box.add_trace(go.Box(
        y=cc_tempo, name="Convencional",
        marker_color=COR_CC, boxmean="sd",
    ))
    fig_box.add_trace(go.Box(
        y=ncc_tempo, name="Não Convencional",
        marker_color=COR_NAO_CC, boxmean="sd",
    ))
    fig_box.update_layout(
        title="Distribuição do Tempo de Fechamento",
        yaxis_title="Horas",
        showlegend=True,
    )
    st.plotly_chart(fig_box, use_container_width=True)

with rq3_col2:
    # Histograma comparativo
    hist_df = dff_tempo[["time_to_close_hours", "is_cc"]].copy()
    hist_df["Categoria"] = hist_df["is_cc"].map({True: "Convencional", False: "Não Convencional"})
    fig_hist = px.histogram(
        hist_df, x="time_to_close_hours", color="Categoria",
        color_discrete_map={"Convencional": COR_CC, "Não Convencional": COR_NAO_CC},
        barmode="overlay", opacity=0.7, nbins=60,
        title="Histograma – Tempo de Fechamento",
        labels={"time_to_close_hours": "Horas", "count": "Nº de PRs"},
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# Métricas resumidas
t_stat, p_mann = stats.mannwhitneyu(cc_tempo, ncc_tempo, alternative="two-sided")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Mediana CC (h)",       f"{cc_tempo.median():.1f}")
m2.metric("Mediana Não-CC (h)",   f"{ncc_tempo.median():.1f}")
m3.metric("Mann-Whitney U",       f"{t_stat:,.0f}")
m4.metric("p-valor (tempo)",      f"{p_mann:.4f}",
          delta="Significativo (p<0.05)" if p_mann < 0.05 else "Não significativo",
          delta_color="normal" if p_mann < 0.05 else "off")
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ4 – Adoção por Repositório e Métricas de Qualidade
# ──────────────────────────────────────────────────────────────────────────────
st.header("RQ4 – Adoção por Repositório e Métricas de Qualidade")
rq4_col1, rq4_col2 = st.columns(2)

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

with rq4_col1:
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

with rq4_col2:
    fig_scatter = px.scatter(
        repo_stats, x="pct_cc", y="pct_merge",
        size="total", color="avg_reviews",
        hover_name="repo_short",
        color_continuous_scale="Viridis",
        title="% CC vs Taxa de Merge (tamanho = nº PRs)",
        labels={
            "pct_cc":    "% PRs Convencionais",
            "pct_merge": "Taxa de Merge",
            "avg_reviews": "Avg Reviews",
        },
    )
    fig_scatter.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%")
    st.plotly_chart(fig_scatter, use_container_width=True)

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
