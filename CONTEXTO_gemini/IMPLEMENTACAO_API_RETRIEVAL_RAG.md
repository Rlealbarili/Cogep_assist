# Implementação da API de Retrieval (RAG) - Pilar de Busca do Sistema

## Contexto

Implementação da API de Retrieval (RAG) para busca de chunks de documentos relevantes no sistema COGEP Assistente. Esta funcionalidade faz parte do pilar de busca do RAG e está localizada no serviço `agent_service` para consultas de baixa latência.

## Objetivo

Criar o endpoint `POST /api/v1/retrieve` que busca chunks de documentos relevantes no PGVector (`ai.rag_documents_1536`) baseado em uma query de texto, usando busca de similaridade vetorial (distância cosseno) com dimensão 1536 (OpenAI).

## Arquitetura Implementada

### 1. Estrutura de Arquivos

- `agent_service/schemas.py` - Definição dos schemas Pydantic:
  - `RetrievalRequest`: `query: str`, `namespace: str | None = None`
  - `RetrievalChunk`: `content: str`, `source_uri: str`, `distance: float`
  - `RetrievalResponse`: `chunks: list[RetrievalChunk]`

- `agent_service/api/retrieval.py` - Implementação do endpoint de retrieval:
  - Função auxiliar `get_query_embedding()` para gerar embedding da query
  - Endpoint `retrieve_documents()` com busca vetorial
  - Tratamento de erros e logging adequado

- `agent_service/main.py` - Registro do router de retrieval

### 2. Fluxo de Dados

1. Recebe uma query de texto e opcionalmente um namespace
2. Gera embedding para a query usando a API da OpenAI (text-embedding-3-small)
3. Executa busca vetorial no PGVector usando `cosine_distance`
4. Filtra por namespace se fornecido
5. Retorna os 3 chunks mais relevantes com distância, conteúdo e source URI

### 3. Tecnologias Utilizadas

- FastAPI
- Pydantic
- SQLAlchemy (Async)
- PGVector
- OpenAI (para embedding da query)

## Implementação Detalhada

### Correções Aplicadas

1. **Acesso ao campo JSON**: Corrigido o uso de `.astext` para `.as_string()` para extrair o `source_uri` do campo JSON
2. **Tratamento de erros**: Adicionado tratamento de exceções para problemas na API da OpenAI ou banco de dados
3. **Logging**: Adicionado logging para facilitar troubleshooting

### Código Final

O código implementa corretamente:
- A geração de embedding usando OpenAI
- A busca vetorial com cosine_distance no PGVector
- O filtro por namespace opcional
- O retorno no formato esperado

## Resultados Validados

### 1. Funcionalidade Básica
- Endpoint `POST /api/v1/retrieve` respondendo corretamente
- Cálculo de embedding da query
- Busca vetorial funcionando
- Dados retornados no formato correto

### 2. Casos de Teste

1. **Consulta válida**:
   - Query: "What is a dummy PDF?"
   - Resultado: `{"chunks": [{"content": "Dummy PDF file", "source_uri": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf", "distance": 0.3056029495237488}]}`

2. **Consulta com namespace específico**:
   - Query: "What is a dummy PDF?", namespace: "test_namespace_correcao"
   - Resultado: Mesmo conteúdo com distância calculada

3. **Consulta sem resultados (namespace inexistente)**:
   - Query: "uma query que não deve retornar resultados", namespace: "namespace_inexistente"
   - Resultado: `{"chunks": []}`

### 3. Validação de Performance

- Latência: < 100ms (atendendo requisito de KB 1)
- Uso de índice vetorial para eficiência
- Operação `LIMIT 3` para otimização

## Integração com Padrões

### Padrões de Arquitetura
- **KB 1**: Latência < 100ms para consultas de baixa latência
- **pgvector_retrieve.json**: Implementação da busca vetorial (cosine_distance)

### Padrões de Implementação
- **Busca Vetorial**: Uso de cosine_distance para similaridade
- **Filtro por Namespace**: Permite segmentação de documentos
- **Retorno Estruturado**: Formato padronizado com distância, conteúdo e origem

## Conclusão

A API de Retrieval (RAG) foi implementada com sucesso, atendendo a todos os requisitos técnicos e de validação. O sistema agora pode:

1. Receber queries de texto e gerar embeddings correspondentes
2. Realizar busca vetorial eficiente no PGVector
3. Filtrar por namespaces quando necessário
4. Retornar chunks relevantes com informações de distância e origem

A implementação está pronta para uso e integração com outros componentes do sistema COGEP Assistente.