"""Script para baixar e preparar o CK com dependências embutidas."""

import urllib.request
import os
from pathlib import Path

def download_ck():
    """Baixa a versão executável do CK se não existir."""
    
    ck_dir = Path(__file__).parent
    ck_jar_with_deps = ck_dir / "ck-0.7.1-SNAPSHOT-jar-with-dependencies.jar"
    ck_jar_original = ck_dir / "ck-0.7.1-SNAPSHOT.jar"
    
    if ck_jar_with_deps.exists():
        print(f"✅ CK com dependências já existe: {ck_jar_with_deps}")
        return str(ck_jar_with_deps)
    
    if ck_jar_original.exists():
        print(f"⚠️  Apenas o CK base existe. Tentando usar via classpath...")
        return str(ck_jar_original)
    
    print("📥 Baixando CK com dependências...")
    url = "https://github.com/mauricioaniche/ck/releases/download/0.7.1/ck-0.7.1-SNAPSHOT-jar-with-dependencies.jar"
    
    try:
        urllib.request.urlretrieve(url, str(ck_jar_with_deps))
        print(f"✅ CK baixado com sucesso: {ck_jar_with_deps}")
        return str(ck_jar_with_deps)
    except Exception as e:
        print(f"❌ Falha ao baixar CK: {e}")
        print("⚠️  Continuando com JAR base (pode falhar na execução)...")
        return str(ck_jar_original)


if __name__ == "__main__":
    ck_path = download_ck()
    print(f"CK path: {ck_path}")

