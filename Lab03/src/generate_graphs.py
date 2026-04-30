import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

GRAPHS_DIR = "../graphs"
DATA_PATH = "prs_dataset.csv"


def ensure_dir():
    os.makedirs(GRAPHS_DIR, exist_ok=True)


def load_data():
    df = pd.read_csv(DATA_PATH)
    return df


def spearman(x, y):
    mask = x.notna() & y.notna()
    if mask.sum() < 3:
        return float("nan"), float("nan")
    coef, pval = stats.spearmanr(x[mask], y[mask])
    return round(float(coef), 4), round(float(pval), 6)


def save(fig, name):
    path = os.path.join(GRAPHS_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {path}")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

COLORS = {"MERGED": "#2196F3", "CLOSED": "#F44336"}

METRIC_LABELS = {
    "changed_files":       "Arquivos Alterados",
    "total_lines_changed": "Linhas Alteradas (add+rem)",
    "analysis_time_hours": "Tempo de Análise (horas)",
    "description_length":  "Tamanho da Descrição (chars)",
    "participants":        "Nº de Participantes",
    "comments":            "Nº de Comentários",
    "review_count":        "Nº de Revisões",
}

RQ_STATUS = [
    ("RQ01",  "changed_files",       "Tamanho (arquivos) × Status do PR"),
    ("RQ01b", "total_lines_changed", "Tamanho (linhas) × Status do PR"),
    ("RQ02",  "analysis_time_hours", "Tempo de Análise × Status do PR"),
    ("RQ03",  "description_length",  "Descrição × Status do PR"),
    ("RQ04",  "participants",        "Participantes × Status do PR"),
    ("RQ04b", "comments",            "Comentários × Status do PR"),
]

RQ_REVIEWS = [
    ("RQ05",  "changed_files",       "Tamanho (arquivos) × Nº Revisões"),
    ("RQ05b", "total_lines_changed", "Tamanho (linhas) × Nº Revisões"),
    ("RQ06",  "analysis_time_hours", "Tempo de Análise × Nº Revisões"),
    ("RQ07",  "description_length",  "Descrição × Nº Revisões"),
    ("RQ08",  "participants",        "Participantes × Nº Revisões"),
    ("RQ08b", "comments",            "Comentários × Nº Revisões"),
]


# ──────────────────────────────────────────────────────────────────────────────
# 1. Boxplot individual por métrica (MERGED vs CLOSED)
# ──────────────────────────────────────────────────────────────────────────────

def plot_boxplot_individual(df, rq_id, metric, title):
    merged = df[df["state"] == "MERGED"][metric].dropna()
    closed = df[df["state"] == "CLOSED"][metric].dropna()
    coef, pval = spearman(df[metric], (df["state"] == "MERGED").astype(int))

    fig, ax = plt.subplots(figsize=(7, 5))
    bp = ax.boxplot(
        [merged, closed],
        labels=["MERGED", "CLOSED"],
        patch_artist=True,
        showfliers=False,
        widths=0.5,
    )
    for patch, color in zip(bp["boxes"], [COLORS["MERGED"], COLORS["CLOSED"]]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_ylabel(METRIC_LABELS.get(metric, metric))
    ax.set_xlabel("Status do PR")
    ax.annotate(
        f"Spearman ρ = {coef:+.4f}  |  p-valor = {pval:.2e}",
        xy=(0.5, 0.01), xycoords="axes fraction",
        ha="center", fontsize=9, color="gray",
    )
    fig.tight_layout()
    save(fig, f"{rq_id}_boxplot.png")


# ──────────────────────────────────────────────────────────────────────────────
# 2. Scatter individual por métrica (vs review_count)
# ──────────────────────────────────────────────────────────────────────────────

def plot_scatter_individual(df, rq_id, metric, title):
    sample = df[[metric, "review_count", "state"]].dropna()
    sample = sample.sample(min(1500, len(sample)), random_state=42)
    coef, pval = spearman(df[metric], df["review_count"])

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = sample["state"].map(COLORS).fillna("#999999")
    ax.scatter(sample[metric], sample["review_count"],
               c=colors, alpha=0.35, s=12, edgecolors="none")

    # Linha de tendência
    x_clean = sample[metric].dropna()
    y_clean = sample.loc[x_clean.index, "review_count"].dropna()
    common_idx = x_clean.index.intersection(y_clean.index)
    if len(common_idx) > 2:
        m, b, *_ = stats.linregress(x_clean[common_idx], y_clean[common_idx])
        x_range = sorted([x_clean.min(), x_clean.max()])
        ax.plot(x_range, [m * xi + b for xi in x_range],
                color="black", linewidth=1.5, linestyle="--", label="Tendência")

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel(METRIC_LABELS.get(metric, metric))
    ax.set_ylabel("Nº de Revisões")
    ax.annotate(
        f"Spearman ρ = {coef:+.4f}  |  p-valor = {pval:.2e}",
        xy=(0.5, 0.01), xycoords="axes fraction",
        ha="center", fontsize=9, color="gray",
    )
    legend_handles = [
        mpatches.Patch(color=COLORS["MERGED"], label="MERGED"),
        mpatches.Patch(color=COLORS["CLOSED"], label="CLOSED"),
    ]
    ax.legend(handles=legend_handles, fontsize=9)
    fig.tight_layout()
    save(fig, f"{rq_id}_scatter.png")


# ──────────────────────────────────────────────────────────────────────────────
# 3. Gráfico de barras com todos os ρ de Spearman
# ──────────────────────────────────────────────────────────────────────────────

def plot_spearman_summary(df):
    status = (df["state"] == "MERGED").astype(int)
    review_count = df["review_count"]

    all_rqs = RQ_STATUS + RQ_REVIEWS
    labels, coefs, sig_colors = [], [], []

    for rq_id, metric, _ in all_rqs:
        target = status if rq_id.startswith("RQ0" + str(int(rq_id[2]) if rq_id[2].isdigit() else 1)) and \
                           int(rq_id[2]) <= 4 else review_count
        # simpler mapping:
        target = status if rq_id in [r[0] for r in RQ_STATUS] else review_count
        coef, pval = spearman(df[metric], target)
        labels.append(rq_id)
        coefs.append(coef if not pd.isna(coef) else 0)
        sig_colors.append("#2196F3" if pval < 0.05 else "#BDBDBD")

    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(labels, coefs, color=sig_colors, edgecolor="white", width=0.6)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Coeficiente de Spearman (ρ) por Questão de Pesquisa",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("Spearman ρ")
    ax.set_xlabel("Questão de Pesquisa")
    ax.set_ylim(-0.4, 0.5)
    for bar, val in zip(bars, coefs):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (0.01 if val >= 0 else -0.03),
                f"{val:+.3f}", ha="center", va="bottom", fontsize=8)
    legend_handles = [
        mpatches.Patch(color="#2196F3", label="Significativo (p < 0.05)"),
        mpatches.Patch(color="#BDBDBD", label="Não significativo"),
    ]
    ax.legend(handles=legend_handles)
    fig.tight_layout()
    save(fig, "spearman_summary.png")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Gráfico de medianas comparado (MERGED vs CLOSED)
# ──────────────────────────────────────────────────────────────────────────────

def plot_medians_bar(df):
    metrics = [
        ("changed_files",       "Arquivos\nAlterados"),
        ("total_lines_changed", "Linhas\nAlteradas"),
        ("analysis_time_hours", "Tempo\nAnálise (h)"),
        ("description_length",  "Tamanho\nDescrição"),
        ("participants",        "Partici-\npantes"),
        ("comments",            "Comen-\ntários"),
        ("review_count",        "Nº\nRevisões"),
    ]

    merged_medians = [df[df["state"] == "MERGED"][m].median() for m, _ in metrics]
    closed_medians = [df[df["state"] == "CLOSED"][m].median() for m, _ in metrics]
    xlabels = [lbl for _, lbl in metrics]

    x = range(len(metrics))
    width = 0.38

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.bar([xi - width / 2 for xi in x], merged_medians, width,
           label="MERGED", color=COLORS["MERGED"], alpha=0.8)
    ax.bar([xi + width / 2 for xi in x], closed_medians, width,
           label="CLOSED", color=COLORS["CLOSED"], alpha=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(xlabels, fontsize=9)
    ax.set_ylabel("Mediana")
    ax.set_title("Medianas das Métricas: MERGED vs CLOSED",
                 fontsize=13, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    save(fig, "medians_comparison.png")


# ──────────────────────────────────────────────────────────────────────────────
# 5. Distribuição do status (pizza)
# ──────────────────────────────────────────────────────────────────────────────

def plot_status_pie(df):
    counts = df["state"].value_counts()
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(counts.values,
           labels=counts.index,
           autopct="%1.1f%%",
           colors=[COLORS.get(k, "#999") for k in counts.index],
           startangle=140,
           wedgeprops=dict(edgecolor="white", linewidth=1.5))
    ax.set_title("Distribuição dos PRs por Status", fontsize=13, fontweight="bold")
    fig.tight_layout()
    save(fig, "status_distribution.png")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    ensure_dir()
    print("Carregando dataset...")
    df = load_data()
    print(f"  {len(df)} PRs carregados.\n")

    print("Gerando gráfico de distribuição de status...")
    plot_status_pie(df)

    print("\nGerando gráfico de medianas...")
    plot_medians_bar(df)

    print("\nGerando resumo dos coeficientes de Spearman...")
    plot_spearman_summary(df)

    print("\nGerando boxplots individuais (RQ01–RQ04)...")
    for rq_id, metric, title in RQ_STATUS:
        plot_boxplot_individual(df, rq_id, metric, title)

    print("\nGerando scatter plots individuais (RQ05–RQ08)...")
    for rq_id, metric, title in RQ_REVIEWS:
        plot_scatter_individual(df, rq_id, metric, title)

    print("\nTodos os gráficos foram gerados em:", os.path.abspath(GRAPHS_DIR))


if __name__ == "__main__":
    main()

