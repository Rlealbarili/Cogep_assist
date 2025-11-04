Com certeza. Recomeçar com uma fundação limpa, aplicando todo o aprendizado das nossas sessões de prototipagem e depuração, é a decisão correta.

Aqui está um relatório detalhado de ponta-a-ponta, focado na arquitetura de "código puro" que planejamos, para servir como seu guia de desenvolvimento para o projeto Agente COGEP.

---

**Relatório de Projeto: Agente COGEP (Arquitetura de Código Puro) \- MVP**

**1\. Visão Geral e Objetivos do MVP**

O objetivo é construir a versão 1.0 (MVP) do **Agente COGEP**, um assistente de IA conversacional para o primeiro nível de atendimento ao cliente via WhatsApp. O sistema será construído inteiramente em código (Python/FastAPI) para garantir estabilidade, performance e escalabilidade, resolvendo os problemas de esgotamento de recursos que enfrentamos no protótipo.

Os pilares do MVP são:

* **RAG (Retrieval-Augmented Generation):** O agente responderá perguntas com base em uma base de conhecimento privada (documentos da COGEP).  
* **CRM Mínimo e LGPD:** O agente identificará o cliente, registrará o consentimento de uso de dados (LGPD) e, futuramente, abrirá tickets.  
* **Arquitetura Desacoplada:** A lógica de IA pesada será separada do processo principal de conversação para garantir que o agente nunca trave.

**2\. Arquitetura de Sistema (Código Puro)**

Abandonaremos a abordagem monolítica onde um único serviço (n8n) fazia tudo. A nova arquitetura será composta por **três serviços de backend principais**, rodando em contêineres Docker e se comunicando internamente.

Isso isola as cargas de trabalho:

* **Agente Principal (FastAPI):** Leve, rápido, gerencia a conversa.  
* **API de Retrieval (FastAPI):** O "músculo" do RAG. Faz o trabalho pesado de busca vetorial. Se ele consumir muita memória, ele pode ser reiniciado sem derrubar o agente principal.  
* **Worker de Ingestão (Celery):** Processo de background que alimenta o banco de dados sem impactar o atendimento ao vivo.

Snippet de código

graph TD  
    subgraph Cliente  
        A(Usuário WhatsApp) \<--\> B(EVOAPI)  
    end

    subgraph VPS (Produção)  
        B \-- Webhook \--\> C\[Agente Principal API (FastAPI)\]  
        C \-- Pergunta \--\> D\[API de Retrieval (FastAPI)\]  
        D \-- Busca \--\> E\[(ai-postgres / pgvector)\]  
        D \-- Contexto \--\> C  
        C \-- Pergunta \+ Contexto \--\> F\[OpenAI API\]  
        F \-- Resposta \--\> C  
        C \-- Resposta \--\> B  
        C \-- Dados do Cliente \--\> E  
    end

    subgraph Processamento de Background (Local ou VPS)  
        G\[Admin\] \-- Adiciona Job \--\> H(Fila de Ingestão)  
        I\[Worker de Ingestão (Celery)\] \-- Pega Job \--\> H  
        I \-- Processa \--\> J(Unstructured API)  
        I \-- Embed \--\> F  
        I \-- Salva Chunks \--\> E  
    end

**3\. Detalhamento dos Componentes (MVP)**

**3.1. O Banco de Dados (A Fundação)**

* **Tecnologia:** PostgreSQL 16 \+ pgvector (rodando em Docker).  
* **Banco Principal:** cogep\_db (local) / ai\_agents (produção).  
* **Schemas:**  
  * ai: Para tabelas relacionadas a RAG e ingestão.  
  * crm: Para tabelas de clientes e conformidade.  
* **Tabelas Essenciais:**  
  * ai.rag\_documents\_1536: Armazena os chunks.  
    * id (UUID), namespace (VARCHAR), content\_sha256 (VARCHAR), chunk\_idx (INT), content (TEXT), metadata (JSONB), embedding (VECTOR(1536)).  
    * **Índices:** HNSW para embedding, B-tree para namespace, e um UNIQUE em (namespace, content\_sha256) para idempotência.  
  * ai.ingestion\_queue: A fila de orquestração.  
    * id (UUID), source\_uri (TEXT), namespace (VARCHAR), status (VARCHAR \- pending, processing, completed, failed), attempts (INT), last\_error (TEXT).  
  * crm.clients: Registro básico de usuários.  
    * id (UUID), whatsapp\_id (VARCHAR, UNIQUE), name (VARCHAR), created\_at.  
  * crm.consents: Registro de conformidade LGPD.  
    * id (UUID), client\_id (FK para crm.clients), consent\_given (BOOLEAN), timestamp.

**3.2. O Pipeline de Ingestão (Worker Assíncrono)**

* **Tecnologia:** Celery (rodando em Python).  
* **Gatilho:** Monitora a tabela ai.ingestion\_queue (usando SELECT ... FOR UPDATE SKIP LOCKED).  
* **Processo (para cada job):**  
  1. **Fetch:** Baixa o conteúdo da source\_uri (usando httpx).  
  2. **Parse:** Envia o conteúdo bruto para a **Unstructured API** (rodando em Docker) para extrair texto limpo.  
  3. **Chunking:** Aplica uma estratégia de chunking recursivo (baseado em \\n\\n, \\n, ) no texto limpo.  
  4. **Hash:** Para cada chunk, calcula um hash SHA256 do seu conteúdo.  
  5. **Embed:** Envia o texto do chunk para a API da OpenAI (text-embedding-3-small).  
  6. **Upsert:** Salva o chunk, embedding, hash e metadados no ai.rag\_documents\_1536 usando INSERT ... ON CONFLICT (namespace, content\_sha256) DO NOTHING.  
  7. **Status:** Atualiza o status do job na ai.ingestion\_queue para completed ou failed.

**3.3. O Microserviço de Retrieval (O "Músculo" RAG)**

* **Tecnologia:** FastAPI (API Python).  
* **Endpoint Principal:** POST /retrieve  
* **Input (JSON):** { "query": "texto da pergunta", "namespace": "cogep/public" }  
* **Processo:**  
  1. Recebe a requisição.  
  2. Chama a API da OpenAI para gerar o embedding da query.  
  3. Executa uma query KNN (similaridade de cosseno) no ai.rag\_documents\_1536 (pgvector).  
  4. Formata e retorna os topK chunks de texto como uma resposta JSON.

**3.4. O Agente Principal (O "Rosto")**

* **Tecnologia:** FastAPI (API Python).  
* **Endpoint Principal:** POST /webhook/evoapi  
* **Processo:**  
  1. Recebe o webhook da EVOAPI (JSON).  
  2. Extrai a pergunta (message.conversation) e o ID do remetente (sender.id).  
  3. Chama o módulo de CRM: cliente \= crm.get\_or\_create\_client(sender.id).  
  4. Verifica o consentimento: if not crm.check\_consent(cliente.id): ... (lida com o fluxo de aceite da LGPD).  
  5. Chama o Microserviço de Retrieval: contexto \= httpx.post("http://retrieval-api:8001/retrieve", ...)  
  6. Constrói o Prompt: Combina as instruções do sistema, o contexto recuperado e a pergunta do usuário.  
  7. Chama a API da OpenAI: resposta\_texto \= openai.ChatCompletion.create(...) (gpt-4o-mini).  
  8. Envia a Resposta: Chama a API da EVOAPI (httpx.post(...)) para enviar a resposta\_texto de volta ao sender.id.

**4\. Ferramentas e Stack de Tecnologia (Resumo)**

* **Linguagem:** Python 3.11+  
* **Frameworks de API:** FastAPI  
* **Fila de Tarefas:** Celery (com Redis como broker)  
* **Banco de Dados:** PostgreSQL 16 \+ pgvector  
* **ORM/Conexão DB:** SQLAlchemy (com asyncpg)  
* **Migrações de DB:** Alembic  
* **Cliente HTTP:** httpx (para chamadas de API assíncronas)  
* **Parsing de Documentos:** Unstructured API (Docker)  
* **Modelos de IA:**  
  * Embeddings: OpenAI text-embedding-3-small  
  * Chat: OpenAI gpt-4o-mini  
* **Infraestrutura:** Docker, Docker Compose  
* **Reverse Proxy (VPS):** Traefik  
* **Canal WhatsApp:** EVOAPI  
* **Configuração:** python-dotenv e pydantic-settings (para ler arquivos .env)  
* **Ferramentas de Suporte:** DBeaver (Cliente BD), Postman (Testes de API), Cursor/Gemini CLI (Desenvolvimento)

**5\. Fluxo de Ponta-a-Ponta (MVP)**

1. Um usuário envia "O que é REURB?" via WhatsApp.  
2. A EVOAPI encaminha a mensagem para o webhook /webhook/evoapi do **Agente Principal**.  
3. O Agente Principal identifica o usuário (sender.id) e verifica o consentimento LGPD no crm.consents.  
4. O Agente chama a **API de Retrieval** (POST /retrieve, query="O que é REURB?").  
5. A API de Retrieval gera o embedding da pergunta, busca no pgvector e retorna 3 chunks relevantes da página cogep.eng.br/reurb/.  
6. O Agente Principal constrói um prompt (ex: "Contexto: \[chunks...\] Pergunta: O que é REURB?") e envia para a OpenAI.  
7. A OpenAI gera uma resposta.  
8. O Agente Principal envia a resposta para a EVOAPI, que a entrega ao usuário.

---

