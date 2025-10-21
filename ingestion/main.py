from fastapi import FastAPI, HTTPException, status
from typing import Dict, Any

# Importa o modelo Pydantic do diretório core
# Assumindo que a estrutura de pastas está no PYTHONPATH
from core.models import IngestionRequest

app = FastAPI(
    title="Serviço de Ingestão - Agente COGEP",
    description="API para iniciar o processo de ingestão de documentos para o RAG.",
    version="0.1.0"
)

@app.post("/ingest", 
          status_code=status.HTTP_202_ACCEPTED,
          summary="Recebe um documento para ingestão",
          response_description="Confirmação de que o pedido de ingestão foi aceito e enfileirado.")
async def create_ingestion_job(request: IngestionRequest) -> Dict[str, Any]:
    """
    Endpoint para enfileirar um novo job de ingestão.

    Recebe uma URL de origem e um namespace, valida os dados e (futuramente)
    adiciona a um sistema de fila como Celery.

    Por enquanto, apenas imprime os dados recebidos no console.
    """
    print(f"[INGESTION JOB RECEIVED] Namespace: {request.namespace}, URI: {request.source_uri}")
    
    # Simula a adição a uma fila
    # No futuro, aqui você chamaria: `ingestion_task.delay(request.dict())`
    
    return {
        "status": "accepted",
        "message": "Pedido de ingestão recebido e enfileirado para processamento.",
        "details": {
            "namespace": request.namespace,
            "source_uri": str(request.source_uri)
        }
    }

@app.get("/health", 
         status_code=status.HTTP_200_OK,
         summary="Verifica a saúde da API")
async def health_check():
    """
    Endpoint simples para verificar se a API está online.
    """
    return {"status": "ok"}
