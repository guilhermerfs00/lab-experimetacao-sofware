import requests
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()
github_token = os.getenv("GITHUB_TOKEN")

if not github_token:
    raise ValueError("Token do GitHub não encontrado. Verifique o arquivo .env.")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

headers = {
    "Authorization": f"Bearer {github_token}",
    "Content-Type": "application/json"
}


def buscandoRepositorios():
    todos_repositorios = []
    cursor_paginacao   = None
    total_repositorios = 1000
    tamanho_lote       = 5
    total_lotes        = total_repositorios // tamanho_lote

    for indice_lote in range(total_lotes):
        print(f"Buscando repositórios... (Chamada {indice_lote + 1}/{total_lotes})")

        query = f"""
        {{
          search(query: "stars:>10000 sort:stars", type: REPOSITORY, first: {tamanho_lote}, after: {json.dumps(cursor_paginacao) if cursor_paginacao else "null"}) {{
            edges {{
              node {{
                ... on Repository {{
                  name
                  owner {{ login }}
                  createdAt
                  updatedAt
                  stargazerCount
                  primaryLanguage {{ name }}
                  pullRequests(states: MERGED) {{ totalCount }}
                  releases {{ totalCount }}
                  totalIssues: issues {{ totalCount }}
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

        resposta = requests.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query},
            headers=headers,
            timeout=30
        )

        dados_resposta = resposta.json()
        repositorios_lote = dados_resposta['data']['search']['edges']
        todos_repositorios.extend(repositorios_lote)

        info_paginacao = dados_resposta['data']['search']['pageInfo']
        cursor_paginacao = info_paginacao["endCursor"] if info_paginacao["hasNextPage"] else None

        print(f"({len(todos_repositorios)}/{total_repositorios} repositórios coletados)")

        time.sleep(1)

    return todos_repositorios
