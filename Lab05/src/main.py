# -*- coding: utf-8 -*-
"""
main.py – Lab05: GraphQL vs REST — Experimento Controlado

Executa o experimento controlado comparando a API REST e GraphQL do GitHub
nas métricas de:
  • RQ1 – Tempo de resposta (ms)
  • RQ2 – Tamanho da resposta (bytes)

Uso:
    python src/main.py                   # 30 trials por (cenário × API)
    python src/main.py --trials 50       # número customizado de trials
    python src/main.py --no-checkpoint   # ignora checkpoint existente e recomeça

Saída:
    docs/results.csv
"""

import argparse
import csv
import os
import random
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(__file__))
import rest_adapter
import graphql_adapter

# ──────────────────────────────────────────────────────────────────────────────
# Caminhos
# ──────────────────────────────────────────────────────────────────────────────
_ROOT      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_DOCS_DIR  = os.path.join(_ROOT, "docs")
os.makedirs(_DOCS_DIR, exist_ok=True)

RESULTS_PATH      = os.path.join(_DOCS_DIR, "results.csv")
CHECKPOINT_PATH   = os.path.join(_DOCS_DIR, "checkpoint.json")

N_TRIALS      = 30
INTER_TRIAL_S = 1.5
WARM_UP_CALLS = 3

# ──────────────────────────────────────────────────────────────────────────────
# Objetos experimentais
# ──────────────────────────────────────────────────────────────────────────────
_REPOS = [
    ("torvalds",  "linux"),
    ("microsoft", "vscode"),
    ("facebook",  "react"),
    ("golang",    "go"),
    ("rust-lang", "rust"),
    ("tensorflow","tensorflow"),
    ("django",    "django"),
    ("rails",     "rails"),
    ("kubernetes","kubernetes"),
    ("flutter",   "flutter"),
]

_USERS = [
    "torvalds", "gaearon", "sindresorhus", "tj", "yyx990803",
    "addyosmani", "paulirish", "wesbos", "dan_abramov", "primer",
]

_LANGUAGES = ["Python", "JavaScript", "TypeScript", "Go", "Rust"]

CSV_HEADER = [
    "scenario", "api_type", "trial_index",
    "response_time_ms", "response_size_bytes", "http_status",
    "owner", "repo", "language", "login",
]


# ──────────────────────────────────────────────────────────────────────────────
# Medição
# ──────────────────────────────────────────────────────────────────────────────
def _measure(fn, *args, **kwargs) -> tuple[float, int, int]:
    """Retorna (tempo_ms, tamanho_bytes, http_status)."""
    t0 = time.perf_counter()
    try:
        resp = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        size    = len(resp.content)
        status  = resp.status_code
    except requests.RequestException as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        size    = 0
        status  = -1
    return elapsed, size, status


def _warm_up(fn, *args, **kwargs):
    for _ in range(WARM_UP_CALLS):
        try:
            fn(*args, **kwargs)
        except Exception:
            pass
        time.sleep(0.5)


# ──────────────────────────────────────────────────────────────────────────────
# Execução de um cenário
# ──────────────────────────────────────────────────────────────────────────────
def run_scenario(scenario: str, n_trials: int) -> list[dict]:
    rows = []

    if scenario == "repo_info":
        obj        = random.choice(_REPOS)
        owner, repo = obj
        rest_fn    = lambda: rest_adapter.repo_info(owner, repo)
        graphql_fn = lambda: graphql_adapter.repo_info(owner, repo)
        extra      = {"owner": owner, "repo": repo, "language": "", "login": ""}

    elif scenario == "search_repos":
        lang       = random.choice(_LANGUAGES)
        rest_fn    = lambda: rest_adapter.search_repos(lang)
        graphql_fn = lambda: graphql_adapter.search_repos(lang)
        extra      = {"owner": "", "repo": "", "language": lang, "login": ""}

    elif scenario == "user_profile":
        login      = random.choice(_USERS)
        rest_fn    = lambda: rest_adapter.user_profile(login)
        graphql_fn = lambda: graphql_adapter.user_profile(login)
        extra      = {"owner": "", "repo": "", "language": "", "login": login}

    elif scenario == "repo_issues":
        obj        = random.choice(_REPOS)
        owner, repo = obj
        rest_fn    = lambda: rest_adapter.repo_issues(owner, repo)
        graphql_fn = lambda: graphql_adapter.repo_issues(owner, repo)
        extra      = {"owner": owner, "repo": repo, "language": "", "login": ""}

    else:
        raise ValueError(f"Cenário desconhecido: {scenario}")

    # Aquecimento
    print(f"  [warm-up] {scenario} …", end=" ", flush=True)
    _warm_up(rest_fn)
    _warm_up(graphql_fn)
    print("ok")

    # Trials intercalados (REST / GraphQL alternados aleatoriamente)
    apis = (["REST"] * n_trials + ["GraphQL"] * n_trials)
    random.shuffle(apis)
    trial_counters = {"REST": 0, "GraphQL": 0}

    for api in apis:
        fn = rest_fn if api == "REST" else graphql_fn
        t_ms, size, status = _measure(fn)
        idx = trial_counters[api]
        trial_counters[api] += 1

        print(f"    {api:<8} trial {idx:02d}  {t_ms:7.1f} ms  {size:8,} bytes  HTTP {status}")
        rows.append({
            "scenario":           scenario,
            "api_type":           api,
            "trial_index":        idx,
            "response_time_ms":   round(t_ms, 3),
            "response_size_bytes": size,
            "http_status":        status,
            **extra,
        })
        time.sleep(INTER_TRIAL_S)

    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Lab05 – GraphQL vs REST")
    parser.add_argument("--trials",        type=int, default=N_TRIALS)
    parser.add_argument("--no-checkpoint", action="store_true")
    args = parser.parse_args()

    scenarios = ["repo_info", "search_repos", "user_profile", "repo_issues"]

    all_rows: list[dict] = []

    for sc in scenarios:
        print(f"\n{'='*60}")
        print(f"Cenário: {sc}  ({args.trials} trials × 2 APIs)")
        print(f"{'='*60}")
        rows = run_scenario(sc, args.trials)
        all_rows.extend(rows)

    # Salva CSV
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✓ {len(all_rows)} medições salvas em: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
