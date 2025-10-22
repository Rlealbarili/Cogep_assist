import httpx
import json

# Dados do Job que queremos enviar
job_data = {
    "source_uri": "https://exemplo.com/documento.pdf",
    "namespace": "teste_inicial"
}

# URL da nossa API de ingestão rodando localmente
api_url = "http://localhost:8001/ingest"

try:
    print(f"Enviando requisição POST para {api_url}...")
    print(f"Payload: {json.dumps(job_data, indent=2)}")

    response = httpx.post(api_url, json=job_data, timeout=10.0)

    print("\n--- Resposta Recebida ---")
    print(f"Status Code: {response.status_code}")
    print(f"Resposta (JSON): {response.json()}")
    print("-------------------------\n")

    if response.status_code == 202:
        print("SUCESSO: O Job foi aceito pela API.")
    else:
        print(f"FALHA: A API retornou um status inesperado: {response.status_code}")

except httpx.ConnectError as e:
    print(f"\nERRO DE CONEXÃO: Não foi possível conectar a {api_url}.")
    print("Verifique se o servidor Uvicorn (Prompt 2) está rodando.")
except Exception as e:
    print(f"\nUm erro inesperado ocorreu: {e}")
