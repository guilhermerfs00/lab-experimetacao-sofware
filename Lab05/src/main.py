# -*- coding: utf-8 -*-
"""
main.py – Lab05: GraphQL vs REST — Experimento Controlado

Executa o experimento controlado comparando a API REST e GraphQL do GitHub
nas métricas de:
  • RQ1 – Tempo de resposta (ms)
  • RQ2 – Tamanho da resposta (bytes)

Uso:
    python main.py                   # 30 trials por (cenário × API)
    python main.py --trials 50       # número customizado de trials
    python main.py --no-checkpoint   # ignora checkpoint existente e recomeça

Saída:
    ../docs/results.csv
"""

import argparse
import os
import random
import sys
import time

import pandas as pd

import rest_adapter
import graphql_adapter

# Força UTF-8 no Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ──────────────────────────────────────────────────────────────────────────────
# Configurações gerais
# ──────────────────────────────────────────────────────────────────────────────
_DOCS_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
os.makedirs(_DOCS_DIR, exist_ok=True)

RESULTS_PATH   = os.path.join(_DOCS_DIR, "results.csv")
N_TRIALS       = 30          # trials por (cenário × API)
INTER_TRIAL_S  = 1.5         # pausa entre chamadas (segundos) — controla rate-limit
WARM_UP_CALLS  = 3           # chamadas de aquecimento (descartadas)

# ──────────────────────────────────────────────────────────────────────────────
# Pool de objetos experimentais
# ──────────────────────────────────────────────────────────────────────────────

# Repositórios para cenários "repo_info" e "repo_issues"
_REPOS = [
    ("facebook",   "react"),
    ("microsoft",  "vscode"),
    ("torvalds",   "linux"),
    ("tensorflow", "tensorflow"),
    ("django",     "django"),
    ("golang",     "go"),
    ("nodejs",     "node"),
    ("rails",      "rails"),
    ("flutter",    "flutter"),
    ("docker",     "compose"),
]

# Linguagens rotativas para "search_repos"
_LANGUAGES = ["Python", "JavaScript", "Java", "TypeScript", "Go",
               "Rust",   "C++",       "Ruby", "Swift",      "Kotlin"]

# Usuários para "user_profile"
_USERS = [
    "torvalds",    "gvanrossum", "antirez",    "yyx990803",
    "addyosmani",  "sindresorhus","tj",         "mrdoob",
    "jeresig",     "defunkt",
]

# ──────────────────────────────────────────────────────────────────────────────
# Definição dos cenários
# ──────────────────────────────────────────────────────────────────────────────

def _build_trials(n_trials: int) -> list[dict]:
    """
    Constrói a lista ordenada de trials a executar.
    Cada trial é um dict com:
        scenario, api_type, trial_index, kwargs
    A ordem REST/GraphQL é alternada aleatoriamente dentro de cada cenário
    para reduzir viés de ordenação.
    """
    scenarios = ["repo_info", "search_repos", "user_profile", "repo_issues"]
    api_types = ["REST", "GraphQL"]

    # Monta pares (scenario, api_type) com índice de objeto experimental circular
    all_trials: list[dict] = []
    for scenario in scenarios:
        for api in api_types:
            for i in range(n_trials):
                trial: dict = {
                    "scenario":    scenario,
                    "api_type":    api,
                    "trial_index": i,
                }
                if scenario in ("repo_info", "repo_issues"):
                    owner, repo = _REPOS[i % len(_REPOS)]
                    trial["owner"] = owner
                    trial["repo"]  = repo
                elif scenario == "search_repos":
                    trial["language"] = _LANGUAGES[i % len(_LANGUAGES)]
                elif scenario == "user_profile":
                    trial["login"] = _USERS[i % len(_USERS)]
                all_trials.append(trial)

    # Embaralha dentro de cada cenário para reduzir efeitos de ordem
    random.seed(42)
    result: list[dict] = []
    for scenario in scenarios:
        subset = [t for t in all_trials if t["scenario"] == scenario]
        random.shuffle(subset)
        result.extend(subset)

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Execução de um único trial
# ──────────────────────────────────────────────────────────────────────────────

def _run_trial(trial: dict) -> dict | None:
    scenario = trial["scenario"]
    api      = trial["api_type"]

    try:
        if api == "REST":
            if scenario == "repo_info":
                metrics = rest_adapter.get_repo_info(trial["owner"], trial["repo"])
            elif scenario == "search_repos":
                metrics = rest_adapter.search_repos(trial["language"])
            elif scenario == "user_profile":
                metrics = rest_adapter.get_user_profile(trial["login"])
            else:  # repo_issues
                metrics = rest_adapter.get_repo_issues(trial["owner"], trial["repo"])
        else:  # GraphQL
            if scenario == "repo_info":
                metrics = graphql_adapter.get_repo_info(trial["owner"], trial["repo"])
            elif scenario == "search_repos":
                metrics = graphql_adapter.search_repos(trial["language"])
            elif scenario == "user_profile":
                metrics = graphql_adapter.get_user_profile(trial["login"])
            else:  # repo_issues
                metrics = graphql_adapter.get_repo_issues(trial["owner"], trial["repo"])
    except Exception as exc:
        print(f"  [ERROR] {scenario}/{api}: {exc}")
        return None

    if not metrics["success"]:
        print(f"  [SKIP] {scenario}/{api} HTTP {metrics['http_status']}")
        return None

    row = {
        "scenario":             scenario,
        "api_type":             api,
        "trial_index":          trial["trial_index"],
        "response_time_ms":     metrics["response_time_ms"],
        "response_size_bytes":  metrics["response_size_bytes"],
        "http_status":          metrics["http_status"],
    }
    # Adiciona contexto do objeto experimental (sem chaves ausentes)
    for k in ("owner", "repo", "language", "login"):
        row[k] = trial.get(k, "")

    return row


# ──────────────────────────────────────────────────────────────────────────────
# Aquecimento (warm-up)
# ──────────────────────────────────────────────────────────────────────────────

def _warm_up() -> None:
    print("\n[WARM-UP] Realizando chamadas de aquecimento (descartadas)...")
    for _ in range(WARM_UP_CALLS):
        rest_adapter.get_repo_info("facebook", "react")
        graphql_adapter.get_repo_info("facebook", "react")
        time.sleep(0.5)
    print("[WARM-UP] Concluído.\n")


# ──────────────────────────────────────────────────────────────────────────────
# Orquestrador principal
# ──────────────────────────────────────────────────────────────────────────────

def run(n_trials: int = N_TRIALS, use_checkpoint: bool = True) -> None:
    # Carrega checkpoint se disponível
    already_done: list[dict] = []
    checkpoint_key: set = set()

    if use_checkpoint and os.path.exists(RESULTS_PATH):
        df_existing = pd.read_csv(RESULTS_PATH, on_bad_lines="skip")
        already_done = df_existing.to_dict("records")
        checkpoint_key = {
            (r["scenario"], r["api_type"], int(r["trial_index"]))
            for r in already_done
        }
        print(f"[INFO] Checkpoint carregado — {len(already_done)} medições já realizadas.")
    else:
        print("[INFO] Iniciando experimento do zero.")

    _warm_up()

    trials = _build_trials(n_trials)
    total  = len(trials)
    done   = 0
    results: list[dict] = list(already_done)

    print(f"[INFO] Total de trials planejados: {total}")
    print(f"[INFO] Trials a executar (excluindo checkpoint): "
          f"{total - len(checkpoint_key)}\n")

    for idx, trial in enumerate(trials, start=1):
        key = (trial["scenario"], trial["api_type"], trial["trial_index"])
        if key in checkpoint_key:
            continue

        print(f"  [{idx:03d}/{total}] {trial['scenario']:15s} | {trial['api_type']:7s} "
              f"| trial {trial['trial_index']:02d}", end=" … ", flush=True)

        row = _run_trial(trial)

        if row:
            results.append(row)
            done += 1
            print(f"{row['response_time_ms']:8.1f} ms  "
                  f"{row['response_size_bytes']:8d} bytes")
            # Persiste a cada 10 medições
            if done % 10 == 0:
                pd.DataFrame(results).to_csv(RESULTS_PATH, index=False, encoding="utf-8-sig")
        else:
            print("FALHOU — ignorado")

        time.sleep(INTER_TRIAL_S)

    # Salva resultado final
    df = pd.DataFrame(results)
    df.to_csv(RESULTS_PATH, index=False, encoding="utf-8-sig")
    print(f"\n[OK] Experimento concluído! {len(df)} medições salvas em '{RESULTS_PATH}'")
    _print_summary(df)


def _print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print("RESUMO DOS RESULTADOS")
    print("=" * 60)
    for scenario in df["scenario"].unique():
        print(f"\n>>> Cenário: {scenario}")
        grp = df[df["scenario"] == scenario].groupby("api_type")
        for api, sub in grp:
            print(
                f"    {api:8s} — tempo: {sub['response_time_ms'].median():.1f} ms (mediana)  "
                f"| tamanho: {sub['response_size_bytes'].median():.0f} bytes (mediana)"
            )
    print("=" * 60)


# ──────────────────────────────────────────────────────────────────────────────
# Entrada
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Lab05 – Experimento GraphQL vs REST (GitHub API)"
    )
    parser.add_argument(
        "--trials", type=int, default=N_TRIALS,
        help=f"Número de trials por (cenário × API) [padrão: {N_TRIALS}]"
    )
    parser.add_argument(
        "--no-checkpoint", dest="no_checkpoint", action="store_true",
        help="Ignora checkpoint existente e reexecuta tudo"
    )
    args = parser.parse_args()

    run(n_trials=args.trials, use_checkpoint=not args.no_checkpoint)
