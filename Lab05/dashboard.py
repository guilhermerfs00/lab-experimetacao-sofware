#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard.py – Lab05
Dashboard interativo (Streamlit + Plotly) para análise do experimento
GraphQL vs REST usando a GitHub API como objeto experimental.

Uso:
    cd d:\\lab-experimetacao-sofware\\Lab05
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
    page_title="Lab05 – GraphQL vs REST",
    layout="wide",
    initial_sidebar_state="expanded",
)

RESULTS_PATH = Path(__file__).parent / "docs" / "results.csv"

COR_REST    = "#EF4444"   # vermelho – REST
COR_GRAPHQL = "#2563EB"   # azul     – GraphQL

SCENARIO_LABELS = {
    "repo_info":    "Metadados de Repositório",
    "search_repos": "Busca de Repositórios",
    "user_profile": "Perfil de Usuário",
    "repo_issues":  "Issues de Repositório",
}

# ──────────────────────────────────────────────────────────────────────────────
# Carregamento e pré-processamento
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Carregando dataset…")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_PATH, on_bad_lines="skip")
    df = df[df["http_status"] == 200].copy()
    df["scenario_label"] = df["scenario"].map(SCENARIO_LABELS).fillna(df["scenario"])
    return df


if not RESULTS_PATH.exists():
    st.error(
        f"Dataset não encontrado: `{RESULTS_PATH}`\n\n"
        "Execute `python src/main.py` dentro da pasta Lab05 antes de abrir o dashboard."
    )
    st.stop()

df = load_data()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar – filtros
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.title("Filtros")

cenarios_disp = sorted(df["scenario_label"].unique())
cenarios_sel  = st.sidebar.multiselect(
    "Cenários",
    options=cenarios_disp,
    default=cenarios_disp,
)

apis_sel = st.sidebar.multiselect(
    "API",
    options=["REST", "GraphQL"],
    default=["REST", "GraphQL"],
)

remove_outliers = st.sidebar.checkbox("Remover outliers (IQR × 1,5)", value=True)

dff = df[df["scenario_label"].isin(cenarios_sel) & df["api_type"].isin(apis_sel)].copy()

if remove_outliers:
    for col in ["response_time_ms", "response_size_bytes"]:
        q1  = dff[col].quantile(0.25)
        q3  = dff[col].quantile(0.75)
        iqr = q3 - q1
        dff = dff[(dff[col] >= q1 - 1.5 * iqr) & (dff[col] <= q3 + 1.5 * iqr)]

# ──────────────────────────────────────────────────────────────────────────────
# Cabeçalho
# ──────────────────────────────────────────────────────────────────────────────
st.title("GraphQL vs REST — Experimento Controlado")
st.caption(
    f"Dataset: **{len(dff):,} medições** | "
    f"**{dff['scenario'].nunique()} cenários** | "
    f"Fonte: GitHub API"
)
st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Desenho do Experimento
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("Desenho do Experimento — Hipóteses, Variáveis e Metodologia", expanded=True):
    st.markdown("""
## Contexto

A linguagem de consulta **GraphQL**, proposta pelo Facebook, representa uma alternativa às
APIs REST. Enquanto REST baseia-se em *endpoints* fixos que retornam estruturas pré-definidas,
GraphQL permite que o cliente especifique exatamente os campos desejados, potencialmente
reduzindo *over-fetching* e melhorando o desempenho.

---

## Hipóteses

### RQ1 – Tempo de Resposta

| | |
|---|---|
| **H₀ (nula)**        | O tempo de resposta de consultas GraphQL é **igual** ao de consultas REST. |
| **H₁ (alternativa)** | O tempo de resposta de consultas GraphQL é **menor** que o de consultas REST. |

### RQ2 – Tamanho da Resposta

| | |
|---|---|
| **H₀ (nula)**        | O tamanho da resposta GraphQL é **igual** ao de respostas REST. |
| **H₁ (alternativa)** | O tamanho da resposta GraphQL é **menor** que o de respostas REST. |

---

## Variáveis

| Tipo | Variável | Unidade |
|---|---|---|
| **Dependente** | Tempo de resposta | milissegundos (ms) |
| **Dependente** | Tamanho da resposta | bytes |
| **Independente** | Tipo de API | REST / GraphQL |
| **Controlada** | Objeto experimental | endpoint / query |
| **Controlada** | Token de autenticação | token GitHub |
| **Controlada** | Ambiente de rede | Mesma máquina, mesma conexão |

---

## Tipo de Projeto Experimental

**Experimento controlado com dois tratamentos independentes** (REST × GraphQL), aplicados
a objetos experimentais equivalentes. Delineamento: *within-subjects* por cenário — ambos
os tratamentos são aplicados ao mesmo conjunto de objetos.

---

## Quantidade de Medições

- **4 cenários × 2 APIs × 30 trials = 240 medições**
- Pausa de 1,5 s entre chamadas para respeitar o rate-limit do GitHub
- Chamadas de aquecimento descartadas para evitar viés de cache/DNS

---

## Ameaças à Validade

| Tipo | Ameaça | Mitigação |
|---|---|---|
| **Interna** | Variação de latência de rede | Múltiplos trials; pausa entre chamadas |
| **Interna** | Cache do servidor GitHub | Headers `Cache-Control: no-cache` |
| **Interna** | Rate limiting | Pausa de 1,5 s; token autenticado |
| **Construto** | Equivalência REST↔GraphQL | Queries GraphQL projetadas para retornar os mesmos campos dos endpoints REST |
| **Externa** | Generalização para outras APIs | Experimento limitado à GitHub API |
    """)

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Visão Geral (KPIs)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Visão Geral")
st.caption(
    "Total de medições coletadas para cada API no experimento."
)

col1, col2 = st.columns(2)

rest_df    = dff[dff["api_type"] == "REST"]
graphql_df = dff[dff["api_type"] == "GraphQL"]

with col1:
    st.metric("Medições REST",    len(rest_df))
with col2:
    st.metric("Medições GraphQL", len(graphql_df))

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ1 – Tempo de Resposta
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("RQ1 – Tempo de Resposta (ms)")
st.caption(
    "Comparação do tempo de resposta (em milissegundos) entre REST e GraphQL nos quatro cenários "
    "do experimento. Use as abas para alternar entre o gráfico de barras e as estatísticas descritivas completas."
)

tab_rq1_bar, tab_rq1_tabela = st.tabs(["Mediana por Cenário", "Tabela Estatística"])

with tab_rq1_bar:
    agg = (
        dff.groupby(["scenario_label", "api_type"])["response_time_ms"]
        .agg(mediana="median", std="std")
        .reset_index()
    )
    fig = px.bar(
        agg,
        x="scenario_label",
        y="mediana",
        color="api_type",
        barmode="group",
        error_y="std",
        color_discrete_map={"REST": COR_REST, "GraphQL": COR_GRAPHQL},
        labels={
            "scenario_label": "Cenário",
            "mediana":        "Mediana do Tempo (ms)",
            "api_type":       "API",
        },
        title="Mediana do Tempo de Resposta por Cenário",
        text_auto=".0f",
    )
    fig.update_layout(height=440)
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

with tab_rq1_tabela:
    table_rq1 = (
        dff.groupby(["scenario_label", "api_type"])["response_time_ms"]
        .agg(n="count", mediana="median", media="mean", std="std", minimo="min", maximo="max")
        .round(2)
        .reset_index()
        .rename(columns={
            "scenario_label": "Cenário",
            "api_type":       "API",
            "n":              "N",
            "mediana":        "Mediana (ms)",
            "media":          "Média (ms)",
            "std":            "DP (ms)",
            "minimo":         "Mín (ms)",
            "maximo":         "Máx (ms)",
        })
    )
    st.dataframe(table_rq1, use_container_width=True, hide_index=True)

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# RQ2 – Tamanho da Resposta
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("RQ2 – Tamanho da Resposta (bytes)")
st.caption(
    "Comparação do tamanho das respostas (em bytes) entre REST e GraphQL. "
    "Respostas menores indicam menor transferência de dados — evidência de que GraphQL "
    "reduz o *over-fetching* ao retornar apenas os campos solicitados."
)

tab_rq2_bar, tab_rq2_tabela = st.tabs(["Mediana por Cenário", "Tabela Estatística"])

with tab_rq2_bar:
    agg2 = (
        dff.groupby(["scenario_label", "api_type"])["response_size_bytes"]
        .agg(mediana="median", std="std")
        .reset_index()
    )
    fig2 = px.bar(
        agg2,
        x="scenario_label",
        y="mediana",
        color="api_type",
        barmode="group",
        error_y="std",
        color_discrete_map={"REST": COR_REST, "GraphQL": COR_GRAPHQL},
        labels={
            "scenario_label": "Cenário",
            "mediana":        "Mediana do Tamanho (bytes)",
            "api_type":       "API",
        },
        title="Mediana do Tamanho da Resposta por Cenário",
        text_auto=".2s",
    )
    fig2.update_layout(height=440, yaxis_tickformat=",")
    fig2.update_traces(textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

with tab_rq2_tabela:
    table_rq2 = (
        dff.groupby(["scenario_label", "api_type"])["response_size_bytes"]
        .agg(n="count", mediana="median", media="mean", std="std", minimo="min", maximo="max")
        .round(0)
        .reset_index()
        .rename(columns={
            "scenario_label": "Cenário",
            "api_type":       "API",
            "n":              "N",
            "mediana":        "Mediana (bytes)",
            "media":          "Média (bytes)",
            "std":            "DP (bytes)",
            "minimo":         "Mín (bytes)",
            "maximo":         "Máx (bytes)",
        })
    )
    st.dataframe(table_rq2, use_container_width=True, hide_index=True)

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Análise Estatística – Mann-Whitney U
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Análise Estatística — Teste de Mann-Whitney U")
st.caption(
    "Teste não paramétrico aplicado par a par (GraphQL vs REST) para cada cenário e métrica. "
    "p-valor ≤ 0,05 indica diferença estatisticamente significativa. "
    "O Cliff's δ mede o tamanho do efeito: |δ| < 0,15 negligenciável; 0,15–0,33 pequeno; 0,33–0,47 médio; > 0,47 grande."
)

st.markdown("""
**Δ Mediana** = mediana(GraphQL) − mediana(REST)  
**Interpretação**: valor negativo indica que GraphQL apresenta menor valor.
""")

scenarios_all = df["scenario"].unique()
rows_stat: list[dict] = []

for scenario in scenarios_all:
    for metric, label_col, label_unit in [
        ("response_time_ms",    "Tempo de Resposta", "ms"),
        ("response_size_bytes", "Tamanho da Resposta", "bytes"),
    ]:
        r_vals = df[(df["scenario"] == scenario) & (df["api_type"] == "REST")][metric].dropna()
        g_vals = df[(df["scenario"] == scenario) & (df["api_type"] == "GraphQL")][metric].dropna()

        if len(r_vals) < 3 or len(g_vals) < 3:
            continue

        u_stat, p_val = stats.mannwhitneyu(g_vals, r_vals, alternative="two-sided")
        delta_med     = g_vals.median() - r_vals.median()
        m, n          = len(g_vals), len(r_vals)
        cliffs_d      = (2 * u_stat / (m * n)) - 1

        rows_stat.append({
            "Cenário":         SCENARIO_LABELS.get(scenario, scenario),
            "Métrica":         f"{label_col} ({label_unit})",
            "N REST":          int(len(r_vals)),
            "N GraphQL":       int(len(g_vals)),
            "Mediana REST":    round(r_vals.median(), 2),
            "Mediana GraphQL": round(g_vals.median(), 2),
            "Δ Mediana":       round(delta_med, 2),
            "p-valor":         round(p_val, 4),
            "Cliff's δ":       round(cliffs_d, 3),
            "Significativo?":  "✅ Sim" if p_val <= 0.05 else "❌ Não",
        })

df_stat = pd.DataFrame(rows_stat)
st.dataframe(df_stat, use_container_width=True, hide_index=True)

# Interpretação automática
st.markdown("### Interpretação Automática")

def _interpret(rq: str, metric: str) -> None:
    subset       = df_stat[df_stat["Métrica"].str.startswith(metric)]
    sig_count    = subset["Significativo?"].str.startswith("✅").sum()
    total        = len(subset)
    median_delta = subset["Δ Mediana"].mean()
    direction    = "menor" if median_delta < 0 else "maior"
    rq_label     = "Tempo de Resposta" if rq == "RQ1" else "Tamanho da Resposta"

    if sig_count > 0:
        st.success(
            f"**{rq} ({rq_label})**: Em {sig_count}/{total} cenários a diferença é "
            f"estatisticamente significativa (p ≤ 0,05). Em média, GraphQL apresentou "
            f"**{abs(median_delta):.1f} unidades {direction}** que REST."
        )
    else:
        st.warning(
            f"**{rq} ({rq_label})**: Nenhum cenário apresentou diferença estatisticamente "
            f"significativa (p > 0,05). Não há evidência suficiente para rejeitar H₀."
        )

if not df_stat.empty:
    _interpret("RQ1", "Tempo de Resposta")
    _interpret("RQ2", "Tamanho da Resposta")

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Evolução por Trial
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("Evolução das Medições por Trial")
st.caption(
    "Acompanha como o tempo e o tamanho das respostas variaram ao longo dos 30 trials "
    "para o cenário selecionado. Séries estáveis indicam ausência de interferências "
    "como cache progressivo ou degradação de rede durante a coleta."
)

cenario_ev   = st.selectbox("Cenário", options=list(SCENARIO_LABELS.values()), key="evolucao_cenario")
scenario_key = {v: k for k, v in SCENARIO_LABELS.items()}.get(cenario_ev, cenario_ev)
df_ev        = dff[dff["scenario"] == scenario_key].sort_values("trial_index")

col_ev1, col_ev2 = st.columns(2)
for col, metric, title in [
    (col_ev1, "response_time_ms",    "Tempo de Resposta (ms)"),
    (col_ev2, "response_size_bytes", "Tamanho da Resposta (bytes)"),
]:
    fig_ev = px.line(
        df_ev,
        x="trial_index",
        y=metric,
        color="api_type",
        color_discrete_map={"REST": COR_REST, "GraphQL": COR_GRAPHQL},
        markers=True,
        labels={"trial_index": "Trial #", metric: title, "api_type": "API"},
        title=f"{title} — {cenario_ev}",
    )
    col.plotly_chart(fig_ev, use_container_width=True)

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Dados Brutos
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("Dados Brutos"):
    cols_show = [c for c in [
        "scenario_label", "api_type", "trial_index",
        "response_time_ms", "response_size_bytes", "http_status",
        "owner", "repo", "language", "login",
    ] if c in dff.columns]
    st.dataframe(
        dff[cols_show].rename(columns={
            "scenario_label":      "Cenário",
            "api_type":            "API",
            "trial_index":         "Trial",
            "response_time_ms":    "Tempo (ms)",
            "response_size_bytes": "Tamanho (bytes)",
            "http_status":         "HTTP Status",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.caption("Lab05 – Laboratório de Experimentação de Software | GitHub API")
