import asyncio
import logging
import httpx # Certifique-se que o import está no topo
from sqlalchemy import text, pool # Importar pool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from core.celery_app import celery_app
from core.models import IngestionStatus
from core.config import DATABASE_URL
# from core.database import AsyncSessionFactory # Removido, pois será criado localmente

log = logging.getLogger(__name__)

async def process_jobs_logic():
    log.info("--- [WORKER] Polling for pending jobs... ---")
    
    claimed_jobs = [] # Inicializa fora do try/finally
    jobs_processed_count = 0
    total_claimed = 0

    engine = None # Inicializar engine fora do try para garantir que esteja disponível no finally
    try:
        engine = create_async_engine(
            DATABASE_URL,
            poolclass=pool.NullPool # Configurar NullPool aqui
        )
        LocalAsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

        async with LocalAsyncSessionFactory() as session:
            async with session.begin(): # Iniciar a transação aqui
                # 1. Reivindica os jobs (fora do loop de processamento)
                claimed_jobs = await claim_jobs_from_db(session)
                total_claimed = len(claimed_jobs) # Guarda o total antes do loop
                
                if not claimed_jobs:
                    log.info("--- [WORKER] No pending jobs found. ---")
                    return "No jobs to process."

                log.info(f"--- [WORKER] Claimed {total_claimed} jobs. ---")

                # 2. Processa cada job DENTRO do loop com try/except individual
                for job in claimed_jobs:
                    job_id = job['id']
                    source_uri = job['source_uri']
                    log.info(f"[Worker] Processing Job ID: {job_id}, URI: {source_uri}")

                    # -- Bloco TRY/EXCEPT por Job --
                    try:
                        # Tenta baixar
                        log.info(f"[Worker:{job_id}] Downloading content from {source_uri}...")
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.get(source_uri)
                            response.raise_for_status()
                            document_content = response.text
                        log.info(f"[Worker:{job_id}] Download successful. Content length: {len(document_content)} bytes.")

                        # TODO: Unstructured, Chunking, Embedding aqui

                        # Marca como COMPLETED apenas se tudo deu certo
                        await update_job_status(session, job_id, IngestionStatus.COMPLETED)
                        log.info(f"[Worker:{job_id}] Marked Job ID as COMPLETED.")
                        jobs_processed_count += 1

                    except httpx.HTTPStatusError as e:
                        log.error(f"[Worker:{job_id}] Failed to download {source_uri}. Status code: {e.response.status_code}")
                        await update_job_status(session, job_id, IngestionStatus.FAILED)
                    except httpx.RequestError as e:
                        log.error(f"[Worker:{job_id}] Failed to connect to {source_uri}. Error: {e}")
                        await update_job_status(session, job_id, IngestionStatus.FAILED)
                    except Exception as e:
                        log.error(f"[Worker:{job_id}] An unexpected error occurred during processing for this job: {e}", exc_info=True)
                        try: # Tenta marcar como FAILED mesmo se o erro foi inesperado
                            await update_job_status(session, job_id, IngestionStatus.FAILED)
                        except Exception as update_err:
                            log.error(f"[Worker:{job_id}] CRITICAL: Failed to even mark job as FAILED. Error: {update_err}", exc_info=True)
                    # -- Fim do Bloco TRY/EXCEPT por Job --

            return f"Processed {jobs_processed_count} of {total_claimed} claimed jobs."
    
    finally:
        if engine: # Apenas dispose se o engine foi criado
            await engine.dispose()
            log.info("[Worker] Engine e pool de conexão da tarefa descartados.")

# --- As funções claim_jobs_from_db e update_job_status permanecem iguais ---

@celery_app.task
def poll_and_process_jobs():
    """
    Tarefa periódica (síncrona) que chama a lógica assíncrona.
    """
    try:
        result = asyncio.run(process_jobs_logic())
        return result
    except Exception as e:
        log.error(f"[WORKER ERROR] Erro fatal na tarefa: {e}", exc_info=True)
        # Retorna falha para o Celery, mas a engine já foi disposed no finally
        return "Task execution failed critically."

async def claim_jobs_from_db(session):
    """
    Conecta ao banco e atomicamente busca e marca até 5 jobs como 'PROCESSING'.
    """
    pending_status_val = IngestionStatus.PENDING.value
    processing_status_val = IngestionStatus.PROCESSING.value
    
    claim_query = text(f"""
        UPDATE ai.ingestion_queue
        SET status = '{processing_status_val}', updated_at = NOW()
        WHERE id IN (
            SELECT id
            FROM ai.ingestion_queue
            WHERE status = '{pending_status_val}'
            ORDER BY created_at
            LIMIT 5
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, source_uri, namespace;
    """)
    
    print(">>> DEBUG: Entrou em claim_jobs_from_db <<<")
    log.info(f"[WORKER DBG] Executando claim_query: {claim_query}")
    # Usa a transação da sessão passada
    result = await session.execute(claim_query)
    claimed_jobs = result.mappings().fetchall()
    await session.commit() # Commit explícito após a reivindicação
    log.info(f"[Worker] Committed {len(claimed_jobs)} claimed jobs.")
    return claimed_jobs

async def update_job_status(session, job_id: int, status: IngestionStatus):
    """
    Atualiza o status de um job específico.
    """
    status_val = status.value
    update_query = text(f"""
        UPDATE ai.ingestion_queue
        SET status = '{status_val}', updated_at = NOW()
        WHERE id = :job_id
    """)
    # Usa a transação da sessão passada
    await session.execute(
        update_query,
        {"job_id": job_id}
    )