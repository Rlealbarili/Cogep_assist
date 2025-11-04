import logging # Adicionar import
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .schemas import IngestionRequest
from core.database import get_db
from core.models import IngestionQueue as IngestionJob

log = logging.getLogger(__name__) # Configurar logger

app = FastAPI(
    title="Serviço de Ingestão COGEP",
    description="API para iniciar o processo de ingestão de documentos para o RAG.",
    version="0.1.0"
)


@app.post("/ingest", status_code=202)
async def create_ingestion_job(request: IngestionRequest, db: AsyncSession = Depends(get_db)):
    """
    Recebe uma URI de origem e um namespace para iniciar um job de ingestão.
    A dependência get_db gerencia automaticamente BEGIN/COMMIT/ROLLBACK.
    """

    new_job = IngestionJob(
        source_uri=str(request.source_uri),
        namespace=request.namespace
    )

    try:
        log.info(f"API: Adicionando Job (antes do add): {new_job.source_uri}")

        # NÃO HÁ MAIS 'async with db.begin():' AQUI
        db.add(new_job)
        
        # Força o flush para pegar erros de constraint antes do commit
        # e para obter o ID provisório, se necessário.
        await db.flush()
        
        log.info(f"API: Job adicionado à sessão (antes do commit automático): {new_job.source_uri}")
        # O COMMIT será executado automaticamente pela dependência get_db()

        # O refresh é necessário para obter os dados pós-commit (como o ID definitivo)
        await db.refresh(new_job)
        log.info(f"API: Refresh bem-sucedido. Job ID definitivo: {new_job.id}")

        return {
            "status": "job created",
            "job_id": new_job.id,
            "namespace": new_job.namespace,
            "source_uri": new_job.source_uri
        }
    except IntegrityError as e:
        log.error(f"API: Erro de integridade (constraint violation): {e}", exc_info=True)
        # O rollback já foi feito automaticamente pela dependência get_db
        raise HTTPException(status_code=400, detail="Erro de integridade: job duplicado ou constraint violada.")
    except SQLAlchemyError as e:
        log.error(f"API: Erro do SQLAlchemy durante operação de banco: {e}", exc_info=True)
        # O rollback já foi feito automaticamente
        raise HTTPException(status_code=500, detail="Erro de banco de dados ao salvar o job.")
    except Exception as e:
        log.error(f"API: Erro inesperado durante operação: {e}", exc_info=True)
        # O rollback já foi feito automaticamente
        raise HTTPException(status_code=500, detail="Erro interno ao salvar o job no banco de dados.")
