import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from core.models import Clients, Consents

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def verify_consent_user():
    async with engine.connect() as conn:
        # Buscar clientes que tenham consentimento
        result = await conn.execute(
            select(Clients.id, Clients.whatsapp_id, Consents.id, Consents.consent_type, Consents.is_given)
            .join(Consents, Clients.id == Consents.client_id)
            .filter(Consents.consent_type == 'LGPD_V1', Consents.is_given == True)
        )
        rows = result.fetchall()
        
        print("Clientes com consentimento encontrado:")
        for row in rows:
            client_id, whatsapp_id, consent_id, consent_type, is_given = row
            print(f"Cliente ID: {client_id}, WhatsApp ID: {whatsapp_id}")
            print(f"Consentimento ID: {consent_id}, Tipo: {consent_type}, Dado: {is_given}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(verify_consent_user())