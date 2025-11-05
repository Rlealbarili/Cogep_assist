from fastapi import FastAPI, APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
import logging

from ingestion_service.schemas import IngestionRequest, IngestionResponse
from core.database import get_db
from core.models import IngestionQueue, PyIngestionStatus

log = logging.getLogger(__name__)

# Configuração da aplicação FastAPI
app = FastAPI(
    title="Serviço de Ingestão COGEP",
    description="API para iniciar o processo de ingestão de documentos para o RAG.",
    version="0.1.0"
)

# Roteador com prefixo e tags
router = APIRouter(prefix='/api/v1', tags=['Ingestion'])

@router.post('/ingest', response_model=IngestionResponse, status_code=201)
async def create_ingestion_job(
    request_data: IngestionRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Endpoint para criar uma nova tarefa de ingestão.
    Apenas insere na tabela 'ai.ingestion_queue' e retorna imediatamente.
    """
    # Cria uma nova instância de IngestionQueue com status inicial PyIngestionStatus.PENDING
    new_job = IngestionQueue(
        source_uri=request_data.source_uri,
        namespace=request_data.namespace,
        status=PyIngestionStatus.PENDING
    )

    try:
        # Adiciona o novo job à sessão
        session.add(new_job)
        # Commita as alterações no banco de dados
        await session.commit()
        # Atualiza o objeto com os dados recém-inseridos (como o ID)
        await session.refresh(new_job)

        # Retorna os dados do novo job criado
        return new_job
    except IntegrityError as e:
        log.error(f"API: Erro de integridade (constraint violation): {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Erro de integridade: job duplicado ou constraint violada.")
    except SQLAlchemyError as e:
        log.error(f"API: Erro do SQLAlchemy durante operação de banco: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro de banco de dados ao salvar o job.")
    except Exception as e:
        log.error(f"API: Erro inesperado durante operação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao salvar o job no banco de dados.")


# Inclui as rotas definidas no roteador
app.include_router(router)

# Endpoint para testar a aplicação
@app.get("/")
async def root():
    return {"message": "Serviço de Ingestão COGEP - API para RAG"}
