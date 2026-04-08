from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import shutil
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import matplotlib
matplotlib.use("Agg")          # back-end sem janela – seguro p/ threads
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from git import Repo
from pygount import ProjectSummary, SourceAnalysis
from requests.adapters import HTTPAdapter
from scipy.stats import spearmanr
from urllib3.util.retry import Retry

import quality_metrics_adapter

# Carregar variáveis de ambiente
BASE_DIR = Path(__file__).resolve().parent
LAB02_DIR = BASE_DIR.parent
WORKDIR_DIR = LAB02_DIR / "workdir"
CLONES_DIR = WORKDIR_DIR / "clones"
CK_OUTPUT_DIR = WORKDIR_DIR / "ck_output"
REPORTS_DIR = LAB02_DIR / "reports"
CHECKPOINT_CSV = WORKDIR_DIR / "results_checkpoint.csv"
CHECKPOINT_META = WORKDIR_DIR / "cursor_checkpoint.json"

load_dotenv(LAB02_DIR / ".env")
load_dotenv()

# TOKEN = os.getenv("GITHUB_TOKEN")
# API_URL = os.getenv("GITHUB_API_URL")
# ck_path = os.getenv("CK_REPO_PATH")

API_URL = os.environ.get("API_URL") or os.environ.get("GITHUB_API_URL")
TOKEN = os.environ.get("TOKEN") or os.environ.get("GITHUB_TOKEN")
ck_path = os.environ.get("CK_REPO_URL") or os.environ.get("CK_REPO_PATH")


def _resolve_github_graphql_url(configured_url):
    default_url = "https://api.github.com/graphql"
    if not configured_url:
        return default_url

    normalized = configured_url.strip().strip('"').rstrip("/")
    if not normalized:
        return default_url

    parsed = urlparse(normalized)
    if not parsed.scheme or not parsed.netloc:
        return default_url

    path = parsed.path.lower()
    if path.endswith("/graphql"):
        return normalized

    # Compatibilidade com .env legado que usa https://api.github.com (REST).
    if parsed.netloc.lower() == "api.github.com" and path in ("", "/"):
        return f"{normalized}/graphql"

    return normalized


GITHUB_GRAPHQL_URL = _resolve_github_graphql_url(API_URL)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Configurações de rede para reduzir timeout e requisições falhas.
REQUEST_TIMEOUT_CONNECT = float(os.environ.get("GITHUB_TIMEOUT_CONNECT", "10"))
REQUEST_TIMEOUT_READ = float(os.environ.get("GITHUB_TIMEOUT_READ", "60"))
REQUEST_MAX_RETRIES = int(os.environ.get("GITHUB_MAX_RETRIES", "8"))
REQUEST_BACKOFF_SECONDS = float(os.environ.get("GITHUB_BACKOFF_SECONDS", "3.0"))
CK_MAX_WORKERS = int(os.environ.get("CK_MAX_WORKERS", str(max(4, (os.cpu_count() or 4) - 1))))
CK_TIMEOUT_SECONDS = int(os.environ.get("CK_TIMEOUT_SECONDS", "600"))

# Limite máximo de caminho para Windows
MAX_PATH_LENGTH = 260


def _build_http_session():
    """Sessao HTTP com retries minimos no nivel urllib3; retries inteligentes ficam no nivel da aplicacao."""
    session = requests.Session()

    retry = Retry(
        total=2,
        connect=2,
        read=2,
        backoff_factor=1.0,
        status_forcelist=[429],         # so 429 (rate limit) no nivel urllib3
        allowed_methods=frozenset(["POST"]),
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


HTTP_SESSION = _build_http_session()


def garantir_diretorios_trabalho():
    """Cria a estrutura de pastas usada durante a execução do Lab02."""
    for path in (WORKDIR_DIR, CLONES_DIR, CK_OUTPUT_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)

def _fetch_repositories_page(first, cursor=None):
    """Busca uma página GraphQL de repositórios Java populares."""
    query = """
    query($first: Int!, $after: String) {
       search(query: "stars:>100 language:Java -topic:tutorial -topic:learning -topic:javaguide", type: REPOSITORY, first: $first, after: $after) {
        edges {
          node {
            ... on Repository {
              name
              owner { login }
              createdAt
              updatedAt
              stargazerCount
              description
              primaryLanguage { name }
              pullRequests(states: MERGED) { totalCount }
              releases { totalCount }
              openIssues: issues(states: OPEN) { totalCount }
              closedIssues: issues(states: CLOSED) { totalCount }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """

    payload = {
        "query": query,
        "variables": {
            "first": first,
            "after": cursor,
        },
    }

    data = _post_graphql_with_retry(payload)
    if data is None:
        return [], cursor, False

    search_data = ((data.get("data") or {}).get("search") or {})
    repositories = search_data.get("edges") or []
    page_info = search_data.get("pageInfo") or {}
    has_next_page = bool(page_info.get("hasNextPage"))
    next_cursor = page_info.get("endCursor") if has_next_page else None
    return repositories, next_cursor, has_next_page


def fetchRepositories(start, end, cursor=None, return_page_state=False):
    """Faz a coleta paginada de repositórios até alcançar o intervalo solicitado."""
    allRepos = []
    totalRepos = max(0, end - start)
    if totalRepos == 0:
        return ([], cursor, False) if return_page_state else []

    base_batch_size = int(os.environ.get("GITHUB_BATCH_SIZE", "30"))
    batch_size = max(1, min(100, base_batch_size))

    chamada = 0
    has_next_page = True

    while len(allRepos) < totalRepos and has_next_page:
        chamada += 1
        faltantes = totalRepos - len(allRepos)
        first = min(batch_size, faltantes)
        print(f"[..] Buscando repositorios... (Chamada {chamada}, coletados {len(allRepos)}/{totalRepos})")

        repositories, cursor, has_next_page = _fetch_repositories_page(first, cursor=cursor)
        if not repositories and has_next_page is False:
            print("[!] Coleta interrompida por falhas repetidas na API do GitHub.")
            break

        if not repositories:
            print("[!] Nenhum repositorio retornado nesta pagina.")
            break

        # Mantém o filtro educacional para não alterar o comportamento atual.
        filtered_repos = [
            repo for repo in repositories
            if not is_educational(repo.get("node", {}))
        ]

        allRepos.extend(filtered_repos)
        print(f"[OK] Chamada {chamada} concluida ({len(allRepos)}/{totalRepos} repositorios coletados)\n")

    result = allRepos[:totalRepos]
    if return_page_state:
        return result, cursor, has_next_page
    return result


def coletar_e_processar_repositorios(start, end, max_workers=None, ck_timeout_seconds=None, resume=False):
    """Busca e processa repositórios em lotes até tentar analisar a quantidade alvo.

    Se *resume=True*, carrega progresso anterior de checkpoint.
    """
    target_repos = max(0, end - start)
    if target_repos == 0:
        return pd.DataFrame()

    garantir_diretorios_trabalho()

    all_rows: list[dict] = []
    cursor = None
    has_next_page = True
    lote = 0

    # ---------- Resume de checkpoint ----------
    if resume:
        ckpt_df, saved_cursor = _load_checkpoint()
        if not ckpt_df.empty:
            all_rows = ckpt_df.to_dict("records")
            cursor = saved_cursor
            print(f"[RESUME] Checkpoint carregado: {len(all_rows)} repositorios ja analisados.")
            if len(all_rows) >= target_repos:
                print("[OK] Checkpoint ja contem a meta desejada.")
                return pd.DataFrame(all_rows[:target_repos])

    processed_keys: set[tuple[str, str]] = {
        (r.get("Nome", ""), r.get("Proprietário", "")) for r in all_rows
    }

    while len(all_rows) < target_repos and has_next_page:
        lote += 1
        remaining = target_repos - len(all_rows)
        fetch_target = min(200, max(remaining, remaining * 2))

        print(f"\n>> Lote {lote}: buscando candidatos para completar {remaining} analises restantes...")
        repositories, cursor, has_next_page = fetchRepositories(
            0,
            fetch_target,
            cursor=cursor,
            return_page_state=True,
        )

        if not repositories:
            break

        # Filtrar repos já processados neste lote.
        new_repos = [
            r for r in repositories
            if (
                r.get("node", {}).get("name", ""),
                (r.get("node", {}).get("owner") or {}).get("login", ""),
            ) not in processed_keys
        ]

        if not new_repos:
            continue

        batch_df = processData(
            new_repos,
            max_workers=max_workers,
            ck_timeout_seconds=ck_timeout_seconds,
        )
        if batch_df is not None and not batch_df.empty:
            new_records = batch_df.to_dict("records")
            all_rows.extend(new_records)
            for rec in new_records:
                processed_keys.add((rec.get("Nome", ""), rec.get("Proprietário", "")))

            # ---------- Salva checkpoint incremental ----------
            _save_checkpoint(pd.DataFrame(all_rows), cursor)

        print(f"[PROGRESSO] {min(len(all_rows), target_repos)}/{target_repos} analisados")

    final_df = pd.DataFrame(all_rows[:target_repos])

    if final_df.empty:
        raise RuntimeError("Nenhum repositório foi analisado com sucesso.")

    if len(final_df) < target_repos:
        print(
            f"[!] Atingiu apenas {len(final_df)}/{target_repos} repositorios. "
            "Gerando relatorio com os dados disponiveis."
        )
    else:
        print(f"[OK] Meta atingida: {target_repos} repositorios analisados.")
        _clear_checkpoint()

    # Salva CSV bruto sempre.
    raw_csv_path = REPORTS_DIR / "dados_brutos.csv"
    raw_csv_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(raw_csv_path, index=False, encoding="utf-8-sig")
    print(f"[SALVO] Dados brutos salvos em: {raw_csv_path}")

    return final_df


# --------------- Checkpoint helpers ---------------

def _save_checkpoint(df: pd.DataFrame, cursor: str | None):
    """Salva progresso incremental em disco."""
    WORKDIR_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(CHECKPOINT_CSV, index=False, encoding="utf-8-sig")
    meta = {"cursor": cursor}
    CHECKPOINT_META.write_text(json.dumps(meta), encoding="utf-8")


def _load_checkpoint():
    """Retorna (DataFrame, cursor) do checkpoint, ou (DataFrame vazio, None)."""
    df = pd.DataFrame()
    cursor = None
    if CHECKPOINT_CSV.exists():
        try:
            df = pd.read_csv(CHECKPOINT_CSV, encoding="utf-8-sig")
        except Exception:
            df = pd.DataFrame()
    if CHECKPOINT_META.exists():
        try:
            meta = json.loads(CHECKPOINT_META.read_text(encoding="utf-8"))
            cursor = meta.get("cursor")
        except Exception:
            cursor = None
    return df, cursor


def _clear_checkpoint():
    """Remove arquivos de checkpoint após conclusão bem-sucedida."""
    for f in (CHECKPOINT_CSV, CHECKPOINT_META):
        try:
            if f.exists():
                f.unlink()
        except OSError:
            pass


def _post_graphql_with_retry(payload):
    """Envia payload GraphQL com retentativas e back-off linear curto."""
    session = HTTP_SESSION
    for attempt in range(1, REQUEST_MAX_RETRIES + 1):
        try:
            response = session.post(
                GITHUB_GRAPHQL_URL,
                json=payload,
                headers=headers,
                timeout=(REQUEST_TIMEOUT_CONNECT, REQUEST_TIMEOUT_READ),
            )
        except requests.exceptions.RequestException as error:
            espera = min(30, REQUEST_BACKOFF_SECONDS * attempt)
            print(f"[!] Erro de conexao ({attempt}/{REQUEST_MAX_RETRIES}): {str(error)[:120]}  aguardando {espera:.0f}s")
            time.sleep(espera)
            continue

        if response.status_code == 200:
            data = response.json()
            graphql_errors = data.get("errors")
            if graphql_errors:
                espera = min(30, REQUEST_BACKOFF_SECONDS * attempt)
                print(f"[!] Erro GraphQL ({attempt}/{REQUEST_MAX_RETRIES}): {str(graphql_errors)[:120]}  aguardando {espera:.0f}s")
                time.sleep(espera)
                continue
            return data

        if response.status_code in (401, 403):
            print(f"[ERRO] Autenticacao falhou ({response.status_code}). Verifique GITHUB_TOKEN.")
            return None

        espera = min(30, REQUEST_BACKOFF_SECONDS * attempt)
        print(f"[!] HTTP {response.status_code} ({attempt}/{REQUEST_MAX_RETRIES})  aguardando {espera:.0f}s")
        time.sleep(espera)

    print("[ERRO] Todas as tentativas de conexao com GitHub falharam.")
    return None

def is_educational(repo):
    """Filtro leve: exclui apenas por nome do repo (tópicos já excluídos na query GraphQL)."""
    keywords = ["tutorial", "example", "guide", "learning", "course", "demo", "how-to"]
    name = repo.get("name", "").lower()
    return any(keyword in name for keyword in keywords)

def has_java_files(repo_path):
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".java"):
                return True
    return False

def _analyze_single_repository(repo, ck_timeout_seconds=None):
    node = repo.get('node', {})
    repo_name = node.get('name', '')
    owner = (node.get('owner') or {}).get('login', '')

    if not repo_name or not owner:
        return None

    if len(repo_name) > 100:
        print(f"[SKIP] Repositorio {repo_name} ignorado (nome muito longo)")
        return None

    repo_age = calculate_repos_age(node['createdAt'])
    clean_name = clean_repo_name(f"{owner}__{repo_name}")
    repo_url = f"https://github.com/{owner}/{repo_name}.git"

    repo_path = CLONES_DIR / clean_name
    ck_output_path = CK_OUTPUT_DIR / clean_name

    try:
        clone_repo(str(repo_path), repo_url)
        if not repo_path.exists() or not has_java_files(str(repo_path)):
            print(f"[SKIP] Repositorio {repo_name} ignorado (nao contem arquivos .java)")
            return None

        code_lines, comment_lines = count_lines(repo_path)
        ck_ok = quality_metrics_adapter.run_ck(
            str(repo_path),
            str(ck_output_path),
            ck_path,
            timeout_seconds=ck_timeout_seconds,
        )
        if not ck_ok:
            return None

        quality_metrics = quality_metrics_adapter.summarize_ck_results(str(ck_output_path), repo_prefix=clean_name)
        return {
            "Nome": repo_name,
            "Proprietário": owner,
            "Idade": f"{repo_age} anos",
            "Estrelas": node['stargazerCount'],
            "Pull Requests Aceitos": node['pullRequests']['totalCount'],
            "Releases": node['releases']['totalCount'],
            "Linhas de código": code_lines,
            "Linhas de comentário": comment_lines,
            **quality_metrics
        }
    except Exception as error:
        print(f"[!] Falha ao processar {owner}/{repo_name}: {error}")
        return None
    finally:
        remove_repo(str(repo_path))
        remove_repo(str(ck_output_path))


def processData(repositories, max_workers=None, ck_timeout_seconds=None):
    """Processa repositórios em paralelo, excluindo os inválidos para análise CK."""
    garantir_diretorios_trabalho()
    repoList = []

    if not repositories:
        return pd.DataFrame(repoList)

    workers = max(1, int(max_workers or CK_MAX_WORKERS))
    timeout_seconds = ck_timeout_seconds if ck_timeout_seconds is not None else CK_TIMEOUT_SECONDS

    print(f"[..] Processando {len(repositories)} repositorios com {workers} workers de CK...\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_analyze_single_repository, repo, timeout_seconds)
            for repo in repositories
        ]

        for idx, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result is not None:
                repoList.append(result)
            if idx % 10 == 0 or idx == len(futures):
                print(f"  [{idx}/{len(futures)}] finalizados | validos: {len(repoList)}")

    return pd.DataFrame(repoList)

def clean_repo_name(repo_name):
    clean_name = re.sub(r'[^\w\s-]', '_', repo_name)  
    clean_name = clean_name.strip()  
    return clean_name

def calculate_repos_age(creation_date):
    repo_age_timezone = datetime.now(timezone.utc) - pd.to_datetime(creation_date)
    repo_age = repo_age_timezone.days / 365.25
    return round(float(repo_age), 1)

def clone_repo(clone_path, repo_url):
    if os.path.exists(clone_path):
        remove_repo(clone_path)

    try:
        # Clone shallow reduz tráfego e tempo de I/O para análise estática local.
        Repo.clone_from(
            repo_url,
            clone_path,
            depth=1,
            single_branch=True,
            no_tags=True,
        )
    except Exception as e:
        print(f"[!] Erro ao clonar o repositorio: {e}")

def count_lines(repo_path):
    summary = ProjectSummary()
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".java"):
                file_path = os.path.join(root, file)
                analysis = SourceAnalysis.from_file(str(file_path), "java", encoding="utf-8")
                summary.add(analysis)

    code_lines = summary.total_code_count
    comment_lines = summary.total_documentation_count

    return code_lines, comment_lines

def remove_repo(repo_path):
    """Remove um repositório clonado."""
    if not os.path.exists(repo_path):
        return

    try:
        shutil.rmtree(repo_path, onerror=remove_readonly)
    except Exception as e:
        print(f"[!] Erro ao excluir repositorio {repo_path}: {e}")

def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def plotGraphs(df, output_dir=None):
    output_dir = Path(output_dir) if output_dir else REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = ['Média CBO (Classes)', 'Média DIT (Classes)', 'Média LCOM (Classes)']
    graph_paths = []
    idade_numerica = pd.to_numeric(
        df['Idade'].astype(str).str.replace(' anos', '', regex=False),
        errors='coerce',
    )

    def _annotate_spearman(ax, x_series, y_series):
        """Calcula Spearman e anota o subplot."""
        valid = pd.DataFrame({"x": x_series, "y": y_series}).dropna()
        if len(valid) > 2:
            rho, pval = spearmanr(valid["x"], valid["y"])
            ax.annotate(
                f"ρ={rho:.3f}  p={pval:.2g}",
                xy=(0.03, 0.95), xycoords="axes fraction",
                fontsize=8, fontstyle="italic",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
                verticalalignment="top",
            )

    # RQ1: Popularidade (estrelas) vs métricas CK.
    fig, axes = plt.subplots(1, len(metrics), figsize=(16, 5))
    fig.suptitle('RQ1 - Popularidade (Estrelas) vs Métricas de Qualidade', fontweight='bold')
    for i, metric in enumerate(metrics):
        axes[i].scatter(df['Estrelas'], df[metric], color='royalblue', alpha=0.45, s=18)
        axes[i].set_title(metric)
        axes[i].set_xlabel('Estrelas')
        axes[i].set_ylabel(metric)
        axes[i].grid(True, alpha=0.3)
        _annotate_spearman(axes[i], df['Estrelas'], df[metric])
    plt.tight_layout()
    rq1_path = output_dir / 'rq01_popularidade_vs_ck.png'
    fig.savefig(rq1_path, dpi=180)
    plt.close(fig)
    graph_paths.append({'titulo': 'RQ1 - Popularidade vs Qualidade', 'arquivo': rq1_path.name})

    # RQ2: Maturidade (idade) vs métricas CK.
    fig, axes = plt.subplots(1, len(metrics), figsize=(16, 5))
    fig.suptitle('RQ2 - Maturidade (Idade) vs Métricas de Qualidade', fontweight='bold')
    for i, metric in enumerate(metrics):
        axes[i].scatter(idade_numerica, df[metric], color='seagreen', alpha=0.45, s=18)
        axes[i].set_title(metric)
        axes[i].set_xlabel('Idade (anos)')
        axes[i].set_ylabel(metric)
        axes[i].grid(True, alpha=0.3)
        _annotate_spearman(axes[i], idade_numerica, df[metric])
    plt.tight_layout()
    rq2_path = output_dir / 'rq02_maturidade_vs_ck.png'
    fig.savefig(rq2_path, dpi=180)
    plt.close(fig)
    graph_paths.append({'titulo': 'RQ2 - Maturidade vs Qualidade', 'arquivo': rq2_path.name})

    # RQ3: Atividade (releases) vs métricas CK.
    fig, axes = plt.subplots(1, len(metrics), figsize=(16, 5))
    fig.suptitle('RQ3 - Atividade (Releases) vs Métricas de Qualidade', fontweight='bold')
    for i, metric in enumerate(metrics):
        axes[i].scatter(df['Releases'], df[metric], color='darkorange', alpha=0.45, s=18)
        axes[i].set_title(metric)
        axes[i].set_xlabel('Releases')
        axes[i].set_ylabel(metric)
        axes[i].grid(True, alpha=0.3)
        _annotate_spearman(axes[i], df['Releases'], df[metric])
    plt.tight_layout()
    rq3_path = output_dir / 'rq03_atividade_vs_ck.png'
    fig.savefig(rq3_path, dpi=180)
    plt.close(fig)
    graph_paths.append({'titulo': 'RQ3 - Atividade vs Qualidade', 'arquivo': rq3_path.name})

    # RQ4: Tamanho (LOC/Comentários) vs métricas CK.
    fig, axes = plt.subplots(2, len(metrics), figsize=(16, 10))
    fig.suptitle('RQ4 - Tamanho (LOC e Comentários) vs Métricas de Qualidade', fontweight='bold')
    for i, metric in enumerate(metrics):
        axes[0, i].scatter(df['Linhas de código'], df[metric], color='purple', alpha=0.45, s=18)
        axes[0, i].set_title(f'LOC vs {metric}')
        axes[0, i].set_xlabel('Linhas de código')
        axes[0, i].set_ylabel(metric)
        axes[0, i].grid(True, alpha=0.3)
        _annotate_spearman(axes[0, i], df['Linhas de código'], df[metric])

        axes[1, i].scatter(df['Linhas de comentário'], df[metric], color='teal', alpha=0.45, s=18)
        axes[1, i].set_title(f'Comentários vs {metric}')
        axes[1, i].set_xlabel('Linhas de comentário')
        axes[1, i].set_ylabel(metric)
        axes[1, i].grid(True, alpha=0.3)
        _annotate_spearman(axes[1, i], df['Linhas de comentário'], df[metric])

    plt.tight_layout()
    rq4_path = output_dir / 'rq04_tamanho_vs_ck.png'
    fig.savefig(rq4_path, dpi=180)
    plt.close(fig)
    graph_paths.append({'titulo': 'RQ4 - Tamanho vs Qualidade', 'arquivo': rq4_path.name})

    return graph_paths

def generate_html_report(df, graphs, report_path=None):
    report_path = Path(report_path) if report_path else REPORTS_DIR / "report.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # --------- Estatísticas descritivas ---------
    numeric_cols = [
        'Estrelas', 'Releases', 'Linhas de código', 'Linhas de comentário',
        'Média CBO (Classes)', 'Média DIT (Classes)', 'Média LCOM (Classes)',
    ]
    idade_num = pd.to_numeric(
        df['Idade'].astype(str).str.replace(' anos', '', regex=False),
        errors='coerce',
    )
    stats_df = df[numeric_cols].copy()
    stats_df.insert(0, 'Idade (anos)', idade_num)
    summary = stats_df.agg(['mean', 'median', 'std']).round(2)
    summary.index = ['Média', 'Mediana', 'Desvio padrão']

    # --------- Spearman para cada RQ ---------
    spearman_pairs = [
        ('RQ1', 'Estrelas', 'Média CBO (Classes)'),
        ('RQ1', 'Estrelas', 'Média DIT (Classes)'),
        ('RQ1', 'Estrelas', 'Média LCOM (Classes)'),
        ('RQ2', idade_num, 'Média CBO (Classes)'),
        ('RQ2', idade_num, 'Média DIT (Classes)'),
        ('RQ2', idade_num, 'Média LCOM (Classes)'),
        ('RQ3', 'Releases', 'Média CBO (Classes)'),
        ('RQ3', 'Releases', 'Média DIT (Classes)'),
        ('RQ3', 'Releases', 'Média LCOM (Classes)'),
        ('RQ4', 'Linhas de código', 'Média CBO (Classes)'),
        ('RQ4', 'Linhas de código', 'Média DIT (Classes)'),
        ('RQ4', 'Linhas de código', 'Média LCOM (Classes)'),
        ('RQ4', 'Linhas de comentário', 'Média CBO (Classes)'),
        ('RQ4', 'Linhas de comentário', 'Média DIT (Classes)'),
        ('RQ4', 'Linhas de comentário', 'Média LCOM (Classes)'),
    ]
    spearman_rows = []
    for rq, x_col, y_col in spearman_pairs:
        if isinstance(x_col, str):
            x_label = x_col
            x_vals = df[x_col]
        else:
            x_label = 'Idade (anos)'
            x_vals = x_col
        pair = pd.DataFrame({'x': x_vals, 'y': df[y_col]}).dropna()
        if len(pair) > 2:
            rho, pval = spearmanr(pair['x'], pair['y'])
        else:
            rho, pval = float('nan'), float('nan')
        spearman_rows.append({
            'RQ': rq, 'X': x_label, 'Y': y_col,
            'N': len(pair), 'ρ': f'{rho:.3f}', 'p-valor': f'{pval:.3g}',
        })

    # --------- HTML ---------
    html_content = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório de Repositórios Java - Lab02</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; background: #fafafa; }
            h1 { color: #1a237e; }
            h2 { color: #2c3e50; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; }
            table { width: 100%%; border-collapse: collapse; margin-bottom: 25px; }
            th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #ddd; font-size: 13px; }
            th { background-color: #e3f2fd; font-weight: bold; }
            tr:nth-child(even) { background-color: #f7f7f7; }
            .graph { margin-top: 30px; }
            .graph img { max-width: 100%%; height: auto; }
            .stats-table { width: auto; }
            .stats-table td, .stats-table th { padding: 6px 14px; text-align: center; }
            .spearman-table { width: auto; }
            .spearman-table td, .spearman-table th { padding: 6px 14px; text-align: center; }
            .info { color: #555; font-style: italic; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>Relatório — Qualidade Interna de Repositórios Java Populares</h1>
        <p class="info">Amostra: """ + str(len(df)) + """ repositórios analisados com CK</p>

        <h2>Resumo Estatístico</h2>
        <table class="stats-table">
            <thead><tr><th>Medida</th>"""

    for col in summary.columns:
        html_content += f"<th>{col}</th>"
    html_content += "</tr></thead><tbody>"
    for idx, row in summary.iterrows():
        html_content += f"<tr><td><b>{idx}</b></td>"
        for val in row:
            html_content += f"<td>{val}</td>"
        html_content += "</tr>"
    html_content += "</tbody></table>"

    html_content += """
        <h2>Correlação de Spearman</h2>
        <table class="spearman-table">
            <thead><tr><th>RQ</th><th>Variável X</th><th>Variável Y</th><th>N</th><th>ρ</th><th>p-valor</th></tr></thead>
            <tbody>"""
    for sr in spearman_rows:
        html_content += f"<tr><td>{sr['RQ']}</td><td>{sr['X']}</td><td>{sr['Y']}</td><td>{sr['N']}</td><td>{sr['ρ']}</td><td>{sr['p-valor']}</td></tr>"
    html_content += "</tbody></table>"

    html_content += """
        <h2>Dados dos Repositórios</h2>
        <table>
            <thead>
                <tr>
                    <th>Nome</th>
                    <th>Proprietário</th>
                    <th>Idade</th>
                    <th>Estrelas</th>
                    <th>Pull Requests Aceitos</th>
                    <th>Releases</th>
                    <th>Linhas de Código</th>
                    <th>Linhas de Comentário</th>
                    <th>Média CBO (Classes)</th>
                    <th>Média DIT (Classes)</th>
                    <th>Média LCOM (Classes)</th>
                </tr>
            </thead>
            <tbody>
    """

    for _, row in df.iterrows():
        html_content += f"""
        <tr>
            <td>{row['Nome']}</td>
            <td>{row['Proprietário']}</td>
            <td>{row['Idade']}</td>
            <td>{row['Estrelas']}</td>
            <td>{row['Pull Requests Aceitos']}</td>
            <td>{row['Releases']}</td>
            <td>{row['Linhas de código']}</td>
            <td>{row['Linhas de comentário']}</td>
            <td>{row['Média CBO (Classes)']}</td>
            <td>{row['Média DIT (Classes)']}</td>
            <td>{row['Média LCOM (Classes)']}</td>
        </tr>
        """

    html_content += """
            </tbody>
        </table>
    """

    html_content += "<h2>Gráficos de Correlação</h2>"

    for i, graph in enumerate(graphs):
        if isinstance(graph, dict):
            graph_title = graph.get('titulo', f'Gráfico {i + 1}')
            graph_src = graph.get('arquivo', '')
        else:
            graph_title = f'Gráfico {i + 1}'
            graph_src = graph

        html_content += f"""
        <div class="graph">
            <h3>{graph_title}</h3>
            <img src="{graph_src}" alt="{graph_title}">
        </div>
        """

    html_content += """
    </body>
    </html>
    """

    with open(report_path, 'w', encoding='utf-8') as file:
        file.write(html_content)
