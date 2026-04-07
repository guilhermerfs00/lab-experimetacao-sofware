import base64
import io
import os
import re
import shutil
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv
from git import Repo
from pygount import ProjectSummary, SourceAnalysis
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import quality_metrics_adapter

# Carregar variáveis de ambiente
BASE_DIR = Path(__file__).resolve().parent
LAB02_DIR = BASE_DIR.parent
WORKDIR_DIR = LAB02_DIR / "workdir"
CLONES_DIR = WORKDIR_DIR / "clones"
CK_OUTPUT_DIR = WORKDIR_DIR / "ck_output"
REPORTS_DIR = LAB02_DIR / "reports"

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
REQUEST_TIMEOUT_CONNECT = float(os.environ.get("GITHUB_TIMEOUT_CONNECT", "5"))
REQUEST_TIMEOUT_READ = float(os.environ.get("GITHUB_TIMEOUT_READ", "30"))
REQUEST_MAX_RETRIES = int(os.environ.get("GITHUB_MAX_RETRIES", "4"))
REQUEST_BACKOFF_SECONDS = float(os.environ.get("GITHUB_BACKOFF_SECONDS", "1.5"))

# Limite máximo de caminho para Windows
MAX_PATH_LENGTH = 260


def _build_http_session():
    session = requests.Session()

    retry = Retry(
        total=REQUEST_MAX_RETRIES,
        connect=REQUEST_MAX_RETRIES,
        read=REQUEST_MAX_RETRIES,
        backoff_factor=REQUEST_BACKOFF_SECONDS,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["POST"]),
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


HTTP_SESSION = _build_http_session()


def garantir_diretorios_trabalho():
    """Cria a estrutura de pastas usada durante a execução do Lab02."""
    for path in (WORKDIR_DIR, CLONES_DIR, CK_OUTPUT_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)

def fetchRepositories(start, end):
    """Faz a requisição GraphQL com paginação para obter repositórios em intervalos definidos."""
    allRepos = []
    cursor = None
    totalRepos = max(0, end - start)
    if totalRepos == 0:
        return []

    base_batch_size = int(os.environ.get("GITHUB_BATCH_SIZE", "20"))
    batch_size = max(1, min(100, base_batch_size))

    query = """
    query($first: Int!, $after: String) {
      search(query: "stars:>10000 language:Java -topic:tutorial -topic:learning -topic:javaguide", type: REPOSITORY, first: $first, after: $after) {
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

    chamada = 0
    has_next_page = True

    while len(allRepos) < totalRepos and has_next_page:
        chamada += 1
        faltantes = totalRepos - len(allRepos)
        first = min(batch_size, faltantes)
        print(f"🔄 Buscando repositórios... (Chamada {chamada}, coletados {len(allRepos)}/{totalRepos})")

        payload = {
            "query": query,
            "variables": {
                "first": first,
                "after": cursor,
            },
        }

        data = _post_graphql_with_retry(payload)
        if data is None:
            print("⚠ Coleta interrompida por falhas repetidas na API do GitHub.")
            break

        search_data = ((data.get("data") or {}).get("search") or {})
        repositories = search_data.get("edges") or []

        if not repositories:
            print("⚠ Nenhum repositório retornado nesta página.")
            break

        # Mantém o filtro educacional para não alterar o comportamento atual.
        filtered_repos = [
            repo for repo in repositories
            if not is_educational(repo.get("node", {}))
        ]

        allRepos.extend(filtered_repos)
        page_info = search_data.get("pageInfo") or {}
        has_next_page = bool(page_info.get("hasNextPage"))
        cursor = page_info.get("endCursor") if has_next_page else None

        print(f"✅ Chamada {chamada} concluída ({len(allRepos)}/{totalRepos} repositórios coletados)\n")

    return allRepos[:totalRepos]


def _post_graphql_with_retry(payload):
    for attempt in range(1, REQUEST_MAX_RETRIES + 1):
        try:
            response = HTTP_SESSION.post(
                GITHUB_GRAPHQL_URL,
                json=payload,
                headers=headers,
                timeout=(REQUEST_TIMEOUT_CONNECT, REQUEST_TIMEOUT_READ),
            )
        except requests.exceptions.RequestException as error:
            espera = REQUEST_BACKOFF_SECONDS * attempt
            print(f"⚠ Erro de conexão com GitHub: {error}. Tentativa {attempt}/{REQUEST_MAX_RETRIES} em {espera:.1f}s...")
            time.sleep(espera)
            continue

        if response.status_code == 200:
            data = response.json()
            graphql_errors = data.get("errors")
            if graphql_errors:
                espera = REQUEST_BACKOFF_SECONDS * attempt
                print(f"⚠ Erro GraphQL: {graphql_errors}. Tentativa {attempt}/{REQUEST_MAX_RETRIES} em {espera:.1f}s...")
                time.sleep(espera)
                continue
            return data

        if response.status_code in (401, 403):
            print(f"⚠ Erro de autenticação/permissão ({response.status_code}). Verifique TOKEN e escopo do GitHub token.")
            return None

        espera = REQUEST_BACKOFF_SECONDS * attempt
        print(f"⚠ Erro HTTP {response.status_code}: {response.text[:300]}. Tentativa {attempt}/{REQUEST_MAX_RETRIES} em {espera:.1f}s...")
        time.sleep(espera)

    return None

def is_educational(repo):
    keywords = ["tutorial", "example", "guide", "learning", "course", "demo", "how-to"]

    name = repo.get("name", "").lower()
    description = (repo.get("description") or "").lower()

    return any(keyword in name or keyword in description for keyword in keywords)

def has_java_files(repo_path):
    print(f"Verificando arquivos em: {repo_path}")
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".java"):
                print("✅ Arquivo .java encontrado!")
                return True
    print("❌ Nenhum arquivo .java encontrado.")
    return False

def processData(repositories):
    """Processa os dados da API para um DataFrame, excluindo repositórios sem arquivos .java."""
    repoList = []
    garantir_diretorios_trabalho()

    print("🔄 Coletando dados dos repositórios...\n")

    for repo in repositories:
        node = repo['node']
        repo_age = calculate_repos_age(node['createdAt'])

        repo_name = node['name']
        if len(repo_name) > 100:  
            print(f"❌ Repositório {repo_name} ignorado (nome muito longo)")
            continue
        clean_name = clean_repo_name(repo_name)

        repo_url = f"https://github.com/{node['owner']['login']}/{repo_name}.git"

        repo_path = CLONES_DIR / clean_name
        ck_output_path = CK_OUTPUT_DIR / clean_name

        clone_repo(str(repo_path), repo_url)

        if repo_path.exists() and has_java_files(str(repo_path)):
            code_lines, comment_lines = count_lines(repo_path)
            quality_metrics_adapter.run_ck(str(repo_path), str(ck_output_path), ck_path)
            quality_metrics = quality_metrics_adapter.summarize_ck_results(str(ck_output_path), repo_prefix=clean_name)
            remove_repo(str(repo_path))
            remove_repo(str(ck_output_path))

            repoList.append({
                "Nome": node['name'],
                "Proprietário": node['owner']['login'],
                "Idade": f"{repo_age} anos",
                "Estrelas": node['stargazerCount'],
                "Pull Requests Aceitos": node['pullRequests']['totalCount'],
                "Releases": node['releases']['totalCount'],
                "Linhas de código": code_lines,
                "Linhas de comentário": comment_lines,
                **quality_metrics
            })
        else:
            print(f"❌ Repositório {node['name']} ignorado (não contém arquivos .java)")


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
        print(f"⚠ Erro ao clonar o repositório: {e}")

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
        print(f"✅ Repositório {repo_path} removido com sucesso!")
    except Exception as e:
        print(f"⚠ Erro ao excluir repositório {repo_path}: {e}")

def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def plotGraphs(df, output_dir=None):
    output_dir = Path(output_dir) if output_dir else REPORTS_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    metrics = ['Média CBO (Classes)', 'Média DIT (Classes)', 'Média LCOM (Classes)']
    graph_paths = []

    fig, axes = plt.subplots(2, len(metrics), figsize=(15, 10))
    fig.suptitle('Popularidade vs Métricas de Qualidade e Maturidade vs Métricas de Qualidade')

    for i, metric in enumerate(metrics):
        ax1 = axes[0, i]
        ax1.scatter(df['Estrelas'], df[metric], color='blue', alpha=0.5)
        ax1.set_title(f'Popularidade vs {metric}')
        ax1.set_xlabel('Estrelas')
        ax1.set_ylabel(metric)
        ax1.grid(True)

        ax2 = axes[1, i]
        ax2.scatter(df['Idade'], df[metric], color='green', alpha=0.5)
        ax2.set_title(f'Maturidade vs {metric}')
        ax2.set_xlabel('Idade (anos)')
        ax2.set_ylabel(metric)
        ax2.grid(True)

    for i in range(len(metrics)):
        svg_output = io.StringIO()
        fig.savefig(svg_output, format='svg')
        svg_output.seek(0)

        svg_content = svg_output.getvalue()
        encoded_svg = base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')
        
        graph_paths.append(f"data:image/svg+xml;base64,{encoded_svg}")

    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    plt.close(fig)

    return graph_paths

def generate_html_report(df, graphs, report_path=None):
    report_path = Path(report_path) if report_path else REPORTS_DIR / "report.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    html_content = """
    <html>
    <head>
        <title>Relatório de Repositórios</title>
        <style>
            body { font-family: Arial, sans-serif; }
            h1 { color: #2c3e50; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
            .graph { width: 100%; height: 400px; margin-top: 30px; }
        </style>
    </head>
    <body>
        <h1>Relatório de Repositórios GitHub</h1>
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
    
    html_content += "<h2>Gráficos</h2>"
    
    for i, graph in enumerate(graphs):
        html_content += f"""
        <div class="graph">
            <h3>Gráfico {i + 1}</h3>
            <img src="{graph}" alt="Gráfico {i + 1}">
        </div>
        """
    
    html_content += """
    </body>
    </html>
    """
    
    with open(report_path, 'w', encoding='utf-8') as file:
        file.write(html_content)
