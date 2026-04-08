import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd

# JVM flags configuráveis via variável de ambiente.
_DEFAULT_JVM_FLAGS = "-Xmx4g -XX:+UseG1GC -XX:+ParallelRefProcEnabled"
CK_JVM_FLAGS = os.environ.get("CK_JVM_FLAGS", _DEFAULT_JVM_FLAGS).split()


def run_ck(repo_path, output_path, ck_dir, timeout_seconds=None):
    ck_jar_path = resolve_ck_jar_path(ck_dir)

    # Verifica se o caminho de saída existe, se não, cria
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Monta o comando Java com flags de otimização da JVM.
    command = [
        "java",
        *CK_JVM_FLAGS,
        "-jar", ck_jar_path,
        repo_path,
        "true",
        "0",
        "true",
        output_path
    ]

    try:
        # Executa o comando Java suprimindo stdout para reduzir I/O.
        subprocess.run(
            command,
            check=True,
            timeout=timeout_seconds,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        print(f"[OK] CK concluido para {Path(repo_path).name}")
        return True
    except subprocess.CalledProcessError as e:
        stderr_msg = (e.stderr or b"").decode(errors="replace")[:300]
        print(f"[ERRO] Erro CK para {Path(repo_path).name}: {stderr_msg}")
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Timeout CK para {Path(repo_path).name}")
    except Exception as e:
        print(f"[!] Erro inesperado CK para {Path(repo_path).name}: {e}")
    return False


def resolve_ck_jar_path(ck_dir):
    """Resolve o caminho do JAR do CK com fallback para o arquivo local do Lab02."""
    local_jar = Path(__file__).resolve().with_name("ck-0.7.1-SNAPSHOT-jar-with-dependencies.jar")

    if ck_dir:
        ck_path = Path(ck_dir)
        if ck_path.is_file() and ck_path.suffix == ".jar":
            return str(ck_path)
        if ck_path.is_dir():
            candidates = sorted(ck_path.glob("*.jar"))
            if candidates:
                return str(candidates[0])

    return str(local_jar)


def summarize_ck_results(output_path, repo_prefix=None):
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = _coletar_csv_ck(output_dir, repo_prefix)

    if not csv_files:
        raise FileNotFoundError(f"Nenhum arquivo CSV encontrado no diretório {output_path} !")

    metrics_summary = {
        "Média CBO (Classes)": None,
        "Média DIT (Classes)": None,
        "Média LCOM (Classes)": None,
        "Média CBO (Métodos)": None,
    }

    for csv_file in csv_files:
        file_path = Path(csv_file)

        # Verificar se o arquivo não está vazio antes de tentar ler
        if os.path.getsize(file_path) == 0:
            print(f"[!] O arquivo {file_path.name} esta vazio e foi ignorado.")
            continue  # Ignora o arquivo vazio
        
        try:
            df = pd.read_csv(str(file_path))
        except Exception as e:
            print(f"Erro ao ler o arquivo {file_path.name}: {e}")
            continue  # Ignora arquivos que não puderam ser lidos

        if "class" in file_path.name:
            if "cbo" in df.columns and "dit" in df.columns and "lcom" in df.columns:
                metrics_summary["Média CBO (Classes)"] = df["cbo"].mean()
                metrics_summary["Média DIT (Classes)"] = df["dit"].mean()
                metrics_summary["Média LCOM (Classes)"] = df["lcom"].mean()
            else:
                print(f"[!] O arquivo {file_path.name} nao contem as colunas esperadas.")
        elif "method" in file_path.name:
            if "cbo" in df.columns:
                metrics_summary["Média CBO (Métodos)"] = df["cbo"].mean()
            else:
                print(f"[!] O arquivo {file_path.name} nao contem a coluna 'cbo'.")

    return metrics_summary


def _coletar_csv_ck(output_dir, repo_prefix=None):
    """Coleta CSVs do CK na pasta do repo e aplica fallback para CSVs prefixados no diretório pai."""
    csv_files = list(output_dir.rglob("*.csv"))
    if csv_files:
        return csv_files

    if not repo_prefix:
        return []

    parent_dir = output_dir.parent
    prefixed_csv = list(parent_dir.glob(f"{repo_prefix}*.csv"))
    if not prefixed_csv:
        return []

    for csv_path in prefixed_csv:
        destino = output_dir / csv_path.name
        shutil.move(str(csv_path), str(destino))

    return list(output_dir.rglob("*.csv"))

