import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
import numpy as np
from core.models import RagDocuments1536

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def test_cosine_distance():
    async with engine.connect() as conn:
        # Primeiro, vamos obter um embedding existente para usar como exemplo
        result = await conn.execute(select(RagDocuments1536).limit(1))
        row = result.first()
        
        if row and row.embedding is not None:
            print(f"Embedding encontrado com tamanho: {len(row.embedding)}")
            
            # Simular um embedding de query
            query_vector = [0.1] * 1536  # Vetor de exemplo com 1536 dimensões
            
            # Agora vamos tentar a operação de cosine_distance diretamente no SQL
            from pgvector.sqlalchemy import Vector
            stmt = select(
                RagDocuments1536.content,
                RagDocuments1536.embedding.cosine_distance(query_vector).label('distance')
            ).limit(1)
            
            result = await conn.execute(stmt)
            rows = result.all()
            
            print(f"Consulta com cosine_distance funcionou! Resultados: {len(rows)}")
            for row in rows:
                print(f"Conteúdo: {row[0][:50]}..., Distância: {row[1]}")
        else:
            print("Nenhum embedding encontrado para teste")

if __name__ == "__main__":
    asyncio.run(test_cosine_distance())