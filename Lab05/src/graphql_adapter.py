# -*- coding: utf-8 -*-
"""
graphql_adapter.py – Lab05
Adaptador para chamadas à GitHub GraphQL API v4.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

_TOKEN   = os.getenv("GITHUB_TOKEN", "")
_GRAPHQL = "https://api.github.com/graphql"
_HEADERS = {
    "Authorization": f"Bearer {_TOKEN}",
    "Content-Type":  "application/json",
    "Cache-Control": "no-cache",
}


def _query(payload: dict) -> requests.Response:
    return requests.post(_GRAPHQL, headers=_HEADERS, json=payload, timeout=30)


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 1 – repo_info: metadados de um repositório
# ──────────────────────────────────────────────────────────────────────────────
def repo_info(owner: str, repo: str) -> requests.Response:
    return _query({
        "query": """
        query($owner: String!, $repo: String!) {
          repository(owner: $owner, name: $repo) {
            name
            description
            stargazerCount
            forkCount
            openIssues: issues(states: OPEN) { totalCount }
            primaryLanguage { name }
            createdAt
            updatedAt
            licenseInfo { name }
            url
          }
        }
        """,
        "variables": {"owner": owner, "repo": repo},
    })


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 2 – search_repos: busca de repositórios por linguagem
# ──────────────────────────────────────────────────────────────────────────────
def search_repos(language: str, per_page: int = 10) -> requests.Response:
    return _query({
        "query": """
        query($q: String!, $n: Int!) {
          search(query: $q, type: REPOSITORY, first: $n) {
            repositoryCount
            edges {
              node {
                ... on Repository {
                  name
                  stargazerCount
                  forkCount
                  primaryLanguage { name }
                  description
                  url
                }
              }
            }
          }
        }
        """,
        "variables": {
            "q": f"language:{language} stars:>1000 sort:stars",
            "n": per_page,
        },
    })


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 3 – user_profile: perfil de um usuário
# ──────────────────────────────────────────────────────────────────────────────
def user_profile(login: str) -> requests.Response:
    return _query({
        "query": """
        query($login: String!) {
          user(login: $login) {
            login
            name
            bio
            location
            company
            email
            followers { totalCount }
            following  { totalCount }
            repositories(privacy: PUBLIC) { totalCount }
            createdAt
            avatarUrl
          }
        }
        """,
        "variables": {"login": login},
    })


# ──────────────────────────────────────────────────────────────────────────────
# Cenário 4 – repo_issues: issues abertas de um repositório
# ──────────────────────────────────────────────────────────────────────────────
def repo_issues(owner: str, repo: str, per_page: int = 10) -> requests.Response:
    return _query({
        "query": """
        query($owner: String!, $repo: String!, $n: Int!) {
          repository(owner: $owner, name: $repo) {
            issues(states: OPEN, first: $n, orderBy: {field: CREATED_AT, direction: DESC}) {
              totalCount
              nodes {
                number
                title
                createdAt
                author { login }
                comments { totalCount }
                labels(first: 5) { nodes { name } }
              }
            }
          }
        }
        """,
        "variables": {"owner": owner, "repo": repo, "n": per_page},
    })
