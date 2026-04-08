import argparse
import sys
from pathlib import Path

import pandas as pd
import repositories_adapter


def main():
    parser = argparse.ArgumentParser(
        description="Lab02 -- Coleta e analise de repositorios Java populares do GitHub."
    )
    parser.add_argument('--start', type=int, default=0, help='Indice de inicio')
    parser.add_argument('--end', type=int, default=1000, help='Indice final')
    parser.add_argument('--max-workers-ck', type=int, default=None,
                        help='Numero de workers paralelos para executar CK')
    parser.add_argument('--ck-timeout-seconds', type=int, default=None,
                        help='Timeout por repositorio na execucao do CK')
    parser.add_argument('--quiet', action='store_true',
                        help='Suprimir a saida no terminal')
    parser.add_argument('--resume', action='store_true',
                        help='Retomar de checkpoint anterior (workdir/results_checkpoint.csv)')
    parser.add_argument('--skip-report', action='store_true',
                        help='Pular a geracao do relatorio final DOCX/PDF')
    args = parser.parse_args()

    if not args.quiet:
        print("=" * 70)
        print("  Lab02 -- Analise de qualidade de repositorios Java populares")
        print(f"  Meta: {args.end - args.start} repositorios | Resume: {args.resume}")
        print("=" * 70)

    # ---------- Coleta e processamento ----------
    try:
        df = repositories_adapter.coletar_e_processar_repositorios(
            args.start,
            args.end,
            max_workers=args.max_workers_ck,
            ck_timeout_seconds=args.ck_timeout_seconds,
            resume=args.resume,
        )
    except RuntimeError as error:
        print(f"[ERRO] {error}")
        return

    if df is None or df.empty:
        print("[AVISO] Nenhum repositorio valido foi analisado. Relatorio nao gerado.")
        return

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)

    if not args.quiet:
        print(f"\n[INFO] Total de repositorios analisados: {len(df)}")
        print(df.to_string())

    # ---------- Graficos e relatorio HTML ----------
    print("\n[INFO] Gerando graficos de correlacao...")
    graphs = repositories_adapter.plotGraphs(df)

    print("[INFO] Gerando relatorio HTML...")
    repositories_adapter.generate_html_report(df, graphs)

    # ---------- Relatorio final DOCX / PDF ----------
    if not args.skip_report:
        _generate_final_report()

    print("\n[OK] Pipeline concluida com sucesso!")


def _generate_final_report():
    """Importa e executa gerar_relatorio_final para produzir DOCX e PDF."""
    try:
        # Adiciona o diretorio pai ao path para importar o modulo.
        lab02_dir = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(lab02_dir))

        import gerar_relatorio_final as grf

        html_path = grf.SOURCE_HTML
        if not html_path.exists():
            print("[AVISO] report.html nao encontrado -- pulando geracao do DOCX/PDF.")
            return

        print("\n[INFO] Gerando relatorio final (DOCX + PDF)...")
        df = grf.load_dataframe(html_path)
        summary = grf.summarize_metrics(df)
        correlations = grf.compute_correlations(df)
        figures = grf.build_figures(df, summary, correlations)

        grf.build_docx(df, summary, correlations, figures.copy(), grf.DEFAULT_DOCX)
        grf.build_pdf(df, summary, correlations, figures.copy(), grf.DEFAULT_PDF)

        import matplotlib.pyplot as plt
        for fig in figures.values():
            plt.close(fig)

        print(f"  DOCX: {grf.DEFAULT_DOCX}")
        print(f"  PDF:  {grf.DEFAULT_PDF}")

    except Exception as e:
        print(f"[AVISO] Erro ao gerar relatorio final: {e}")
        print("  Voce pode gerar manualmente com: python gerar_relatorio_final.py")


if __name__ == "__main__":
    main()
