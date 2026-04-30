# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"


def _run_query(query: str, variables: dict = None, retries: int = 5) -> dict | None:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables  # type: ignore[assignment]

    for attempt in range(retries):
        try:
            response = requests.post(GITHUB_GRAPHQL_URL, json=payload, headers=headers, timeout=60)
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Excecao de rede: {e}. Tentativa {attempt + 1}/{retries}. Aguardando...")
            time.sleep(10 * (attempt + 1))
            continue

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as e:
                print(f"[WARN] Erro ao decodificar JSON: {e}. Tentativa {attempt + 1}/{retries}.")
                time.sleep(5)
                continue
            if "errors" in data:
                print(f"[WARN] GraphQL errors: {data['errors']}")
                return None
            return data
        elif response.status_code in (502, 503, 504):
            print(f"[WARN] {response.status_code} - gateway error, tentativa {attempt + 1}/{retries}. Aguardando...")
            time.sleep(15 * (attempt + 1))
        elif response.status_code == 403:
            print(f"[WARN] 403 Rate limit. Aguardando 60s...")
            time.sleep(60)
        else:
            print(f"[WARN] Erro {response.status_code}: {response.text[:200]}. Tentativa {attempt + 1}/{retries}...")
            time.sleep(5)
    return None


# GraphQL query to fetch PRs from a repository with all required metrics
PR_QUERY = """
query($owner: String!, $name: String!, $states: [PullRequestState!], $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: $states, first: 50, after: $after, orderBy: {field: CREATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          state
          createdAt
          closedAt
          mergedAt
          bodyText
          additions
          deletions
          changedFiles
          participants { totalCount }
          comments { totalCount }
          reviews { totalCount }
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


def _parse_pr(node: dict) -> dict | None:
    """Extrai e calcula as metricas de um PR."""
    created_at_str = node.get("createdAt")
    merged_at_str = node.get("mergedAt")
    closed_at_str = node.get("closedAt")
    state = node.get("state")  # MERGED or CLOSED

    if not created_at_str:
        return None

    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

    # Ultima atividade: mergedAt se MERGED, senao closedAt
    last_activity_str = merged_at_str if state == "MERGED" else closed_at_str
    if not last_activity_str:
        return None

    last_activity = datetime.fromisoformat(last_activity_str.replace("Z", "+00:00"))
    analysis_time_hours = (last_activity - created_at).total_seconds() / 3600.0

    # Filtrar PRs com menos de 1 hora de analise (automatizados)
    if analysis_time_hours < 1.0:
        return None

    review_count = node.get("reviews", {}).get("totalCount", 0)
    # Filtrar PRs sem nenhuma revisao
    if review_count < 1:
        return None

    body = node.get("bodyText") or ""
    description_length = len(body)

    return {
        "number": node.get("number"),
        "state": state,
        "created_at": created_at_str,
        "last_activity": last_activity_str,
        "analysis_time_hours": round(analysis_time_hours, 2),
        # Tamanho
        "changed_files": node.get("changedFiles", 0),
        "additions": node.get("additions", 0),
        "deletions": node.get("deletions", 0),
        "total_lines_changed": node.get("additions", 0) + node.get("deletions", 0),
        # Descricao
        "description_length": description_length,
        # Interacoes
        "participants": node.get("participants", {}).get("totalCount", 0),
        "comments": node.get("comments", {}).get("totalCount", 0),
        # Revisoes
        "review_count": review_count,
    }


def fetch_prs_for_repo(owner: str, name: str, max_prs: int = 200) -> list[dict]:
    """Coleta PRs (MERGED + CLOSED) de um repositorio aplicando os filtros definidos."""
    prs = []
    fetched = 0

    for state in ["MERGED", "CLOSED"]:
        cursor = None
        while fetched < max_prs:
            variables = {
                "owner": owner,
                "name": name,
                "states": [state],
                "after": cursor
            }
            data = _run_query(PR_QUERY, variables)
            if not data:
                break

            pr_data = data.get("data", {}).get("repository", {}).get("pullRequests", {})
            edges = pr_data.get("edges", [])

            for edge in edges:
                node = edge.get("node", {})
                parsed = _parse_pr(node)
                if parsed:
                    parsed["repo"] = f"{owner}/{name}"
                    prs.append(parsed)
                    fetched += 1
                    if fetched >= max_prs:
                        break

            page_info = pr_data.get("pageInfo", {})
            if not page_info.get("hasNextPage") or fetched >= max_prs:
                break
            cursor = page_info["endCursor"]
            time.sleep(0.5)  # Be kind to the API

    return prs

