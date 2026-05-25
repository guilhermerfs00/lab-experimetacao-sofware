# -*- coding: utf-8 -*-
"""
commit_adapter.py - Lab04
Coleta commits de um repositorio GitHub via REST API e classifica:
  - is_conventional   : segue o padrao Conventional Commits
  - conventional_type : tipo extraido (feat, fix, docs, etc.)
  - scope             : escopo, se presente
  - is_bug_related    : commit relacionado a bug (via issue vinculada ou keywords)
"""

import os
import re
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

GITHUB_REST_URL = "https://api.github.com"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Regex para detectar Conventional Commits (com ou sem escopo)
# Ex: feat: ...  |  fix(api): ...  |  chore!: ...
CC_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s+.+",
    re.IGNORECASE,
)

# Palavras-chave auxiliares para identificar commits relacionados a bugs
BUG_KEYWORDS = re.compile(
    r"\b(bug|bugs|bugfix|fix bug|fixes bug|error|crash|defect|failure|regression"
    r"|issue|hotfix|critical|exception|traceback|stack overflow)\b",
    re.IGNORECASE,
)


def _get(url: str, params: dict = None, retries: int = 5) -> Optional[dict | list]:
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Excecao de rede: {e}. Tentativa {attempt + 1}/{retries}.")
            time.sleep(10 * (attempt + 1))
            continue

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            # Verificar se é rate limit
            remaining = response.headers.get("X-RateLimit-Remaining", "1")
            if remaining == "0":
                reset_at = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset_at - int(time.time()), 5) + 2
                print(f"[WARN] Rate limit atingido. Aguardando {wait}s...")
                time.sleep(wait)
            else:
                time.sleep(5)
        elif response.status_code == 404:
            return None
        elif response.status_code in (502, 503, 504):
            print(f"[WARN] {response.status_code} gateway error. Tentativa {attempt + 1}/{retries}.")
            time.sleep(10 * (attempt + 1))
        else:
            print(f"[WARN] HTTP {response.status_code}: {response.text[:100]}. Tentativa {attempt + 1}/{retries}.")
            time.sleep(5)

    return None


def _issue_is_bug(owner: str, repo: str, issue_number: int) -> bool:
    """Verifica se uma issue tem label 'bug'."""
    url = f"{GITHUB_REST_URL}/repos/{owner}/{repo}/issues/{issue_number}"
    data = _get(url)
    if not data or isinstance(data, list):
        return False
    labels = [label["name"].lower() for label in data.get("labels", [])]
    return any("bug" in label for label in labels)


def _extract_issue_refs(message: str) -> list[int]:
    """Extrai numeros de issues referenciadas na mensagem do commit."""
    return [int(n) for n in re.findall(r"#(\d+)", message)]


def classify_commit(message: str, owner: str, repo: str) -> dict:
    """Classifica um commit em relacao ao padrao Conventional Commits e bugs."""
    first_line = message.strip().split("\n")[0]

    match = CC_PATTERN.match(first_line)
    is_conventional = match is not None
    conventional_type = match.group("type").lower() if match else None
    scope = match.group("scope") if match else None

    # Detectar relacao com bugs
    # Prioridade 1: issue vinculada com label "bug"
    is_bug_related = False
    bug_source = "nao"

    issue_refs = _extract_issue_refs(message)
    for issue_num in issue_refs:
        if _issue_is_bug(owner, repo, issue_num):
            is_bug_related = True
            bug_source = "issue_label"
            break

    # Prioridade 2: keywords na mensagem (critério auxiliar)
    if not is_bug_related and BUG_KEYWORDS.search(first_line):
        is_bug_related = True
        bug_source = "keyword"

    return {
        "is_conventional": "Sim" if is_conventional else "Não",
        "conventional_type": conventional_type if conventional_type else "Não convencional",
        "scope": scope if scope else "",
        "is_bug_related": "Sim" if is_bug_related else "Não",
        "bug_source": bug_source,
    }


def fetch_commits_for_repo(owner: str, repo: str, branch: str = "main",
                           max_commits: int = 500) -> list[dict]:
    """
    Coleta commits de um repositorio e retorna lista de dicionarios.
    Cada dicionario representa uma linha do dataset final.
    """
    commits = []
    page = 1
    per_page = 100

    print(f"  -> Coletando commits de {owner}/{repo} (branch: {branch})...")

    while len(commits) < max_commits:
        url = f"{GITHUB_REST_URL}/repos/{owner}/{repo}/commits"
        params = {
            "sha": branch,
            "per_page": min(per_page, max_commits - len(commits)),
            "page": page,
        }

        data = _get(url, params=params)
        if not data:
            break
        if not isinstance(data, list) or len(data) == 0:
            break

        for item in data:
            commit_data = item.get("commit", {})
            author_info = commit_data.get("author", {})
            stats = item.get("stats", {})

            message = commit_data.get("message", "")
            classification = classify_commit(message, owner, repo)

            commits.append({
                "repository": f"{owner}/{repo}",
                "commit_hash": item.get("sha", "")[:8],
                "commit_message": message.split("\n")[0][:200],
                "commit_date": author_info.get("date", ""),
                "author": author_info.get("name", ""),
                "files_changed": stats.get("total", 0),
                "additions": stats.get("additions", 0),
                "deletions": stats.get("deletions", 0),
                **classification,
            })

        print(f"     {len(commits)} commits coletados...")

        if len(data) < per_page:
            break
        page += 1
        time.sleep(0.5)

    return commits
