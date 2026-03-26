"""Modulo de compatibilidade: delega para adapters.quality_metrics_adapter."""

from pathlib import Path

from adapters.quality_metrics_adapter import run_ck as _run_ck_impl
from adapters.quality_metrics_adapter import summarize_ck_results as _summarize_ck_results_impl


def run_ck(repo_path, output_path, ck_dir):
    """Executa CK mantendo assinatura historica usada por chamadas legadas."""

    _run_ck_impl(Path(repo_path), Path(output_path), Path(ck_dir))


def summarize_ck_results(output_path):
    """Resume CSVs do CK mantendo retorno esperado por codigo legado."""

    return _summarize_ck_results_impl(Path(output_path))
