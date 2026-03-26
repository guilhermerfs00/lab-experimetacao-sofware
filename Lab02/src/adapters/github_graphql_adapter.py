import json
import time
from typing import Dict, List, Optional

import requests

from config.settings import Settings


def _build_headers(token: str) -> Dict[str, str]:
    """Monta headers HTTP usados na autenticacao GraphQL."""

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _build_search_query(batch_size: int, cursor: Optional[str]) -> str:
    """Monta a query GraphQL com paginacao por cursor para buscar repositorios Java populares."""

    return f"""
    {{
      search(query: "stars:>10000 language:Java -topic:tutorial -topic:learning -topic:javaguide", type: REPOSITORY, first: {batch_size}, after: {json.dumps(cursor) if cursor else "null"}) {{
        edges {{
          node {{
            ... on Repository {{
              name
              owner {{ login }}
              createdAt
              updatedAt
              stargazerCount
              description
              primaryLanguage {{ name }}
              pullRequests(states: MERGED) {{ totalCount }}
              releases {{ totalCount }}
              openIssues: issues(states: OPEN) {{ totalCount }}
              closedIssues: issues(states: CLOSED) {{ totalCount }}
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


def _is_educational(repo_node: Dict) -> bool:
    """Filtra repositos de tutorial/guia para manter foco em projetos de producao."""

    keywords = ["tutorial", "example", "guide", "learning", "course", "demo", "how-to"]
    name = (repo_node.get("name") or "").lower()
    description = (repo_node.get("description") or "").lower()
    return any(keyword in name or keyword in description for keyword in keywords)


def fetch_repositories(start: int, end: int, settings: Settings, quiet: bool = False) -> List[Dict]:
    """Busca repositorios no GitHub com retry simples e retorna lista de edges filtradas."""

    total_repos = max(end - start, 0)
    if total_repos == 0:
        return []

    all_repositories: List[Dict] = []
    cursor: Optional[str] = None
    batch_size = 20
    num_batches = total_repos // batch_size
    if total_repos % batch_size != 0:
        num_batches += 1

    headers = _build_headers(settings.token)

    for batch in range(num_batches):
        if not quiet:
            print(f"Buscando repositorios... ({batch + 1}/{num_batches})")

        query = _build_search_query(batch_size=batch_size, cursor=cursor)

        for attempt in range(3):
            response = requests.post(
                settings.api_url,
                json={"query": query},
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                payload = response.json()
                search_data = payload.get("data", {}).get("search", {})
                repositories = search_data.get("edges", [])

                filtered_repositories = [
                    repo for repo in repositories if not _is_educational(repo.get("node", {}))
                ]
                all_repositories.extend(filtered_repositories)

                page_info = search_data.get("pageInfo", {})
                cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
                break

            if attempt < 2:
                time.sleep(5)
            elif not quiet:
                print(f"Falha na chamada GraphQL: {response.status_code} - {response.text}")

    return all_repositories[:total_repos]

