# 🤖 Sistema Híbrido de Trading Algorítmico - Guia de Setup

**Versão:** 0.1.0 (Fase 0 - Preparação do Ambiente)
**Data:** 2025-01-12
**Status:** Em Desenvolvimento

---

## 📋 Resumo do Projeto

Este é um **sistema de trading algorítmico** para Forex que combina:
- ✅ **Sinais Técnicos** (RSI, MACD) - Rápidos e determinísticos
- ✅ **Análise de Sentimento** (RAG + Qwen 14B) - Contexto qualitativo
- ✅ **Arquitetura Pub/Sub** (Redis) - Baixa latência e desacoplamento
- ✅ **5 Microserviços** independentes e escaláveis

**Refatorado de:** Cogep_assist (RAG reativo para WhatsApp)
**Nova arquitetura:** Sistema proativo orientado a eventos

---

## 🏗️ Arquitetura dos Microserviços

```
┌─────────────────────┐
│  Forex Exchange WS  │ (Alpaca/OANDA)
└──────────┬──────────┘
           │ WebSocket
           ▼
┌───────────────────────────┐
│ 1. market_data_service    │ ─────► Redis Pub/Sub: market:ticks:*
└───────────────────────────┘
           │
           ├────► Redis ────────────────────┐
           │                                 │
           ▼                                 ▼
┌───────────────────────────┐    ┌──────────────────────────┐
│ 2. technical_signal       │    │ 3. sentiment_analysis    │
│    _service               │    │    _service              │
│    (RSI, MACD)            │    │    (RAG + Qwen 14B)      │
└───────────┬───────────────┘    └────────┬─────────────────┘
            │                              │
            │ signals:tech:*               │ signals:sentiment:*
            │                              │
            └──────────┬───────────────────┘
                       │
                       ▼ Redis Pub/Sub
            ┌──────────────────────┐
            │ 4. decision_engine   │
            │    _service          │
            │    (decision_trees)  │
            └──────────┬───────────┘
                       │ orders:execute
                       ▼
            ┌──────────────────────┐
            │ 5. order_execution   │
            │    _service          │
            └──────────┬───────────┘
                       │
                       ▼
              ┌────────────────┐
              │ Forex Exchange │ (API REST)
              └────────────────┘
```

---

## 🚀 Setup Inicial (FAÇA ISSO PRIMEIRO!)

### 1. Configurar Ambiente

```bash
# Clonar o repositório (se ainda não fez)
cd ~/Cogep_assist
git checkout claude/read-trading-system-ddp-011CV4NSnQZnXZbKuVYVK6iL
git pull origin claude/read-trading-system-ddp-011CV4NSnQZnXZbKuVYVK6iL

# Copiar .env.example e configurar
cp .env.example .env
nano .env  # Editar com suas configurações
```

### 2. Instalar Dependências Python

```bash
# Criar ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

**⚠️ IMPORTANTE - TA-Lib:**
O `ta-lib` requer a biblioteca C nativa. Instalação:

```bash
# Ubuntu/Debian
sudo apt-get install ta-lib

# macOS
brew install ta-lib

# Windows
# Baixe o wheel de: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib‑0.4.XX‑cpXX‑cpXX‑win_amd64.whl
```

Se tiver problemas com TA-Lib, **pode comentar** no requirements.txt por enquanto (modo simulação não usa).

### 3. Subir Infraestrutura Docker

```bash
# Subir PostgreSQL, Redis e TimescaleDB
docker-compose up -d

# Verificar se os containers estão rodando
docker ps

# Deve mostrar:
# - cogep_assist_postgres (PostgreSQL + PGVector)
# - cogep_assist_redis (Redis)
# - trading_bot_timescaledb (TimescaleDB)
```

### 4. Executar Migrations do Banco de Dados

```bash
# Criar schema trading e tabelas
alembic upgrade head

# Verificar que o schema foi criado
docker exec -it cogep_assist_postgres psql -U cogep_user -d cogep_assist_db -c "\dn"
# Deve mostrar: ai, trading
```

### 5. Configurar Variáveis de Ambiente

Edite o arquivo `.env` com suas configurações:

```bash
# CRÍTICO: Configure o Qwen 14B
OLLAMA_API_BASE_URL=http://seu-servidor-local:11434/v1
OLLAMA_CHAT_MODEL_NAME=qwen2.5-coder:14b-instruct-q4_K_M

# CRÍTICO: Configure OpenAI (para embeddings)
OPENAI_API_KEY=sk-your-key-here

# OPCIONAL: Por enquanto deixe vazio (rodará em modo SIMULAÇÃO)
EXCHANGE_API_KEY=
EXCHANGE_API_SECRET=
```

---

## 🧪 Testar a Infraestrutura (Modo Simulação)

### 1. Testar Market Data Service

```bash
cd ~/Cogep_assist
python -m trading_services.market_data_service.main
```

**Saída esperada:**
```
[2025-01-12 12:00:00] INFO Conectado ao Redis: redis://localhost:6379
[2025-01-12 12:00:00] INFO Market Data Service iniciado para alpaca
[2025-01-12 12:00:00] WARNING Rodando em MODO SIMULAÇÃO - dados sintéticos
[2025-01-12 12:00:01] DEBUG Publicado em market:ticks:EUR_USD: {"symbol": "EUR/USD", "price": 1.0851, ...}
```

**Deixe rodando** e abra outro terminal.

### 2. Testar Technical Signal Service

```bash
# Em outro terminal
python -m trading_services.technical_signal_service.main
```

**Saída esperada:**
```
[2025-01-12 12:01:00] INFO Conectado ao Redis: redis://localhost:6379
[2025-01-12 12:01:00] INFO Subscrito aos canais: ['market:ticks:EUR_USD', ...]
[2025-01-12 12:01:15] INFO Sinal publicado em signals:tech:EUR_USD: RSI=52.34
```

### 3. Testar Decision Engine

```bash
# Em outro terminal
python -m trading_services.decision_engine_service.main
```

**Saída esperada:**
```
[2025-01-12 12:02:00] INFO Regras de decisão carregadas
[2025-01-12 12:02:00] INFO Subscrito aos canais de sinais
[2025-01-12 12:02:30] INFO 🎯 ORDEM PUBLICADA: BUY EUR/USD @ 1.0845 (size=0.01)
```

### 4. Testar Order Execution Service

```bash
# Em outro terminal
python -m trading_services.order_execution_service.main
```

**Saída esperada:**
```
[2025-01-12 12:03:00] WARNING ⚠️  CREDENCIAIS DA EXCHANGE NÃO CONFIGURADAS - Rodando em modo SIMULAÇÃO
[2025-01-12 12:03:00] INFO Order Execution Service iniciado - Modo: SIMULAÇÃO
[2025-01-12 12:03:45] INFO 🎮 MODO SIMULAÇÃO - Ordem NÃO será enviada à exchange real
[2025-01-12 12:03:45] INFO ✅ Ordem executada com sucesso: sim_1705068225.123
```

---

## 📊 Próximos Passos

### ✅ **FASE 0: PREPARAÇÃO** (CONCLUÍDA!)

- [x] Docker Compose com TimescaleDB
- [x] Refatoração de `core/models.py` (removido CRM/LGPD)
- [x] Criação dos 5 microserviços (esqueleto)
- [x] Migration Alembic para schema `trading`
- [x] `.env.example` configurado
- [x] `requirements.txt` atualizado

### 🔨 **FASE 1: REFATORAÇÃO E COLETA DE DADOS** (PRÓXIMA!)

#### **1.1. Conectar ao Alpaca Paper Trading**

1. **Criar conta gratuita:** https://app.alpaca.markets/signup
2. **Ativar Paper Trading:** Dashboard → Paper Trading → Enable
3. **Copiar API Keys:**
   - `EXCHANGE_API_KEY=PKXXXXXXXX`
   - `EXCHANGE_API_SECRET=XXXXXXXX`
4. **Atualizar `.env`:**
   ```bash
   EXCHANGE_TYPE=alpaca
   PAPER_TRADING=true
   EXCHANGE_API_KEY=sua-chave-paper-aqui
   EXCHANGE_API_SECRET=seu-secret-paper-aqui
   ```

#### **1.2. Implementar WebSocket Real**

**Arquivo:** `trading_services/market_data_service/main.py`

Substituir `_run_simulation_mode()` por conexão WebSocket Alpaca:

```python
# TODO: Implementar em market_data_service/main.py
import ccxt.pro as ccxtpro

async def connect_exchange_websocket(self):
    exchange = ccxtpro.alpaca({
        'apiKey': os.getenv('EXCHANGE_API_KEY'),
        'secret': os.getenv('EXCHANGE_API_SECRET'),
        'urls': {'api': os.getenv('ALPACA_BASE_URL')}
    })

    while True:
        for symbol in self.symbols:
            trades = await exchange.watch_trades(symbol)
            for trade in trades:
                await self.publish_tick(symbol, trade)
```

#### **1.3. Salvar OHLCV no TimescaleDB**

**Criar tabela hypertable no TimescaleDB:**

```bash
docker exec -it trading_bot_timescaledb psql -U trading_user -d trading_data
```

```sql
CREATE TABLE ohlcv (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open NUMERIC(12,5),
    high NUMERIC(12,5),
    low NUMERIC(12,5),
    close NUMERIC(12,5),
    volume NUMERIC(18,8)
);

SELECT create_hypertable('ohlcv', 'time');
CREATE INDEX ON ohlcv (symbol, time DESC);
```

**Implementar ingestão:** Adicionar ao `market_data_service` código para agregar ticks em velas de 1 minuto e salvar no TimescaleDB.

---

### 🎯 **FASE 2: MOTOR DE DECISÃO + PAPER TRADING** (Semana 3-4)

1. Refatorar `sentiment_analysis_service` (remover lógica WhatsApp)
2. Integrar feeds RSS de Forex (ForexFactory, DailyFX)
3. Testar estratégia completa em Paper Trading

---

### 🔬 **FASE 3: OTIMIZAÇÃO** (Semana 5-6)

1. Backtesting com VectorBT
2. Grid search de parâmetros ótimos
3. Atualizar `decision_trees.json`

---

### 🚀 **FASE 4: PRODUÇÃO** (Semana 7-8)

1. Deploy em VPS
2. Grafana + Prometheus
3. Live trading com $100

---

### 🧠 **FASE 5: REINFORCEMENT LEARNING** (Semana 9+)

1. Implementar FinRL (PPO agent)
2. A/B testing Nível 1 vs Nível 3

---

## 🛟 Troubleshooting

### Problema: "docker: command not found"

**Solução:** Instale o Docker:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Problema: "ModuleNotFoundError: No module named 'talib'"

**Solução:** Instale a biblioteca C do TA-Lib primeiro (veja seção 2 acima), ou comente `ta-lib` no `requirements.txt` para testes iniciais.

### Problema: "Connection refused to Redis"

**Solução:** Verifique se o Redis está rodando:
```bash
docker ps | grep redis
docker-compose restart redis
```

### Problema: "Failed to connect to Ollama"

**Solução:** Verifique se o Qwen 14B está rodando no seu servidor:
```bash
curl http://seu-servidor:11434/api/tags
```

---

## 📚 Documentação de Referência

- **DDP Original:** `CONTEXTO_gemini/Documento de Design de Projeto (DDP)_ Sistema Híbrido de Trading Algorítmico.md`
- **Alpaca Docs:** https://alpaca.markets/docs/
- **CCXT Pro:** https://docs.ccxt.com/en/latest/ccxt.pro.manual.html
- **Redis Pub/Sub:** https://redis.io/docs/manual/pubsub/
- **TimescaleDB:** https://docs.timescale.com/

---

## 🤝 Próximos Comandos para Você

**Depois de fazer pull desta branch:**

```bash
# 1. Configurar .env
cp .env.example .env
nano .env  # Configure suas chaves

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Subir Docker
docker-compose up -d

# 4. Executar migrations
alembic upgrade head

# 5. Testar modo simulação
python -m trading_services.market_data_service.main
```

**Reporte os resultados!** Se houver erros, me envie os logs completos.

---

**Status:** ✅ Fase 0 Completa - Pronto para Fase 1!
