from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List

from core.database import get_db
from core.models import Clients, Consents, PyConsentType
from agent_service.schemas import ClientBase, ClientResponse, ConsentRequest, ConsentResponse

router = APIRouter(prefix='/api/v1/crm', tags=['CRM / LGPD'])


@router.post('/clients/find_or_create', response_model=ClientResponse)
async def find_or_create_client(
    client_data: ClientBase,
    session: AsyncSession = Depends(get_db)
):
    """
    Endpoint para encontrar ou criar um cliente baseado no whatsapp_id
    """
    # Buscar cliente existente pelo whatsapp_id
    stmt = select(Clients).filter(Clients.whatsapp_id == client_data.whatsapp_id)
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()
    
    # Se cliente existe, retornar o cliente existente
    if client:
        return client
    
    # Se não existe, criar novo cliente
    new_client = Clients(
        whatsapp_id=client_data.whatsapp_id,
        name=client_data.name
    )
    
    session.add(new_client)
    await session.commit()
    await session.refresh(new_client)
    
    return new_client


@router.post('/consents', response_model=ConsentResponse, status_code=201)
async def record_consent(
    consent_data: ConsentRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Endpoint para registrar um consentimento
    """
    # Converter string para enum se necessário
    consent_type = PyConsentType(consent_data.consent_type)
    
    new_consent = Consents(
        client_id=consent_data.client_id,
        consent_type=consent_type,
        is_given=consent_data.is_given
    )
    
    session.add(new_consent)
    await session.commit()
    await session.refresh(new_consent)
    
    return new_consent


@router.get('/consents/{whatsapp_id}', response_model=List[ConsentResponse])
async def get_client_consents(
    whatsapp_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Endpoint para obter todos os consentimentos de um cliente pelo whatsapp_id
    """
    stmt = select(Consents).join(Clients).filter(Clients.whatsapp_id == whatsapp_id).order_by(Consents.timestamp.desc())
    result = await session.execute(stmt)
    consents = result.scalars().all()
    
    return consents