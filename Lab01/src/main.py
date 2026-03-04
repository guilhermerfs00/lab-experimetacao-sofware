import pandas as pd

from client.github_client import buscar_repositorios
from service.data_service import processar_dados, salvar_resultados, gerar_graficos

if __name__ == "__main__":
    repositorios = buscar_repositorios()
    dados_repositorios = processar_dados(repositorios)

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    salvar_resultados(dados_repositorios)
    gerar_graficos(dados_repositorios)
