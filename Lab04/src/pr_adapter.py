# -*- coding: utf-8 -*-
"""
pr_adapter.py - Lab04
Coleta Pull Requests (MERGED e CLOSED) de repositórios GitHub via GraphQL.
Classifica o título do PR segundo o padrão Conventional Commits e registra
métricas de tempo de merge, reviews e tamanho para análise no Power BI.

Unidade de análise: Pull Request
Questão central:
  PRs com títulos no padrão Conventional Commits têm maior taxa de merge?
"""

import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

# ──────────────────────────────────────────────────────────────────────────────
# Regex – Conventional Commits no título do PR
# Aceita: feat:, fix(api):, chore!:, etc.
# ──────────────────────────────────────────────────────────────────────────────
CC_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s+.+",
    re.IGNORECASE,
)


# ──────────────────────────────────────────────────────────────────────────────
# GraphQL
# ──────────────────────────────────────────────────────────────────────────────
PR_QUERY = """
query($owner: String!, $name: String!, $states: [PullRequestState!], $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(
      states: $states
      first: 50
      after: $after
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      edges {
        node {
          number
          title
          state
          createdAt
          closedAt
          mergedAt
          additions
          deletions
          changedFiles
          commits { totalCount }
          comments { totalCount }
          reviews { totalCount }
          author { login }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


def _run_query(query: str, variables: dict, retries: int = 5) -> Optional[dict]:
    payload = {"query": query, "variables": variables}

    for attempt in range(retries):
        try:
            resp = requests.post(
                GITHUB_GRAPHQL_URL, json=payload, headers=headers, timeout=60
            )
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Rede: {e}. Tentativa {attempt + 1}/{retries}.")
            time.sleep(10 * (attempt + 1))
            continue

        if resp.status_code == 200:
            data = resp.json()
            if "errors" in data:
                print(f"[WARN] GraphQL errors: {data['errors']}")
                return None
            return data
        elif resp.status_code in (502, 503, 504):
            print(f"[WARN] {resp.status_code}. Tentativa {attempt + 1}/{retries}.")
            time.sleep(15 * (attempt + 1))
        elif resp.status_code == 403:
            print("[WARN] Rate limit. Aguardando 60s...")
            time.sleep(60)
        else:
            print(f"[WARN] HTTP {resp.status_code}. Tentativa {attempt + 1}/{retries}.")
            time.sleep(5)

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Classificação de Conventional Commits no título
# ──────────────────────────────────────────────────────────────────────────────
def _classify_title(title: str) -> dict:
    """Classifica o título do PR segundo o padrão Conventional Commits."""
    match = CC_PATTERN.match(title.strip())
    if match:
        return {
            "title_is_conventional": "Sim",
            "conventional_type": match.group("type").lower(),
            "scope": match.group("scope") or "",
            "is_breaking": "Sim" if match.group("breaking") else "Não",
        }
    return {
        "title_is_conventional": "Não",
        "conventional_type": "Não convencional",
        "scope": "",
        "is_breaking": "Não",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Parser de PR
# ──────────────────────────────────────────────────────────────────────────────
def _parse_pr(node: dict, owner: str, repo: str) -> Optional[dict]:
    """Extrai e calcula as métricas de um nó de PR."""
    created_str = node.get("createdAt")
    merged_str = node.get("mergedAt")
    closed_str = node.get("closedAt")
    state = node.get("state", "")

    if not created_str:
        return None

    created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))

    # Tempo até fechamento (merge ou rejeição)
    end_str = merged_str if state == "MERGED" else closed_str
    time_to_close_hours = None
    if end_str:
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        time_to_close_hours = round((end_dt - created_dt).total_seconds() / 3600.0, 2)

    title = node.get("title", "")
    classification = _classify_title(title)
    author_node = node.get("author") or {}

    return {
        "repository": f"{owner}/{repo}",
        "pr_number": node.get("number"),
        "pr_title": title[:300],
        "pr_state": state,
        "is_merged": "Sim" if state == "MERGED" else "Não",
        "created_at": created_str,
        "merged_at": merged_str or "",
        "closed_at": closed_str or "",
        "time_to_close_hours": time_to_close_hours,
        "commits_count": node.get("commits", {}).get("totalCount", 0),
        "review_count": node.get("reviews", {}).get("totalCount", 0),
        "comment_count": node.get("comments", {}).get("totalCount", 0),
        "additions": node.get("additions", 0),
        "deletions": node.get("deletions", 0),
        "changed_files": node.get("changedFiles", 0),
        "author": author_node.get("login", ""),
        **classification,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Coleta de PRs de um repositório
# ──────────────────────────────────────────────────────────────────────────────
def fetch_prs_for_repo(owner: str, repo: str, max_prs: int = 200) -> list[dict]:
    """
    Coleta PRs MERGED e CLOSED de um repositório.
    Retorna lista de dicionários prontos para o dataset.
    """
    prs: list[dict] = []

    for state in ["MERGED", "CLOSED"]:
        cursor = None
        per_state = max_prs // 2  # metade merged, metade closed

        while len([p for p in prs if p["pr_state"] == state]) < per_state:
            data = _run_query(PR_QUERY, {
                "owner": owner,
                "name": repo,
                "states": [state],
                "after": cursor,
            })
            if not data:
                break

            pr_data = (
                data.get("data", {})
                    .get("repository", {})
                    .get("pullRequests", {})
            )
            edges = pr_data.get("edges", [])
            page_info = pr_data.get("pageInfo", {})

            if not edges:
                break

            for edge in edges:
                parsed = _parse_pr(edge["node"], owner, repo)
                if parsed:
                    prs.append(parsed)

            if not page_info.get("hasNextPage"):
                break
            cursor = page_info["endCursor"]
            time.sleep(0.3)

    return prs
