# Guia de Configuração - Cogep Assist

## 1. Pré-requisitos

- Docker e Docker Compose instalados na sua máquina local
- Git configurado
- Python 3.11+ (para desenvolvimento local)

## 2. Configuração Inicial

### 2.1. Clonar o Repositório

```bash
git clone https://github.com/Rlealbarili/Cogep_assist.git
cd Cogep_assist
```

### 2.2. Configurar Variáveis de Ambiente

O arquivo `.env.example` serve como template. Copie-o para criar seu arquivo `.env` local:

```bash
cp .env.example .env
```

### 2.3. Gerar Senhas Seguras

**IMPORTANTE:** Substitua as senhas placeholder no arquivo `.env` por senhas fortes.

Você pode gerar senhas seguras usando:

```bash
# No Linux/Mac
openssl rand -base64 32

# Ou com Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Edite o arquivo `.env` e substitua:
- `sua_senha_segura_aqui` → senha gerada para PostgreSQL
- `trading_password_segura` → senha gerada para TimescaleDB

## 3. Inicializar os Bancos de Dados

### 3.1. Subir os Containers

```bash
docker-compose up -d
```

Este comando irá:
- ✅ Criar o container PostgreSQL com PGVector (para RAG)
- ✅ Criar o container TimescaleDB (para séries temporais de trading)
- ✅ Criar o container Redis (para cache e Pub/Sub)
- ✅ Aplicar as credenciais do arquivo `.env` aos bancos

### 3.2. Verificar Status dos Containers

```bash
docker-compose ps
```

Você deve ver 3 containers rodando:
- `cogep_assist_postgres` (porta 5432)
- `cogep_assist_timescale` (porta 5433)
- `cogep_assist_redis` (porta 6379)

### 3.3. Verificar Logs (se necessário)

```bash
# Todos os containers
docker-compose logs

# Container específico
docker-compose logs postgres_db
docker-compose logs timescale_db
docker-compose logs redis
```

## 4. Aplicar Migrações do Banco de Dados

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Aplicar migrações do Alembic
alembic upgrade head
```

## 5. Testar Conexão com os Bancos

### 5.1. PostgreSQL (RAG)

```bash
docker exec -it cogep_assist_postgres psql -U cogep_admin -d cogep_assist
```

### 5.2. TimescaleDB (Trading)

```bash
docker exec -it cogep_assist_timescale psql -U trading_admin -d trading_timeseries
```

### 5.3. Redis

```bash
docker exec -it cogep_assist_redis redis-cli ping
# Deve retornar: PONG
```

## 6. Parar os Containers

```bash
# Parar sem remover volumes (dados persistem)
docker-compose stop

# Parar e remover containers (volumes persistem)
docker-compose down

# CUIDADO: Remover tudo incluindo volumes (APAGA DADOS!)
docker-compose down -v
```

## 7. Recriar Containers com Novas Credenciais

Se você alterar as senhas no `.env`, precisa recriar os containers:

```bash
# Parar e remover containers
docker-compose down

# Remover volumes antigos (isso apaga os dados!)
docker volume rm cogep_assist_pg_data cogep_assist_timescale_data

# Recriar com novas credenciais
docker-compose up -d
```

## 8. Estrutura dos Bancos de Dados

### PostgreSQL (cogep_assist)
- **Porta:** 5432
- **Uso:** RAG, embeddings, dados estruturados
- **Extensões:** PGVector para busca vetorial

### TimescaleDB (trading_timeseries)
- **Porta:** 5433
- **Uso:** Séries temporais do sistema de trading
- **Ideal para:** Candles, ticks, indicadores técnicos

### Redis
- **Porta:** 6379
- **Uso:** Cache, Celery broker, Pub/Sub para microserviços

## 9. Próximos Passos

1. Configure a API do OpenAI no `.env` (OPENAI_API_KEY)
2. Configure o Ollama localmente para usar Qwen 2.5:14b
3. Execute as migrações do Alembic
4. Inicie os workers do Celery
5. Execute os testes para validar a configuração

## Troubleshooting

### Erro: "port is already allocated"
Outro serviço está usando a porta. Altere no `.env`:
- `POSTGRES_PORT=5433` (se 5432 estiver ocupada)
- `TIMESCALE_PORT=5434` (se 5433 estiver ocupada)
- `REDIS_PORT=6380` (se 6379 estiver ocupada)

### Erro: "Authentication failed"
Verifique se:
1. O arquivo `.env` foi criado corretamente
2. Não há espaços antes/depois do `=` nas variáveis
3. As senhas não contêm caracteres especiais problemáticos

### Containers não inicializam
```bash
docker-compose logs [nome_do_serviço]
```

## Segurança

⚠️ **NUNCA** commite o arquivo `.env` com senhas reais!
✅ O `.env` está no `.gitignore` e não será enviado ao repositório
✅ Use `.env.example` como referência para outros desenvolvedores
