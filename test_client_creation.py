import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from core.models import Clients, Consents

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def test_client_creation():
    async with engine.connect() as conn:
        # Testar se o cliente foi criado
        result = await conn.execute(select(Clients).filter(Clients.whatsapp_id == "554199997777"))
        client = result.first()
        
        if client:
            print(f"Cliente encontrado! ID: {client.id}, whatsapp_id: {client.whatsapp_id}")
            
            # Verificar se tem consentimentos
            consent_result = await conn.execute(select(Consents).filter(Consents.client_id == client.id))
            consent = consent_result.first()
            
            if consent:
                print(f"Consentimento encontrado! ID: {consent.id}, tipo: {consent.consent_type}, dado: {consent.is_given}")
            else:
                print("Nenhum consentimento encontrado para este cliente")
        else:
            print("Nenhum cliente encontrado com este whatsapp_id")

if __name__ == "__main__":
    asyncio.run(test_client_creation())