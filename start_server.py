import subprocess
import sys
import os

# Adiciona o diretório raiz do projeto ao PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Muda para o diretório do projeto
os.chdir(project_root)

# Ativar o ambiente virtual e iniciar o uvicorn
command = [
    'uvicorn',
    'ingestion_service.main:app',
    '--reload',
    '--host', '0.0.0.0',
    '--port', '8000'
]

# Iniciar o subprocesso
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

print("Servidor iniciado. PID:", process.pid)

try:
    # Imprimir a saída do servidor em tempo real
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())

    # Capturar qualquer erro
    _, stderr = process.communicate()
    if stderr:
        print("Erro:", stderr)

except KeyboardInterrupt:
    print("\nEncerrando o servidor...")
    process.terminate()
    process.wait()