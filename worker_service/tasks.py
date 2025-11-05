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
from core.models import IngestionQueue, RagDocuments1536, PyIngestionStatus

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
async def call_unstructured_api(content: bytes, filename: str = "document") -> str:
    """
    Faz chamada à API de parsing do Unstructured para obter o conteúdo textual do documento
    """
    unstructured_api_url = os.getenv("UNSTRUCTURED_API_URL")
    if not unstructured_api_url:
        raise Exception("UNSTRUCTURED_API_URL não encontrada nas variáveis de ambiente")
    
    files = {'files': (filename, content)}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{unstructured_api_url}/general/v0/general", files=files)
            response.raise_for_status() # Lança exceção para erros HTTP (4xx, 5xx)
            parsed_elements = response.json()
            # Processar 'parsed_elements' para extrair e concatenar o texto
            full_text = "\n\n".join([element.get("text", "") for element in parsed_elements])
            
            # Garantir que o texto retornado está em formato UTF-8
            # para evitar problemas de codificação nos estágios subsequentes
            if isinstance(full_text, str):
                full_text = full_text.encode('utf-8', errors='replace').decode('utf-8')
            else:
                full_text = str(full_text, 'utf-8', errors='replace')
            
            return full_text
        except httpx.HTTPStatusError as e:
            log.error(f"Erro HTTP ao chamar Unstructured API: {e.response.status_code} - {e.response.text}", exc_info=True)
            raise Exception(f"Erro HTTP ao chamar Unstructured API: {e.response.status_code}")
        except UnicodeDecodeError as e:
            log.error(f"Erro de decodificação ao processar com Unstructured API: {e}", exc_info=True)
            raise Exception(f"Erro de decodificação ao processar com Unstructured API: {e}")
        except Exception as e:
            log.error(f"Erro ao processar com Unstructured API: {e}", exc_info=True)
            raise Exception(f"Erro ao processar com Unstructured API: {e}")


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
            job.status = PyIngestionStatus.PROCESSING
            await session.commit()
            
            # Download do conteúdo
            async with httpx.AsyncClient() as client:
                response = await client.get(job.source_uri)
                if response.status_code != 200:
                    raise Exception(f"Falha no download: {response.status_code}")
                
                doc_content = response.content

            # Parsing do conteúdo
            # Extrair o nome do arquivo da URI para passar para a API do Unstructured
            filename = job.source_uri.split('/')[-1] or "document"
            parsed_content = await call_unstructured_api(doc_content, filename)

            # Geração do hash SHA256 - garantir codificação UTF-8
            content_sha = hashlib.sha256(parsed_content.encode('utf-8', errors='replace')).hexdigest()

            # Gerar embedding - garantir que o conteúdo é uma string válida
            embedding = await call_openai_embedding(parsed_content)

            # Garantir que o conteúdo a ser salvo está em formato seguro
            safe_content = parsed_content.encode('utf-8', errors='replace').decode('utf-8')

            # Salvar no RAG DB
            new_doc = RagDocuments1536(
                namespace=job.namespace,
                content=safe_content,
                content_sha256=content_sha,
                embedding=embedding,
                document_metadata={'source_uri': job.source_uri}
            )
            
            session.add(new_doc)
            
            # Atualizar status para COMPLETED
            job.status = PyIngestionStatus.COMPLETED
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
                    job.status = PyIngestionStatus.FAILED
                    # Garantir que a mensagem de erro também é segura em termos de codificação
                    error_message = str(e).encode('utf-8', errors='replace').decode('utf-8')
                    job.processing_log = error_message
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
                .filter(IngestionQueue.status == PyIngestionStatus.PENDING)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            job = result.scalar_one_or_none()

            if job:
                # Atualizar status para PROCESSING
                job.status = PyIngestionStatus.PROCESSING
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