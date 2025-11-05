from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import openai
import httpx
import os
import logging
from typing import List

from core.database import get_db
from core.models import Clients, Consents, RagDocuments1536, Tickets, PyConsentType, PyTicketStatus
from agent_service.schemas import EvoApiPayload
from pgvector.sqlalchemy import Vector

# Configuração do logger
log = logging.getLogger(__name__)

router = APIRouter(prefix='/webhook', tags=['Agent Orchestrator'])


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


async def get_user_intent(query: str) -> str:
    """
    Classifica a intenção do usuário como 'PERGUNTA_RAG' ou 'PEDIDO_SUPORTE'
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise Exception("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
    
    client = openai.AsyncOpenAI(api_key=openai_api_key)
    
    system_prompt = "Você é um classificador. A mensagem do usuário é uma PERGUNTA_RAG ou um PEDIDO_SUPORTE? Responda *apenas* com o nome da classe."
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        max_tokens=20,
        temperature=0.1
    )
    
    intent = response.choices[0].message.content.strip()
    return intent


async def send_response_to_evoapi(whatsapp_id: str, response_text: str):
    """
    Envia a resposta de volta para a EVOAPI
    """
    # Esta é uma implementação simulada - substitua com a verdadeira API da EVOAPI
    evoapi_url = os.getenv("EVOAPI_WEBHOOK_URL")
    if not evoapi_url:
        log.error("EVOAPI_WEBHOOK_URL não configurada")
        return
    
    payload = {
        "whatsapp_id": whatsapp_id,
        "message": response_text
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(evoapi_url, json=payload)
            response.raise_for_status()
            log.info(f"Resposta enviada para {whatsapp_id}: {response_text}")
        except httpx.HTTPStatusError as e:
            log.error(f"Erro ao enviar resposta para {whatsapp_id}: {e}")
        except Exception as e:
            log.error(f"Erro inesperado ao enviar resposta para {whatsapp_id}: {e}")


async def process_conversation(payload: EvoApiPayload, session: AsyncSession):
    """
    Processa a conversação completa: LGPD -> Classificação de Intenção -> RAG ou Tickets
    """
    whatsapp_id = payload.sender.id
    user_query = payload.message.body.text
    
    # Etapa CRM (Find/Create)
    stmt = select(Clients).filter(Clients.whatsapp_id == whatsapp_id)
    result = await session.execute(stmt)
    client = result.scalar_one_or_none()
    
    if not client:
        client = Clients(whatsapp_id=whatsapp_id)
        session.add(client)
        await session.commit()
        await session.refresh(client)
    
    # Etapa LGPD (Verificar consentimento)
    stmt = select(Consents).filter(
        Consents.client_id == client.id,
        Consents.consent_type == PyConsentType.LGPD_V1,
        Consents.is_given == True
    )
    result = await session.execute(stmt)
    consent_given = result.scalar_one_or_none()
    
    # Fluxo LGPD (Se não houver consentimento)
    if not consent_given:
        if user_query.lower().strip() in ["sim", "s", "yes", "y"]:
            # Registrar consentimento
            new_consent = Consents(
                client_id=client.id,
                consent_type=PyConsentType.LGPD_V1,
                is_given=True
            )
            session.add(new_consent)
            await session.commit()
            await session.refresh(new_consent)
            response_text = "Obrigado pelo seu consentimento! Agora posso te ajudar com suas dúvidas ou registrar um ticket de suporte."
        else:
            response_text = "Olá! Para continuar, preciso do seu consentimento (LGPD)... (Sim/Não)"
        # Enviar resposta para EVOAPI
        await send_response_to_evoapi(whatsapp_id, response_text)
        return
    else:
        # Após verificar consentimento, classificar intenção
        intent = await get_user_intent(user_query)
        log.info(f"Intenção detectada para {whatsapp_id}: {intent}")
        
        if intent == 'PERGUNTA_RAG':
            # Fluxo RAG (Se houver consentimento e for pergunta)
            query_vector = await get_query_embedding(user_query)
            
            stmt = select(
                RagDocuments1536.content
            ).filter(
                RagDocuments1536.embedding.cosine_distance(query_vector) < 0.8  # Apenas resultados relevantes
            ).order_by(
                RagDocuments1536.embedding.cosine_distance(query_vector)
            ).limit(3)
            
            context_result = await session.execute(stmt)
            context_chunks = context_result.scalars().all()
            
            # Etapa LLM (Gerar Resposta)
            context_str = "\n\n".join(context_chunks)
            
            # Preparar o prompt para o LLM
            prompt = f"""Contexto: {context_str}\n\nPergunta: {user_query}\n\nResponda com base no contexto fornecido. Se não encontrar informações relevantes no contexto, diga que não encontrou informações suficientes para responder."""
            
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise Exception("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
            
            client_openai = openai.AsyncOpenAI(api_key=openai_api_key)
            
            response = await client_openai.chat.completions.create(
                model="gpt-4o-mini",  # Usando gpt-4o-mini como especificado
                messages=[
                    {"role": "system", "content": "Você é um assistente útil que responde com base no contexto fornecido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            llm_response_text = response.choices[0].message.content
            response_text = llm_response_text
            
        elif intent == 'PEDIDO_SUPORTE':
            # Lógica de Criação de Ticket
            new_ticket = Tickets(
                client_id=client.id,
                description=user_query,
                status=PyTicketStatus.OPEN
            )
            session.add(new_ticket)
            await session.commit()
            await session.refresh(new_ticket)
            
            response_text = f'Obrigado. Seu ticket de suporte (ID: {new_ticket.id}) foi aberto com a descrição: "{user_query}". Em breve, um atendente humano entrará em contato.'
        else:  # Fallback
            response_text = 'Desculpe, não consegui entender sua solicitação. Posso ajudar com dúvidas ou abrir um chamado de suporte.'
    
    # Etapa Resposta: Enviar resposta para EVOAPI
    await send_response_to_evoapi(whatsapp_id, response_text)


@router.post('/evoapi')
async def handle_evoapi_webhook(
    payload: EvoApiPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """
    Endpoint para lidar com o webhook da EVOAPI
    """
    # Processar a conversação como uma tarefa em segundo plano para não bloquear o webhook
    background_tasks.add_task(process_conversation, payload, session)
    
    # Retornar OK imediatamente
    return {"status": "ok"}