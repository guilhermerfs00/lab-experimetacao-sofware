import pandas as pd

from client.github_client import fetchRepositories
from service.data_service import processData, saveResults, generateGraphs, printReport

if __name__ == "__main__":
    repositorios = fetchRepositories()

    if repositorios:
        print(f"\n{len(repositorios)} repositórios coletados. Processando dados...")

        df = processData(repositorios)

        pd.set_option("display.max_rows", None)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", 200)

        print(df[[
            "Nome", "Estrelas", "Idade (anos)", "Pull Requests Aceitos",
            "Releases", "Dias Desde Atualização", "Linguagem Principal",
            "Razão Issues Fechadas"
        ]].to_string(index=False))

        saveResults(df)
        generateGraphs(df)
        printReport(df)
    else:
        print("Nenhum repositório foi retornado pela API.")
