from pathlib import Path
import re
import shutil
import stat
import os
import time

from git import Repo
from pygount import ProjectSummary, SourceAnalysis


def clean_repo_name(repo_name: str) -> str:
    """Normaliza o nome para uso seguro como pasta no sistema de arquivos."""

    clean_name = re.sub(r"[^\w\s-]", "_", repo_name)
    return clean_name.strip()


def build_repo_url(owner: str, repo_name: str) -> str:
    """Constroi URL HTTPS para clonagem do repositorio no GitHub."""

    return f"https://github.com/{owner}/{repo_name}.git"


def clone_repo(clone_path: Path, repo_url: str) -> None:
    """Clona o repositorio no caminho informado, removendo copia anterior quando necessario."""

    if clone_path.exists():
        remove_path(clone_path)
    clone_path.parent.mkdir(parents=True, exist_ok=True)
    Repo.clone_from(repo_url, str(clone_path))


def has_java_files(repo_path: Path) -> bool:
    """Verifica se ha ao menos um arquivo .java para evitar analise CK em repositorios nao Java."""

    for _, _, files in os.walk(repo_path):
        if any(file.endswith(".java") for file in files):
            return True
    return False


def count_java_lines(repo_path: Path) -> tuple[int, int]:
    """Conta linhas de codigo e comentario em arquivos Java usando pygount."""

    summary = ProjectSummary()
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".java"):
                file_path = Path(root) / file
                analysis = SourceAnalysis.from_file(str(file_path), "java", encoding="utf-8")
                summary.add(analysis)

    return summary.total_code_count, summary.total_documentation_count


def _remove_readonly(func, path, _exc_info) -> None:
    """Callback do rmtree para alterar permissao antes de remover arquivos bloqueados."""

    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_path(path: Path) -> None:
    """Remove diretorios e trata atributos read-only comuns em ambiente Windows com retry."""

    if not path.exists():
        return
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path, onerror=_remove_readonly)
            return
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                pass

