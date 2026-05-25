# -*- coding: utf-8 -*-
"""
repositories_adapter.py - Lab04
Coleta os repositorios mais populares do GitHub via GraphQL.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}


def _run_query(query: str, variables: dict = None, retries: int = 5) -> dict | None:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    for attempt in range(retries):
        try:
            response = requests.post(
                GITHUB_GRAPHQL_URL, json=payload, headers=headers, timeout=60
            )
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Excecao de rede: {e}. Tentativa {attempt + 1}/{retries}.")
            time.sleep(10 * (attempt + 1))
            continue

        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                print(f"[WARN] GraphQL errors: {data['errors']}")
                return None
            return data
        elif response.status_code in (502, 503, 504):
            print(f"[WARN] {response.status_code} - gateway error. Tentativa {attempt + 1}/{retries}.")
            time.sleep(15 * (attempt + 1))
        elif response.status_code == 403:
            print("[WARN] 403 Rate limit. Aguardando 60s...")
            time.sleep(60)
        else:
            print(f"[WARN] HTTP {response.status_code}: {response.text[:200]}. Tentativa {attempt + 1}/{retries}.")
            time.sleep(5)

    return None


REPO_QUERY = """
query($after: String) {
  search(
    query: "stars:>500 language:Java sort:stars"
    type: REPOSITORY
    first: 25
    after: $after
  ) {
    edges {
      node {
        ... on Repository {
          nameWithOwner
          name
          owner { login }
          stargazerCount
          primaryLanguage { name }
          defaultBranchRef { name }
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


def fetch_top_repositories(total: int = 100) -> list[dict]:
    """Retorna lista de repositorios populares do GitHub."""
    repos = []
    cursor = None

    while len(repos) < total:
        variables = {"after": cursor}
        data = _run_query(REPO_QUERY, variables)
        if not data:
            break

        edges = data["data"]["search"]["edges"]
        page_info = data["data"]["search"]["pageInfo"]

        for edge in edges:
            node = edge["node"]
            repos.append({
                "repo": node["nameWithOwner"],
                "owner": node["owner"]["login"],
                "name": node["name"],
                "stars": node["stargazerCount"],
                "language": node["primaryLanguage"]["name"] if node["primaryLanguage"] else "Unknown",
                "default_branch": node["defaultBranchRef"]["name"] if node["defaultBranchRef"] else "main",
            })

        print(f"[OK] {len(repos)}/{total} repositorios coletados...")

        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        time.sleep(1)

    return repos[:total]
