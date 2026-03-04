import os


class CsvResultados:
    def __init__(self, diretorio_saida):
        self.diretorio_saida = diretorio_saida
        os.makedirs(self.diretorio_saida, exist_ok=True)

    def salvar(self, dataframe_repositorios):
        caminho_csv = os.path.join(self.diretorio_saida, "repositorios.csv")
        dataframe_repositorios.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
        print(f"\nDados salvos em: {caminho_csv}")

