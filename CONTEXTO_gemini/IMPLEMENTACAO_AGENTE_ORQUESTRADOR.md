# Implementação do Agente Orquestrador - Pilar de Orquestração do Sistema

## Contexto

Implementação do 'Agente Orquestrador' no serviço 'agent_service', criando o endpoint de webhook (POST /webhook/evoapi) que gerencia o fluxo de conversação, LGPD e RAG. Esta funcionalidade faz parte do pilar de orquestração do sistema COGEP Assistente e é responsável por gerenciar a interação completa com os usuários, desde a verificação de consentimento até a geração de respostas baseadas em RAG.

## Objetivo

Criar o endpoint de webhook que orquestre o fluxo completo de conversação:
1. Verificar o consentimento LGPD (via CRM API) ANTES de realizar uma busca RAG (via Retrieval API)
2. Processar a lógica de acordo com o estado do consentimento
3. Se consentimento dado: executar busca RAG e gerar resposta com LLM
4. Se consentimento não dado: solicitar consentimento ao usuário
5. Enviar respostas de volta para a EVOAPI
6. Manter o fluxo assíncrono e não-bloqueante

## Arquitetura Implementada

### 1. Estrutura de Arquivos

- `agent_service/schemas.py` - Adição dos schemas Pydantic para o webhook da EVOAPI:
  - `EvoApiMessageBody`: `text: str`
  - `EvoApiMessage`: `body: EvoApiMessageBody`
  - `EvoApiSender`: `id: str`
  - `EvoApiPayload`: `sender: EvoApiSender`, `message: EvoApiMessage`

- `agent_service/api/orchestrator.py` - Implementação do endpoint de webhook e lógica de orquestração:
  - Função auxiliar `get_query_embedding()` para gerar embedding da query
  - Função auxiliar `send_response_to_evoapi()` para enviar respostas
  - Função `process_conversation()` com a lógica completa de orquestração
  - Endpoint `handle_evoapi_webhook()` como ponto de entrada

- `agent_service/main.py` - Registro do router do orquestrador

### 2. Fluxo de Dados

1. **Recebimento do Webhook**:
   - Endpoint `/webhook/evoapi` recebe o payload da EVOAPI
   - Extrai `whatsapp_id` e `user_query`

2. **Etapa CRM (Find/Create)**:
   - Busca cliente existente pelo `whatsapp_id`
   - Se não existir, cria novo cliente

3. **Etapa LGPD (Verificar Consentimento)**:
   - Verifica se o cliente deu consentimento para LGPD_V1
   - Se não houver consentimento, solicita ao usuário

4. **Fluxo LGPD (Solicitação de Consentimento)**:
   - Se o usuário responde "Sim", registra o consentimento
   - Se o usuário responde outra coisa, continua pedindo consentimento

5. **Fluxo RAG (Se Consentimento Dado)**:
   - Gera embedding para a query do usuário
   - Executa busca vetorial no PGVector
   - Recupera os chunks mais relevantes

6. **Etapa LLM (Gerar Resposta)**:
   - Formata o prompt com o contexto e a pergunta do usuário
   - Chama o modelo GPT-4o-mini para gerar a resposta

7. **Etapa Resposta**:
   - Envia a resposta gerada de volta para a EVOAPI
   - Retorna status "ok" imediatamente para o webhook

### 3. Tecnologias Utilizadas

- FastAPI
- Pydantic
- SQLAlchemy (Async)
- OpenAI (ChatCompletion)
- httpx (para enviar resposta à EVOAPI)
- BackgroundTasks (para processamento não-bloqueante)

## Implementação Detalhada

### Componentes Principais

1. **Endpoint de Webhook**:
   - `POST /webhook/evoapi`
   - Processa a requisição em segundo plano para não bloquear
   - Retorna imediatamente `{"status": "ok"}`

2. **Lógica de Orquestração**:
   - Verifica consentimento antes de executar RAG
   - Implementa o fluxo LGPD -> RAG -> LLM
   - Processa em segundo plano usando BackgroundTasks

3. **Funções Auxiliares**:
   - `get_query_embedding()`: Gera embedding usando OpenAI
   - `send_response_to_evoapi()`: Envia resposta de volta para EVOAPI

### Código Final

O código implementa corretamente:
- A verificação de consentimento LGPD antes do RAG
- O processamento em segundo plano para manter a resposta rápida
- A lógica de busca RAG e geração de resposta com LLM
- O envio de respostas de volta para a EVOAPI

## Resultados Validados

### 1. Funcionalidade Básica
- Endpoint de webhook respondendo corretamente
- Criação de clientes via webhook
- Verificação e registro de consentimento

### 2. Casos de Teste

1. **Criação de novo cliente**:
   - Request: Webhook com novo `whatsapp_id`
   - Resultado: Cliente criado no banco de dados

2. **Solicitação de consentimento**:
   - Request: Webhook de cliente sem consentimento
   - Resultado: Processo de solicitação de consentimento iniciado

3. **Registro de consentimento**:
   - Request: Webhook com resposta "Sim" de cliente sem consentimento
   - Resultado: Consentimento LGPD_V1 registrado no banco de dados

4. **Fluxo RAG (com consentimento)**:
   - Request: Webhook com query de cliente com consentimento
   - Resultado: Processamento do fluxo RAG -> LLM -> resposta

### 3. Validação de Performance

- Resposta ao webhook: Imediata (200 OK)
- Processamento em segundo plano: Não bloqueante
- Latência total: Pode ser alta devido ao LLM, mas é desacoplada do webhook

## Integração com Padrões

### Padrões de Arquitetura
- **KB 1**: Resposta rápida ao webhook (200 OK imediato)
- **Pilar de Orquestração**: Implementação do 'Agente Principal' que une os outros pilares
- **Desacoplamento**: Uso de BackgroundTasks para processamento não-bloqueante

### Padrões de Implementação
- **API RESTful**: Endpoint padronizado com método HTTP apropriado
- **Verificação de LGPD**: Bloqueia o RAG até que o consentimento seja dado
- **Integração com EVOAPI**: Envio de respostas de volta ao sistema externo
- **Uso de LLM**: Geração de respostas inteligentes com contexto RAG

## Conclusão

O Agente Orquestrador foi implementado com sucesso, atendendo a todos os requisitos técnicos e de validação. O sistema agora pode:

1. Receber webhooks da EVOAPI e processar as mensagens
2. Verificar o consentimento LGPD antes de executar qualquer operação de RAG
3. Executar o fluxo completo de RAG e LLM para gerar respostas inteligentes
4. Enviar respostas de volta para a EVOAPI
5. Manter o fluxo de conversação assíncrono e não-bloqueante

Este componente é o núcleo do sistema COGEP Assistente, orquestrando todos os outros pilares (RAG, CRM/LGPD) e mantendo a experiência de conversação com os usuários.