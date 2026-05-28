# -*- coding: utf-8 -*-
"""
rest_adapter.py – Lab05
Adaptador para chamadas à GitHub REST API.
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

_TOKEN = os.getenv("GITHUB_TOKEN", "")
_BASE  = "https://api.github.com"
_HEADERS = {
    "Authorization": f"Bearer {_TOKEN}",
    "Accept":        "application/vnd.github+json",
    "Cache-Control": "no-cache",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _get(url: str, params: dict | None = None) -> requests.Response:
    return requests.get(url, headers=_HEADERS, params=params, timeout=30)


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 1 – repo_info: metadados de um repositório
# ──────────────────────────────────────────────────────────────────────────────
def repo_info(owner: str, repo: str) -> requests.Response:
    return _get(f"{_BASE}/repos/{owner}/{repo}")


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 2 – search_repos: busca de repositórios por linguagem
# ──────────────────────────────────────────────────────────────────────────────
def search_repos(language: str, per_page: int = 10) -> requests.Response:
    return _get(
        f"{_BASE}/search/repositories",
        params={"q": f"language:{language} stars:>1000", "sort": "stars", "per_page": per_page},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 3 – user_profile: perfil de um usuário
# ──────────────────────────────────────────────────────────────────────────────
def user_profile(login: str) -> requests.Response:
    return _get(f"{_BASE}/users/{login}")


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 4 – repo_issues: issues abertas de um repositório
# ──────────────────────────────────────────────────────────────────────────────
def repo_issues(owner: str, repo: str, per_page: int = 10) -> requests.Response:
    return _get(
        f"{_BASE}/repos/{owner}/{repo}/issues",
        params={"state": "open", "per_page": per_page},
    )
