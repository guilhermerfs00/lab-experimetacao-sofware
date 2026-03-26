from pathlib import Path
import subprocess
import os

import pandas as pd


def run_ck(repo_path: Path, output_path: Path, ck_jar_path: Path, demo_mode: bool = False) -> None:
    """Executa o CK para o repositorio atual e grava os CSVs de metricas no diretorio de saida.
    
    Se demo_mode=True, gera CSVs fake para validacao sem executar CK real (necessario quando
    JAR com dependencias nao esta disponivel).
    """

    if not ck_jar_path.exists():
        raise FileNotFoundError(f"Arquivo CK nao encontrado: {ck_jar_path}")

    output_path.mkdir(parents=True, exist_ok=True)

    if demo_mode:
        _generate_demo_csv(output_path)
        return

    command = [
        "java",
        "-jar",
        str(ck_jar_path),
        str(repo_path),
        "true",
        "0",
        "true",
        str(output_path),
    ]
    subprocess.run(command, check=True)


def _generate_demo_csv(output_path: Path) -> None:
    """Gera CSVs fake para teste de fluxo quando CK real nao esta disponivel."""

    import random
    
    class_data = {
        "cbo": [random.uniform(1, 10) for _ in range(20)],
        "dit": [random.randint(1, 5) for _ in range(20)],
        "lcom": [random.uniform(0, 100) for _ in range(20)],
    }
    df_class = pd.DataFrame(class_data)
    df_class.to_csv(output_path / "class.csv", index=False)
    
    method_data = {
        "cbo": [random.uniform(0.5, 5) for _ in range(50)],
    }
    df_method = pd.DataFrame(method_data)
    df_method.to_csv(output_path / "method.csv", index=False)


def summarize_ck_results(output_path: Path) -> dict:
    """Le os CSVs gerados pelo CK e calcula medias das metricas usadas no relatorio."""

    if not output_path.exists() or not output_path.is_dir():
        raise FileNotFoundError(f"Diretorio {output_path} nao encontrado.")

    csv_files = [path for path in output_path.iterdir() if path.suffix.lower() == ".csv"]
    if not csv_files:
        raise FileNotFoundError(f"Nenhum CSV do CK encontrado em {output_path}.")

    metrics_summary = {
        "Média CBO (Classes)": None,
        "Média DIT (Classes)": None,
        "Média LCOM (Classes)": None,
        "Média CBO (Métodos)": None,
    }

    for csv_path in csv_files:
        if csv_path.stat().st_size == 0:
            continue

        try:
            df = pd.read_csv(csv_path)
        except Exception:
            continue

        name = csv_path.name.lower()
        if "class" in name and {"cbo", "dit", "lcom"}.issubset(df.columns):
            metrics_summary["Média CBO (Classes)"] = float(df["cbo"].mean())
            metrics_summary["Média DIT (Classes)"] = float(df["dit"].mean())
            metrics_summary["Média LCOM (Classes)"] = float(df["lcom"].mean())

        if "method" in name and "cbo" in df.columns:
            metrics_summary["Média CBO (Métodos)"] = float(df["cbo"].mean())

    return metrics_summary

