# -*- coding: utf-8 -*-
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise ValueError("Erro: O token do GitHub nao foi encontrado. Verifique o arquivo .env.")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

def fetch_top_repositories(total: int = 200, batch_size: int = 25) -> list[dict]:
    """Busca os repositorios mais populares do GitHub (ordenados por estrelas)."""
    all_repos = []
    cursor = None
    num_batches = total // batch_size

    for batch in range(num_batches):
        print(f"[INFO] Buscando repositorios... (Chamada {batch + 1}/{num_batches})")

        query = f"""
        {{
          search(query: "stars:>10000 sort:stars-desc", type: REPOSITORY, first: {batch_size}, after: {json.dumps(cursor) if cursor else "null"}) {{
            edges {{
              node {{
                ... on Repository {{
                  nameWithOwner
                  name
                  owner {{ login }}
                  stargazerCount
                  pullRequests(states: [MERGED, CLOSED]) {{ totalCount }}
                }}
              }}
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
        }}
        """

        for attempt in range(3):
            response = requests.post(GITHUB_GRAPHQL_URL, json={"query": query}, headers=headers)
            if response.status_code == 200:
                data = response.json()
                edges = data["data"]["search"]["edges"]
                all_repos.extend(edges)
                page_info = data["data"]["search"]["pageInfo"]
                cursor = page_info["endCursor"] if page_info["hasNextPage"] else None
                print(f"[OK] Chamada {batch + 1}/{num_batches} concluida. ({len(all_repos)}/{total} repos coletados)")
                break
            else:
                print(f"[WARN] Erro {response.status_code}: {response.text}. Tentativa {attempt + 1}/3...")
                time.sleep(5)

    # Filter repos with at least 100 PRs (MERGED + CLOSED)
    filtered = [
        r for r in all_repos
        if r["node"].get("pullRequests", {}).get("totalCount", 0) >= 100
    ]
    print(f"\n[OK] {len(filtered)} repositorios com pelo menos 100 PRs (MERGED+CLOSED) encontrados.\n")
    return filtered
