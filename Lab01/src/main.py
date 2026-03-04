import pandas as pd

from client.github_client import buscandoRepositorios
from service.data_service import processarDados, salvarResultados, gerarGraficos

if __name__ == "__main__":
    repositorios = buscandoRepositorios()
    dados_repositorios = processarDados(repositorios)

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    salvarResultados(dados_repositorios)
    gerarGraficos(dados_repositorios)
