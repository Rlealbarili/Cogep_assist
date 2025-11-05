import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import json

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def verify_rag_documents():
    async with engine.connect() as conn:
        # Consultar os 5 documentos mais recentes
        result = await conn.execute(text("""
            SELECT id, namespace, content, content_sha256, created_at
            FROM ai.rag_documents_1536
            ORDER BY created_at DESC
            LIMIT 5
        """))
        
        rows = result.fetchall()
        
        print("Documentos mais recentes em ai.rag_documents_1536:")
        for row in rows:
            print(f"ID: {row[0]}, Namespace: {row[1]}")
            print(f"Content (first 100 chars): {repr(row[2][:100])}")
            print(f"Content SHA256: {row[3]}")
            print(f"Created: {row[4]}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(verify_rag_documents())