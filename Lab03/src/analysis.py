# -*- coding: utf-8 -*-
"""
analysis.py
Responde as 8 RQs usando correlacao de Spearman e gera graficos.
"""

import os

import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

DOCS_DIR = "../docs"


def _ensure_docs():
    os.makedirs(DOCS_DIR, exist_ok=True)


def load_dataset(path: str = "prs_dataset.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def _spearman(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    """Retorna (coeficiente, p-valor) da correlacao de Spearman entre x e y."""
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan"), float("nan")
    coef, pval = stats.spearmanr(x[mask], y[mask])
    return round(float(coef), 4), round(float(pval), 6)


def _binary_status(df: pd.DataFrame) -> pd.Series:
    """Converte state em variavel binaria: MERGED=1, CLOSED=0."""
    return (df["state"] == "MERGED").astype(int)


def run_rq_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Executa todas as 8 RQs e retorna um DataFrame com os resultados."""

    status = _binary_status(df)
    review_count = df["review_count"]

    rq_map = [
        ("RQ01",  "changed_files",        status,       "Tamanho (arquivos) x Status do PR"),
        ("RQ01b", "total_lines_changed",   status,       "Tamanho (linhas)   x Status do PR"),
        ("RQ02",  "analysis_time_hours",   status,       "Tempo de Analise   x Status do PR"),
        ("RQ03",  "description_length",    status,       "Descricao          x Status do PR"),
        ("RQ04",  "participants",          status,       "Participantes      x Status do PR"),
        ("RQ04b", "comments",              status,       "Comentarios        x Status do PR"),
        ("RQ05",  "changed_files",         review_count, "Tamanho (arquivos) x Nr Revisoes"),
        ("RQ05b", "total_lines_changed",   review_count, "Tamanho (linhas)   x Nr Revisoes"),
        ("RQ06",  "analysis_time_hours",   review_count, "Tempo de Analise   x Nr Revisoes"),
        ("RQ07",  "description_length",    review_count, "Descricao          x Nr Revisoes"),
        ("RQ08",  "participants",          review_count, "Participantes      x Nr Revisoes"),
        ("RQ08b", "comments",              review_count, "Comentarios        x Nr Revisoes"),
    ]

    results = []
    for rq_id, metric_col, target, label in rq_map:
        coef, pval = _spearman(df[metric_col], target)
        significant = "YES" if pval < 0.05 else "NO"
        results.append({
            "RQ": rq_id,
            "Relacao": label,
            "Spearman rho": coef,
            "p-valor": pval,
            "Significativo (p<0.05)": significant
        })
        print(f"  {rq_id} | {label:45s} | rho={coef:+.4f} | p={pval:.6f} [{significant}]")

    result_df = pd.DataFrame(results)
    _ensure_docs()
    out_path = os.path.join(DOCS_DIR, "rq_results.csv")
    result_df.to_csv(out_path, index=False)
    print(f"\n[OK] Resultados das RQs salvos em '{out_path}'")
    return result_df


def print_medians(df: pd.DataFrame):
    """Imprime e salva valores medianos das principais metricas separando MERGED e CLOSED."""
    print("\n" + "=" * 70)
    print("MEDIANAS GLOBAIS")
    print("=" * 70)
    cols = ["changed_files", "total_lines_changed", "analysis_time_hours",
            "description_length", "participants", "comments", "review_count"]

    rows = []
    for state in ["MERGED", "CLOSED"]:
        sub = df[df["state"] == state]
        print(f"\n--- {state} ({len(sub)} PRs) ---")
        for col in cols:
            median_val = sub[col].median()
            print(f"  {col:30s}: {median_val:.2f}")
            rows.append({"Estado": state, "Metrica": col, "Mediana": round(median_val, 2)})

    _ensure_docs()
    medians_path = os.path.join(DOCS_DIR, "medians.csv")
    pd.DataFrame(rows).to_csv(medians_path, index=False)
    print(f"\n[OK] Medianas salvas em '{medians_path}'")


def plot_boxplots(df: pd.DataFrame):
    """Gera boxplots comparando MERGED vs CLOSED para as metricas principais."""
    cols = [
        ("changed_files",       "Arquivos Alterados"),
        ("total_lines_changed", "Linhas Alteradas"),
        ("analysis_time_hours", "Tempo de Analise (h)"),
        ("description_length",  "Tamanho da Descricao"),
        ("participants",        "Participantes"),
        ("comments",            "Comentarios"),
        ("review_count",        "Nr de Revisoes"),
    ]

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()

    for i, (col, label) in enumerate(cols):
        data_merged = df[df["state"] == "MERGED"][col].dropna()
        data_closed = df[df["state"] == "CLOSED"][col].dropna()
        axes[i].boxplot([data_merged, data_closed], labels=["MERGED", "CLOSED"], showfliers=False)
        axes[i].set_title(label)
        axes[i].set_ylabel("Valor")

    axes[-1].set_visible(False)
    plt.suptitle("Distribuicao das Metricas por Status do PR (sem outliers extremos)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    _ensure_docs()
    out_path = os.path.join(DOCS_DIR, "lab03_boxplots.png")
    plt.savefig(out_path, dpi=150)
    plt.show()
    print(f"[OK] Boxplots salvos em '{out_path}'")


def plot_scatter_reviews(df: pd.DataFrame):
    """Gera scatter plots das metricas vs numero de revisoes."""
    cols = [
        ("changed_files",       "Arquivos Alterados"),
        ("total_lines_changed", "Linhas Alteradas"),
        ("analysis_time_hours", "Tempo de Analise (h)"),
        ("description_length",  "Tamanho da Descricao"),
        ("participants",        "Participantes"),
        ("comments",            "Comentarios"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for i, (col, label) in enumerate(cols):
        sample = df[[col, "review_count"]].dropna().sample(min(1000, len(df)), random_state=42)
        axes[i].scatter(sample[col], sample["review_count"], alpha=0.3, s=10)
        axes[i].set_xlabel(label)
        axes[i].set_ylabel("Nr de Revisoes")
        axes[i].set_title(f"{label} x Nr de Revisoes")

    plt.suptitle("Metricas vs Numero de Revisoes", fontsize=14, fontweight="bold")
    plt.tight_layout()
    _ensure_docs()
    out_path = os.path.join(DOCS_DIR, "lab03_scatter_reviews.png")
    plt.savefig(out_path, dpi=150)
    plt.show()
    print(f"[OK] Scatter plots salvos em '{out_path}'")
