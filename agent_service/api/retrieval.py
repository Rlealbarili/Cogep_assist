from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import openai
import os
import logging
from typing import List

from core.database import get_db
from core.models import RagDocuments1536
from agent_service.schemas import RetrievalRequest, RetrievalChunk, RetrievalResponse
from pgvector.sqlalchemy import Vector

# Configuração do logger
log = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v1', tags=['RAG Retrieval'])


async def get_query_embedding(text: str) -> list[float]:
    """
    Gera embedding para a query usando a API da OpenAI
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise Exception("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
    
    client = openai.AsyncOpenAI(api_key=openai_api_key)
    
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    
    return response.data[0].embedding


@router.post('/retrieve', response_model=RetrievalResponse)
async def retrieve_documents(
    request: RetrievalRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Endpoint para buscar chunks de documentos relevantes baseado em uma query de texto
    """
    try:
        # Gerar embedding para a query
        query_vector = await get_query_embedding(request.query)
        
        # Construir a query SQLAlchemy
        stmt = select(
            RagDocuments1536.content,
            RagDocuments1536.document_metadata['source_uri'].as_string().label('source_uri'),
            RagDocuments1536.embedding.cosine_distance(query_vector).label('distance')
        )
        
        # Adicionar filtro de namespace (se fornecido)
        if request.namespace:
            stmt = stmt.filter(RagDocuments1536.namespace == request.namespace)
        
        # Ordenar e limitar
        stmt = stmt.order_by('distance').limit(3)
        
        # Executar
        results = await session.execute(stmt)
        rows = results.all()
        
        # Formatar a resposta
        chunks = []
        for row in rows:
            chunk = RetrievalChunk(
                content=row[0],
                source_uri=row[1],
                distance=float(row[2])
            )
            chunks.append(chunk)
        
        return RetrievalResponse(chunks=chunks)
    except Exception as e:
        log.error(f"Erro ao processar requisição de retrieval: {str(e)}", exc_info=True)
        raise e