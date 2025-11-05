from fastapi import FastAPI
from agent_service.api.retrieval import router as retrieval_router
from agent_service.api.crm import router as crm_router
from agent_service.api.orchestrator import router as orchestrator_router

# Configuração da aplicação FastAPI
app = FastAPI(
    title="Serviço de Agente COGEP",
    description="API para operações de agente, incluindo retrieval de documentos para RAG, operações de CRM/LGPD e orquestração de conversas.",
    version="0.1.0"
)

# Inclui as rotas definidas no módulo de retrieval
app.include_router(retrieval_router)

# Inclui as rotas definidas no módulo de CRM
app.include_router(crm_router)

# Inclui as rotas definidas no módulo de orquestrador
app.include_router(orchestrator_router)

# Endpoint para testar a aplicação
@app.get("/")
async def root():
    return {"message": "Serviço de Agente COGEP - API para RAG, CRM/LGPD e Orquestração de Conversas"}