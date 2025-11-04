# Relatório de Contexto do Sistema Cogep

## Visão Geral

O Sistema Cogep é um ambiente de desenvolvimento que integra agentes de IA para auxiliar no desenvolvimento de software e automação de processos. O sistema é composto por múltiplos componentes, incluindo agentes, serviços e um banco de dados PostgreSQL.

## Estado Atual do Banco de Dados

### PostgreSQL - cogep_db

- **Número de tabelas no banco cogep_db**: 1
- **Tabelas existentes**:
  - alembic_version (tabela do sistema Alembic para controle de migrações)
- **Tabelas solicitadas que não existem**:
  - usuarios (não existe)
  - processos (não existe)

## Estrutura do Projeto

O projeto está organizado com os seguintes componentes principais:

- **agent**: Componente do agente principal
- **agent_service**: Serviço que gerencia o agente
- **alembic**: Sistema de migrações de banco de dados
- **core**: Componentes centrais do sistema
- **crm**: Componentes relacionados ao CRM
- **ingestion_service**: Serviço de ingestão de dados
- **CONTEXTO_gemini**: Pasta para contexto de IA

## Ferramentas e Tecnologias Utilizadas

### Banco de Dados
- PostgreSQL
- psycopg2 (driver Python para PostgreSQL)
- Alembic (sistema de migrações de banco de dados)

### Ambiente de Desenvolvimento
- Python
- Docker (através do docker-compose.yml)
- Celery (sistema de tarefas assíncronas - evidenciado pelos arquivos celerybeat)

### Outras Tecnologias
- Qwen Code (IDE e ambiente de desenvolvimento)
- Git (sistema de controle de versão)

## Arquivos de Configuração Importantes

- **requirements.txt**: Lista de dependências do Python
- **docker-compose.yml**: Configuração de containers Docker
- **alembic.ini**: Configuração do sistema de migrações
- **QWEN.md**: Documentação do ambiente Qwen

## Agentes e Serviços

- **Professor Anatoly Petrovich**: Arquiteto de Sistemas Sênior e mentor de desenvolvedores
- **Agentes de IA**: Componentes que interagem com o sistema para criar prompts e executar tarefas
- **Serviços de backend**: Incluindo serviço de ingestão de dados e serviço do agente

## Observações

O sistema tem um banco de dados com apenas a tabela de controle de migrações do Alembic. As tabelas esperadas para usuários e processos ainda não foram criadas. O ambiente está configurado para desenvolvimento com Python, PostgreSQL e containers Docker.

## Próximos Passos

1. Criar as tabelas necessárias para usuários e processos no banco de dados
2. Configurar a integração entre os agentes e os serviços backend
3. Estabelecer conexão adequada com o banco de dados para manipulação de dados
4. Implementar funcionalidades de acordo com os requisitos do sistema