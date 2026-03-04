import requests
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    raise ValueError("Token do GitHub não encontrado. Verifique o arquivo .env.")

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}


def fetchRepositories():
    allRepos   = []
    cursor     = None
    totalRepos = 1000
    batchSize  = 1
    numBatches = totalRepos // batchSize

    for batch in range(numBatches):
        print(f"Buscando repositórios... (Chamada {batch + 1}/{numBatches})")

        query = f"""
        {{
          search(query: "stars:>10000 sort:stars", type: REPOSITORY, first: {batchSize}, after: {json.dumps(cursor) if cursor else "null"}) {{
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

        for attempt in range(3):
            response = requests.post(
                GITHUB_GRAPHQL_URL,
                json={"query": query},
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                if "errors" in data:
                    print(f"Erro GraphQL: {data['errors']}")
                    time.sleep(5)
                    continue

                repositories = data['data']['search']['edges']

                if not repositories:
                    print("Nenhum repositório encontrado nesta chamada.")
                    break

                allRepos.extend(repositories)

                pageInfo = data['data']['search']['pageInfo']
                cursor = pageInfo["endCursor"] if pageInfo["hasNextPage"] else None

                print(f"Chamada {batch + 1}/{numBatches} concluída. ({len(allRepos)}/{totalRepos} repositórios coletados)")

                if not pageInfo["hasNextPage"]:
                    print("Sem mais páginas disponíveis.")
                    return allRepos

                time.sleep(1)
                break

            elif response.status_code == 403:
                print(f"Rate limit atingido. Aguardando 60 segundos... (Tentativa {attempt + 1}/3)")
                time.sleep(60)
            else:
                print(f"Erro {response.status_code}: {response.text}. Tentativa {attempt + 1}/3...")
                time.sleep(5)
        else:
            print(f"Falha na chamada {batch + 1} após 3 tentativas. Abortando.")
            break

    return allRepos
