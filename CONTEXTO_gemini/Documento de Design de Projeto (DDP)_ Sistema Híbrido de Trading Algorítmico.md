# **Documento de Design de Projeto (DDP): Sistema Híbrido de Trading Algorítmico**

ID do Documento: DDP-TRD-BOT-V1  
Versão: 1.0  
Status: Aprovado para Iniciação  
Proprietário: Rafael H Leal  
OBS IMPORTANTE: PRIMEIRA COISA A FAZER É CLONAR O REPOSITORIO: [https://github.com/Rlealbarili/Cogep\_assist](https://github.com/Rlealbarili/Cogep_assist)  
PARA OUTRO REPOSITORIO OU CRIAR UMA BRANCH QUE NAO INTERAJA COM O REPOSITORIO PRINCIPAL PARA NÃO AFETAR OQUE FOI FEITO NO REPOSITORIO PRINCIPAL

## **1.0 Resumo Executivo**

Este documento detalha a arquitetura e o plano de implementação de um sistema de automação de trading para os mercados de Criptomoedas e Forex. O projeto é um *pivô* de uma arquitetura de RAG (Retrieval-Augmented Generation) reativa existente (Cogep\_assist) para um **sistema de microserviços proativo, de baixa latência e orientado a eventos**.

O erro fundamental corrigido por este plano foi a tentativa de usar um LLM (Qwen) como tomador de decisão síncrono. Na arquitetura aprovada, o LLM e a infraestrutura RAG existentes serão reaproveitados como um **microserviço de análise de sentimento**, fornecendo um *único sinal qualitativo* (lento) que é fundido com sinais quantitativos (rápidos) por um motor de decisão determinístico.

A arquitetura central será baseada no **padrão Publish/Subscribe (Pub/Sub) via Redis**, o que garante desacoplamento, escalabilidade e performance de baixa latência, em oposição direta à arquitetura anterior baseada em *webhook* HTTP síncrono.

## **2.0 Arquitetura Central: O Barramento de Eventos (Pub/Sub)**

A espinha dorsal do sistema é o **Redis**, que já faz parte da stack (docker-compose.yml). Ele não será usado apenas como *broker* Celery, mas como o barramento de eventos principal que conecta os microserviços.

O fluxo de dados será o seguinte:

\[Exchange WS\] \-\> 1\. market\_data\_service  \-\> (PUBLISH ticks) \-\> \[Redis Pub/Sub\]  
                                                                     |  
                                                                     v  
\[Redis Pub/Sub\] \-\> 2\. technical\_signal\_service \-\> (PUBLISH signals:tech) \-\> \[Redis Pub/Sub\]  
                                                                     |  
\[News APIs\]     \-\> 3\. sentiment\_analysis\_service \-\> (PUBLISH signals:sentiment) \-\> \[Redis Pub/Sub\]  
                                                                     |  
                                                                     v  
\[Redis Pub/Sub\] \-\> 4\. decision\_engine\_service \-\> (PUBLISH orders:execute) \-\> \[Redis Pub/Sub\]  
                                                                     |  
                                                                     v  
\[Redis Pub/Sub\] \-\> 5\. order\_execution\_service \-\> \[Exchange API\]

## **3.0 Detalhamento dos Microserviços**

O sistema será composto por 5 (cinco) microserviços independentes.

### **3.1. market\_data\_service (O Ouvido)**

* **Propósito:** Ingerir dados de mercado com a menor latência possível.  
* **Stack:** Python, websockets-client, ccxt.  
* **Lógica:** Conecta-se aos *streams* WebSocket da exchange (ex: Binance). A cada *tick* (trade) recebido, publica-o imediatamente no canal Redis market:ticks:\<PAR\>. Não realiza cálculos.

### **3.2. technical\_signal\_service (O Cérebro Quant)**

* **Propósito:** Calcular indicadores técnicos.  
* **Stack:** Python, pandas, numpy, TA-Lib.  
* **Lógica:** Assina o canal market:ticks:\<PAR\>. Agrega ticks em velas (ex: 1 minuto) em memória. A cada fechamento de vela, calcula indicadores (RSI, MACD, etc.) e publica um JSON de sinal no canal signals:tech:\<PAR\>.

### **3.3. sentiment\_analysis\_service (O Cérebro RAG)**

* **Propósito:** Analisar dados não estruturados (notícias) e gerar um score de sentimento.  
* **Status:** **Refatoração do Cogep\_assist**.  
* **Lógica:**  
  1. **Exclusão:** Os modelos Clients, Consents, e Tickets do core/models.py serão removidos. A lógica de CRM e LGPD é irrelevante para este projeto.  
  2. **Manutenção:** A pipeline de ingestão (worker\_service/tasks.py) será mantida para processar *links* de APIs de notícias.  
  3. **Refatoração:** O orchestrator.py será substituído por um endpoint de API interna (POST /api/v1/get\_sentiment).  
  4. **Integração:** Um *scheduler* (Celery Beat) chamará este endpoint periodicamente. O serviço usará o Qwen 14B (local) para analisar os documentos RAG (do RagDocuments1536) e publicará um score no canal signals:sentiment:\<ATIVO\>.

### **3.4. decision\_engine\_service (O Juiz)**

* **Propósito:** Tomar a decisão final de trade. **Este serviço não contém um LLM.**  
* **Stack:** Python, redis-py.  
* **Lógica:** Assina *todos* os canais de signals:\*. Mantém o estado atual da estratégia. A cada novo sinal, ele carrega a lógica de decisão (Nível 1\) de um arquivo decision\_trees.json e o compara com o estado atual. Se as regras forem atendidas, calcula o tamanho da posição e publica uma ordem final no canal orders:execute.

### **3.5. order\_execution\_service (As Mãos)**

* **Propósito:** Enviar ordens à exchange. O único componente com chaves de API *write*.  
* **Stack:** Python, ccxt, tenacity (para retries).  
* **Lógica:** Assina o canal orders:execute. Recebe a ordem formatada, executa-a via ccxt.create\_order() e loga o resultado (sucesso ou falha) no banco de dados persistente.

## **4.0 Hierarquia de Lógica de Decisão e Métricas**

A "inteligência" do bot evoluirá em três níveis de complexidade:

* **Nível 1: Árvore de Decisão Estática:** Implementação inicial no decision\_engine\_service. Usará um decision\_trees.json com regras rígidas (ex: "SE RSI \< 30 E Sentimento \> 0.5 ENTRAR").  
* **Nível 2: Otimização de Parâmetros (Backtesting):** Usando ferramentas *offline* (ex: VectorBT, Backtrader), executaremos *grid searches* em dados históricos para encontrar os parâmetros ótimos (ex: "RSI \< 28", "Sentimento \> 0.65") e atualizar o Nível 1\.  
* **Nível 3: Modelo Adaptativo (Reinforcement Learning):** Uma fase futura usará **FinRL** para treinar um agente que substitua a árvore de decisão estática, permitindo que o bot se adapte a novos regimes de mercado.

### **4.1. Métricas de Sucesso**

O sucesso não será medido por "Win Rate", mas por performance ajustada ao risco e eficiência.

1. **Métricas de Estratégia:**  
   * **Sharpe Ratio (Índice de Sharpe):** Métrica primária. (Retorno / Risco).  
   * **Max Drawdown (Rebaixamento Máximo):** Métrica secundária. Mede a "dor" máxima.  
   * **Profit Factor (Fator de Lucro):** (Ganhos Totais / Perdas Totais).  
2. **Métricas Operacionais:**  
   * **Latência de Sinal-para-Ordem (ms):** Tempo entre o market\_data\_service ver um tick e o order\_execution\_service enviar a ordem.  
   * **Slippage (Derrapagem):** Diferença de preço entre a decisão e a execução.

## **5.0 Stack de Tecnologia Consolidada**

* **Infraestrutura:** Docker, VPS (ex: DigitalOcean/Vultr).  
* **Barramento de Eventos e Cache:** Redis.  
* **Banco de Dados (RAG):** PostgreSQL \+ PGVector.  
* **Banco de Dados (Séries Temporais):** InfluxDB ou TimescaleDB (Novo requisito).  
* **Serviços / Workers:** Python, FastAPI, Celery.  
* **Bibliotecas de Trading:** CCXT, TA-Lib, VectorBT, FinRL.  
* **Modelo de IA (Local):** Qwen 14B Coder (para o sentiment\_analysis\_service).

## **6.0 Fases do Projeto (Plano de Ação)**

1. **Fase 1: Refatoração e Coleta de Dados.**  
   * \[ \] Remover lógica de CRM/LGPD do Cogep\_assist.  
   * \[ \] Configurar banco de dados de séries temporais (InfluxDB).  
   * \[ \] Implementar market\_data\_service e technical\_signal\_service (publicando no Redis).  
   * \[ \] Iniciar coleta de dados OHLCV.  
2. **Fase 2: Implementação (Nível 1\) e Paper Trading.**  
   * \[ \] Implementar decision\_engine\_service (lendo decision\_trees.json).  
   * \[ \] Implementar order\_execution\_service.  
   * \[ \] Conectar à conta de *Paper Trading* da Alpaca e iniciar testes.  
3. **Fase 3: Otimização (Nível 2\) e RAG.**  
   * \[ \] Iniciar *backtesting* (Nível 2\) para otimizar os parâmetros do Nível 1\.  
   * \[ \] Implementar o sentiment\_analysis\_service (Fase 4 do plano original).  
   * \[ \] Atualizar o decision\_engine\_service para assinar os sinais de sentimento.  
4. **Fase 4: Produção (Capital Mínimo).**  
   * \[ \] Deploy em VPS.  
   * \[ \] Iniciar trading *live* com capital de risco mínimo (ex: $100).  
   * \[ \] Configurar monitoramento (Grafana) para Métricas Operacionais (Latência, Slippage).  
5. **Fase 5: Adaptação (Nível 3).**  
   * \[ \] Iniciar P\&D do modelo de Reinforcement Learning (FinRL).

---

