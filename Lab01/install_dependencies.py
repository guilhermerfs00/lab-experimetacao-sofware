import os
import subprocess
import venv

venv_dir = ".venv"

if not os.path.exists(venv_dir):
    print("Criando ambiente virtual...")
    venv.create(venv_dir, with_pip=True)

python_exec = os.path.join(venv_dir, "Scripts", "python.exe" if os.name == "nt" else "bin/python")

subprocess.run([python_exec, "-m", "ensurepip"], check=True)

subprocess.run([python_exec, "-m", "pip", "install", "--upgrade", "pip"], check=True)
subprocess.run([python_exec, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

print("✅ Ambiente virtual configurado e dependências instaladas!")