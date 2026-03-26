from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import os


@dataclass(frozen=True)
class Settings:
    """Centraliza configuracoes de ambiente e caminhos usados no pipeline do Lab02."""

    token: str
    api_url: str
    ck_jar_path: Path
    repo_base_dir: Path
    reports_dir: Path


def _get_first_env(*names: str) -> Optional[str]:
    """Retorna o primeiro valor de variavel de ambiente nao vazio entre os nomes informados."""

    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip().strip('"').strip("'")
    return None


def load_settings() -> Settings:
    """Carrega variaveis .env e resolve caminhos absolutos para tornar a execucao independente do CWD."""

    load_dotenv()

    root_dir = Path(__file__).resolve().parents[3]
    lab02_dir = root_dir / "Lab02"
    src_dir = lab02_dir / "src"

    token = _get_first_env("TOKEN", "GITHUB_TOKEN") or ""
    api_url = _get_first_env("API_URL", "GITHUB_API_URL") or "https://api.github.com/graphql"
    ck_jar_raw = _get_first_env("CK_REPO_URL", "CK_REPO_PATH")
    
    if ck_jar_raw:
        ck_jar_candidate = Path(ck_jar_raw)
        if ck_jar_candidate.is_absolute():
            ck_jar_path = ck_jar_candidate
        else:
            ck_jar_path = root_dir / ck_jar_candidate
    else:
        ck_jar_path = src_dir / "ck-0.7.1-SNAPSHOT.jar"

    repo_base_dir = src_dir / "repo"
    reports_dir = lab02_dir / "reports"

    return Settings(
        token=token,
        api_url=api_url,
        ck_jar_path=ck_jar_path,
        repo_base_dir=repo_base_dir,
        reports_dir=reports_dir,
    )

