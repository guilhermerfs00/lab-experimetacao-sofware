# -*- coding: utf-8 -*-
"""
graphql_adapter.py – Lab05
Executa consultas à API GraphQL do GitHub e mede tempo de resposta e tamanho do payload.

As queries foram projetadas para retornar dados equivalentes aos endpoints REST
correspondentes, permitindo comparação justa entre as duas abordagens.

Cada função retorna um dict com:
    response_time_ms    – latência total da requisição em milissegundos
    response_size_bytes  – tamanho do corpo da resposta em bytes
    http_status          – código HTTP retornado
    success              – True se status == 200 e sem erros GraphQL
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

_TOKEN = os.getenv("GITHUB_TOKEN", "")
_GRAPHQL_URL = "https://api.github.com/graphql"
_HEADERS = {
    "Authorization": f"Bearer {_TOKEN}",
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


# ──────────────────────────────────────────────────────────────────────────────
# Queries GraphQL (equivalentes aos endpoints REST)
# ──────────────────────────────────────────────────────────────────────────────

# Equivalente a GET /repos/{owner}/{repo}
_REPO_INFO_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
    name
    nameWithOwner
    description
    isPrivate
    isFork
    isArchived
    isDisabled
    stargazerCount
    forkCount
    createdAt
    updatedAt
    pushedAt
    url
    sshUrl
    homepageUrl
    defaultBranchRef { name }
    primaryLanguage { name }
    licenseInfo { name key }
    owner {
      login
      ... on User    { name avatarUrl }
      ... on Organization { name avatarUrl }
    }
    issues(states: OPEN)        { totalCount }
    pullRequests(states: OPEN)  { totalCount }
    watchers                    { totalCount }
  }
}
"""

# Equivalente a GET /search/repositories?q=stars:>5000+language:Python
_SEARCH_REPOS_QUERY = """
query($queryStr: String!) {
  search(query: $queryStr, type: REPOSITORY, first: 30) {
    repositoryCount
    edges {
      node {
        ... on Repository {
          id
          name
          nameWithOwner
          description
          isPrivate
          isFork
          isArchived
          stargazerCount
          forkCount
          createdAt
          updatedAt
          url
          homepageUrl
          primaryLanguage { name }
          licenseInfo { name key }
          owner { login }
          issues(states: OPEN)       { totalCount }
          pullRequests(states: OPEN) { totalCount }
          watchers                   { totalCount }
          defaultBranchRef { name }
        }
      }
    }
  }
}
"""

# Equivalente a GET /users/{login}
_USER_PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    id
    login
    name
    email
    bio
    company
    location
    avatarUrl
    websiteUrl
    createdAt
    updatedAt
    followers { totalCount }
    following  { totalCount }
    repositories(privacy: PUBLIC) { totalCount }
    starredRepositories            { totalCount }
    gists(privacy: PUBLIC)         { totalCount }
  }
}
"""

# Equivalente a GET /repos/{owner}/{repo}/issues?state=open&per_page=30
_REPO_ISSUES_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    issues(first: 30, states: OPEN, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes {
        number
        title
        state
        createdAt
        updatedAt
        closedAt
        bodyText
        author { login }
        labels(first: 10) {
          nodes { name color }
        }
        comments { totalCount }
        assignees(first: 5) { nodes { login } }
      }
    }
  }
}
"""


# ──────────────────────────────────────────────────────────────────────────────
# Utilitário interno
# ──────────────────────────────────────────────────────────────────────────────

def _measure(query: str, variables: dict | None = None) -> dict:
    """Executa uma query GraphQL, cronometra e devolve as métricas."""
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    start = time.perf_counter()
    try:
        resp = requests.post(_GRAPHQL_URL, headers=_HEADERS, json=payload, timeout=30)
        elapsed_ms = (time.perf_counter() - start) * 1000
        has_errors = False
        if resp.status_code == 200:
            body = resp.json()
            has_errors = "errors" in body
        return {
            "response_time_ms": round(elapsed_ms, 3),
            "response_size_bytes": len(resp.content),
            "http_status": resp.status_code,
            "success": resp.status_code == 200 and not has_errors,
        }
    except requests.RequestException as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"  [GQL ERROR] {exc}")
        return {
            "response_time_ms": round(elapsed_ms, 3),
            "response_size_bytes": 0,
            "http_status": 0,
            "success": False,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Cenários de consulta (espelham o rest_adapter)
# ──────────────────────────────────────────────────────────────────────────────

def get_repo_info(owner: str, repo: str) -> dict:
    """Metadados completos de um repositório via GraphQL."""
    return _measure(_REPO_INFO_QUERY, {"owner": owner, "name": repo})


def search_repos(language: str = "Python") -> dict:
    """Busca de repositórios populares via GraphQL."""
    return _measure(_SEARCH_REPOS_QUERY, {"queryStr": f"stars:>5000 language:{language}"})


def get_user_profile(login: str) -> dict:
    """Perfil de um usuário GitHub via GraphQL."""
    return _measure(_USER_PROFILE_QUERY, {"login": login})


def get_repo_issues(owner: str, repo: str) -> dict:
    """Issues abertas de um repositório via GraphQL."""
    return _measure(_REPO_ISSUES_QUERY, {"owner": owner, "name": repo})
