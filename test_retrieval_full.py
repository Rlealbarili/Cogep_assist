import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from core.models import RagDocuments1536

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def test_full_retrieval():
    async with engine.connect() as conn:
        # Testar a consulta completa que usamos no endpoint
        query_vector = [0.1] * 1536  # Vetor de exemplo
        
        stmt = select(
            RagDocuments1536.content,
            RagDocuments1536.document_metadata['source_uri'].astext,
            RagDocuments1536.embedding.cosine_distance(query_vector).label('distance')
        ).limit(3)
        
        result = await conn.execute(stmt)
        rows = result.all()
        
        print(f"Consulta completa funcionou! Resultados: {len(rows)}")
        for i, row in enumerate(rows):
            print(f"Resultado {i+1}:")
            print(f"  Conteúdo: {row[0][:50]}...")
            print(f"  Source URI: {row[1]}")
            print(f"  Distância: {row[2]}")

if __name__ == "__main__":
    asyncio.run(test_full_retrieval())