import asyncio
import hashlib
from datetime import datetime
import os
import logging
from sqlalchemy import pool

import httpx
import openai
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from celery import Celery
import os
from core.config import DATABASE_URL
from core.models import IngestionQueue, RagDocuments1536

# Configuração do logger
log = logging.getLogger(__name__)

# Inicialização do Celery
celery_app = Celery('worker')

# Configuração do Celery
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_hijack_root_logger=False,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
)

# Função auxiliar para chamada da API de parsing Unstructured
async def call_unstructured_api(content: bytes) -> str:
    """
    Faz chamada à API de parsing do Unstructured para obter o conteúdo textual do documento
    """
    # Implementação do parsing com Unstructured Client
    # Ajuste conforme a documentação oficial do unstructured-client
    # Por enquanto, retornando o conteúdo como string (isso deve ser substituído pela implementação real)
    return content.decode('utf-8', errors='ignore')


# Função auxiliar para chamada da API de embeddings OpenAI
async def call_openai_embedding(content: str) -> list:
    """
    Faz chamada à API de embeddings do OpenAI para gerar o embedding do conteúdo
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise Exception("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
    
    client = openai.AsyncOpenAI(api_key=openai_api_key)
    
    response = await client.embeddings.create(
        input=content,
        model="text-embedding-3-small"  # Ou outro modelo de sua escolha
    )
    
    return response.data[0].embedding


@celery_app.task(name='tasks.process_ingestion_job')
def process_ingestion_job(job_id: int):
    # Executar a lógica assíncrona dentro de um loop de eventos
    import asyncio
    return asyncio.run(_process_ingestion_job_async(job_id))


async def _process_ingestion_job_async(job_id: int):
    """
    Tarefa principal do worker para processar um job de ingestão.
    Aplica o Engine-per-task (PATTERN-001) para gerenciar a conexão com o banco.
    """
    engine = None
    try:
        # PATTERN-001: Criar engine e sessionmaker locais para esta tarefa
        engine = create_async_engine(
            DATABASE_URL,
            echo=True,
            poolclass=pool.NullPool
        )
        session_maker = async_sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

        async with session_maker() as session:
            # Buscar o job no banco
            job = await session.get(IngestionQueue, job_id)
            if not job:
                log.warning(f"Job com ID {job_id} não encontrado")
                return

            log.info(f"Processando job {job.id} de {job.source_uri}")
            
            # Atualizar status para PROCESSING
            job.status = 'PROCESSING'
            await session.commit()
            
            # Download do conteúdo
            async with httpx.AsyncClient() as client:
                response = await client.get(job.source_uri)
                if response.status_code != 200:
                    raise Exception(f"Falha no download: {response.status_code}")
                
                doc_content = response.content

            # Parsing do conteúdo
            parsed_content = await call_unstructured_api(doc_content)

            # Geração do hash SHA256
            content_sha = hashlib.sha256(parsed_content.encode()).hexdigest()

            # Gerar embedding
            embedding = await call_openai_embedding(parsed_content)

            # Salvar no RAG DB
            new_doc = RagDocuments1536(
                namespace=job.namespace,
                content=parsed_content,
                content_sha256=content_sha,
                embedding=embedding,
                document_metadata={'source_uri': job.source_uri}
            )
            
            session.add(new_doc)
            
            # Atualizar status para COMPLETED
            job.status = 'COMPLETED'
            job.updated_at = datetime.utcnow()
            
            await session.commit()
            log.info(f"Job {job.id} processado com sucesso")

    except Exception as e:
        log.error(f"Erro ao processar job {job_id}: {str(e)}", exc_info=True)
        
        # Em caso de erro, criar nova sessão para atualizar o status
        if engine:
            async with async_sessionmaker(bind=engine)() as error_session:
                job = await error_session.get(IngestionQueue, job_id)
                if job:
                    job.status = 'FAILED'
                    job.processing_log = str(e)
                    job.updated_at = datetime.utcnow()
                    await error_session.commit()
    finally:
        # PATTERN-001: Dispor do engine para liberar recursos
        if engine:
            await engine.dispose()


@celery_app.task(name='tasks.schedule_job_processor')
def schedule_job_processor():
    # Executar a lógica assíncrona dentro de um loop de eventos
    import asyncio
    return asyncio.run(_schedule_job_processor_async())


async def _schedule_job_processor_async():
    """
    Tarefa agendada para buscar e agendar jobs de ingestão.
    Implementa o 'Feeder' que verifica por novos jobs.
    """
    engine = None
    try:
        # PATTERN-001: Criar engine e sessionmaker locais para esta tarefa
        engine = create_async_engine(
            DATABASE_URL,
            echo=True,
            poolclass=pool.NullPool
        )
        session_maker = async_sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

        async with session_maker() as session:
            # Reivindicar atomicamente um job pendente
            result = await session.execute(
                select(IngestionQueue)
                .filter(IngestionQueue.status == 'PENDING')
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            job = result.scalar_one_or_none()

            if job:
                # Atualizar status para PROCESSING
                job.status = 'PROCESSING'
                await session.commit()
                
                # Agendar o processamento do job
                process_ingestion_job.delay(job.id)
                log.info(f"Job {job.id} reivindicado e agendado para processamento")

    except Exception as e:
        log.error(f"Erro ao agendar processamento de job: {str(e)}", exc_info=True)
    finally:
        # PATTERN-001: Dispor do engine para liberar recursos
        if engine:
            await engine.dispose()


# Configurar o Celery Beat para agendar tarefas periódicas
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Configura tarefas periódicas para o Celery Beat
    """
    # Agendar o schedule_job_processor para rodar a cada 10 segundos
    sender.add_periodic_task(10.0, schedule_job_processor.s(), name='check for new jobs')