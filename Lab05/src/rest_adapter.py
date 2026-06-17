# -*- coding: utf-8 -*-
"""
rest_adapter.py – Lab05
Executa chamadas à API REST do GitHub e mede tempo de resposta e tamanho do payload.

Cada função retorna um dict com:
    response_time_ms   – latência total da requisição em milissegundos
    response_size_bytes – tamanho do corpo da resposta em bytes
    http_status         – código HTTP retornado
    success             – True se status == 200
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

_TOKEN = os.getenv("GITHUB_TOKEN", "")
_BASE_URL = "https://api.github.com"
_HEADERS = {
    "Authorization": f"Bearer {_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    # Desabilita cache de proxy para medir latência real
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# ──────────────────────────────────────────────────────────────────────────────
# Utilitário interno
# ──────────────────────────────────────────────────────────────────────────────

def _measure(url: str, params: dict | None = None) -> dict:
    """Faz GET, cronometra a requisição e devolve as métricas."""
    start = time.perf_counter()
    try:
        resp = requests.get(url, headers=_HEADERS, params=params, timeout=30)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "response_time_ms": round(elapsed_ms, 3),
            "response_size_bytes": len(resp.content),
            "http_status": resp.status_code,
            "success": resp.status_code == 200,
        }
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"  [REST ERROR] {exc}")
        return {
            "response_time_ms": round(elapsed_ms, 3),
            "response_size_bytes": 0,
            "http_status": 0,
            "success": False,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Cenários de consulta
# ──────────────────────────────────────────────────────────────────────────────

def get_repo_info(owner: str, repo: str) -> dict:
    """GET /repos/{owner}/{repo} — metadados completos de um repositório."""
    return _measure(f"{_BASE_URL}/repos/{owner}/{repo}")


def search_repos(language: str = "Python", per_page: int = 30) -> dict:
    """GET /search/repositories — busca de repositórios populares."""
    return _measure(
        f"{_BASE_URL}/search/repositories",
        params={"q": f"stars:>5000 language:{language}", "sort": "stars", "per_page": per_page},
    )


def get_user_profile(login: str) -> dict:
    """GET /users/{login} — perfil de um usuário GitHub."""
    return _measure(f"{_BASE_URL}/users/{login}")


def get_repo_issues(owner: str, repo: str, per_page: int = 30) -> dict:
    """GET /repos/{owner}/{repo}/issues — issues abertas de um repositório."""
    return _measure(
        f"{_BASE_URL}/repos/{owner}/{repo}/issues",
        params={"state": "open", "per_page": per_page},
    )
