from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import IngestionRequest
from core.database import get_db
from core.schemas import IngestionJob


app = FastAPI(
    title="Serviço de Ingestão COGEP",
    description="API para iniciar o processo de ingestão de documentos para o RAG.",
    version="0.1.0"
)


@app.post("/ingest", status_code=202)
async def create_ingestion_job(request: IngestionRequest, db: AsyncSession = Depends(get_db)):
    """
    Recebe uma URI de origem e um namespace para iniciar um job de ingestão.

    Adiciona a tarefa na tabela `ai.ingestion_queue` com status 'pending'.
    """
    
    new_job = IngestionJob(
        source_uri=str(request.source_uri),
        namespace=request.namespace
    )
    
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    return {
        "status": "job created",
        "job_id": new_job.id,
        "namespace": new_job.namespace,
        "source_uri": new_job.source_uri
    }

@app.get("/health", status_code=200)
async def health_check():
    """Endpoint simples para verificação de saúde do serviço."""
    return {"status": "ok"}
