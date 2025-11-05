# Resolução do Erro 'CharacterNotInRepertoireError' (PATTERN-003)

## Contexto

Durante o processamento de documentos no sistema COGEP Assistente, ocorria um erro de codificação chamado `CharacterNotInRepertoireError` que impedía o processamento adequado de documentos contendo caracteres especiais. Esse erro resultava na falha dos trabalhos de ingestão com a mensagem "Erro ao processar com Unstructured API:".

## Problema

O sistema apresentava o seguinte comportamento:

1. O endpoint de ingestão criava trabalhos normalmente
2. O worker pegava os trabalhos e tentava processá-los
3. Os trabalhos falhavam com status 'FAILED' e mensagem "Erro ao processar com Unstructured API:"
4. Nenhum registro era salvo em `ai.rag_documents_1536`
5. Ocorriam erros de codificação `CharacterNotInRepertoireError` durante o processamento

## Análise

O problema foi identificado como um erro de fluxo de dados (PATTERN-003):

- **Antes (incorreto)**: bytes (binário do arquivo) eram manipulados como se fossem texto
- **Depois (correto)**: bytes → parse(unstructured) → str → db(text)

## Solução Implementada

Atualizamos o arquivo `worker_service/tasks.py` com as seguintes correções:

### 1. Melhoria na função `call_unstructured_api`:
- Adicionamos tratamento de codificação UTF-8 para garantir que o texto retornado da API do Unstructured seja válido
- Implementamos tratamento de erros específicos para decodificação

```python
# Garantir que o texto retornado está em formato UTF-8
if isinstance(full_text, str):
    full_text = full_text.encode('utf-8', errors='replace').decode('utf-8')
else:
    full_text = str(full_text, 'utf-8', errors='replace')
```

### 2. Melhoria na geração do hash:
- Adicionamos tratamento de codificação ao gerar o SHA256

```python
content_sha = hashlib.sha256(parsed_content.encode('utf-8', errors='replace')).hexdigest()
```

### 3. Melhoria no salvamento no banco:
- Adicionamos tratamento de segurança no conteúdo a ser salvo

```python
# Garantir que o conteúdo a ser salvo está em formato seguro
safe_content = parsed_content.encode('utf-8', errors='replace').decode('utf-8')
```

### 4. Melhoria no tratamento de erros:
- Adicionamos tratamento de codificação nas mensagens de erro

## Resultados

Após a implementação das correções:

1. **Trabalho Processado com Sucesso**: O novo trabalho (ID 10) foi criado e processado com status 'COMPLETED'
2. **Registro Salvo no Banco**: Um novo documento foi salvo em `ai.rag_documents_1536` 
3. **Conteúdo Correto**: O campo `content` contém "Dummy PDF file" e não o binário do PDF
4. **Hash Adequado**: O SHA256 foi gerado corretamente a partir do conteúdo textual

## Fluxo de Dados Corrigido

O fluxo de dados agora segue corretamente o padrão:
1. `doc_content` (bytes) → 2. `call_unstructured_api(doc_content)` → 3. `parsed_content` (str) → 4. `call_openai_embedding(parsed_content)` → 5. `session.add(RagDocuments1536(content=parsed_content, ...))`

## Arquitetura Afetada

- **worker_service/tasks.py**: Correção na tarefa `process_ingestion_job`
- **core/models.py**: Uso correto do modelo `RagDocuments1536`
- **core/database.py**: Uso adequado da sessão assíncrona

## Validação

- Endpoint de ingestão funcional
- Worker processando trabalhos com sucesso
- Dados corretamente salvos em formato textual
- Erros de codificação resolvidos

## Conclusão

A correção implementada resolveu o problema "CharacterNotInRepertoireError" ao garantir o tratamento adequado de codificação UTF-8 em todos os pontos críticos do pipeline de processamento de documentos.

## Próximas Etapas

- Monitorar o sistema para garantir que não ocorram mais falhas devido a caracteres especiais
- Considerar melhorias no tratamento de diferentes formatos de documentos
- Avaliar a possibilidade de implementar validação prévia de codificação dos documentos de entrada