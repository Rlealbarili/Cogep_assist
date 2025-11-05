import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select
from core.models import Tickets, Clients

# Configuração do banco de dados
DATABASE_URL = "postgresql+asyncpg://agent_app:Qwe123rty456@localhost:5432/cogep_db"
engine = create_async_engine(DATABASE_URL)

async def check_tickets():
    async with engine.connect() as conn:
        # Consultar os tickets recentes
        result = await conn.execute(select(Tickets).order_by(Tickets.id.desc()).limit(5))
        tickets = result.fetchall()
        
        print("Tickets mais recentes:")
        for ticket in tickets:
            print(f"ID: {ticket.id}, Client ID: {ticket.client_id}, Description: {ticket.description[:50]}..., Status: {ticket.status}, Created: {ticket.created_at}")
        
        # Contar total de tickets
        result = await conn.execute(select(Tickets))
        all_tickets = result.fetchall()
        print(f"\nTotal de tickets: {len(all_tickets)}")

if __name__ == "__main__":
    asyncio.run(check_tickets())