import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from core.models import RagDocuments1536
import os

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def test_retrieval():
    async with engine.connect() as conn:
        # Testar se a conexão com o banco e a tabela estão funcionando
        result = await conn.execute(select(RagDocuments1536).limit(1))
        row = result.first()
        
        if row:
            print(f"Conexão bem-sucedida! Primeira linha: ID={row.id}, Namespace={row.namespace}")
            print(f"Conteúdo (primeiros 50 chars): {row.content[:50]}...")
            print(f"Tipo do embedding: {type(row.embedding)}")
            print(f"Tamanho do embedding: {len(row.embedding) if row.embedding else 'N/A'}")
            # Verificar se o embedding é uma array numpy e obter seu tamanho
            if hasattr(row.embedding, '__len__'):
                print(f"Tamanho do embedding: {len(row.embedding)}")
            else:
                print("Tamanho do embedding: N/A")
        else:
            print("Nenhuma linha encontrada na tabela rag_documents_1536")

if __name__ == "__main__":
    asyncio.run(test_retrieval())