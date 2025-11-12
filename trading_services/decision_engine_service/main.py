"""
Decision Engine Service - Main
===============================

Motor de decisão determinístico.
NÃO contém LLM - usa árvore de decisão estática.
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
from dotenv import load_dotenv

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
)
log = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()


class DecisionEngine:
    """
    Motor de decisão para trading.
    Combina sinais técnicos e de sentimento para tomar decisões.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.pubsub = None
        self.symbols = os.getenv("TRADING_SYMBOLS", "EUR/USD,GBP/USD,USD/JPY").split(",")

        # Estado atual dos sinais para cada símbolo
        self.signal_state = defaultdict(lambda: {
            "technical": None,
            "sentiment": None,
            "last_decision": None,
            "position": None  # None, 'LONG', 'SHORT'
        })

        # Carregar regras de decisão
        self.decision_rules = self.load_decision_rules()

    def load_decision_rules(self) -> Dict[str, Any]:
        """Carrega regras de decisão do arquivo JSON"""
        rules_file = os.getenv("DECISION_RULES_FILE", "trading_services/decision_engine_service/decision_trees.json")

        if os.path.exists(rules_file):
            with open(rules_file, 'r') as f:
                rules = json.load(f)
                log.info(f"Regras de decisão carregadas de {rules_file}")
                return rules
        else:
            # Regras padrão (Nível 1 - conservador)
            log.warning("Arquivo de regras não encontrado, usando regras padrão")
            return {
                "EUR/USD": {
                    "BUY": {"rsi_min": 0, "rsi_max": 30, "sentiment_min": 0.3},
                    "SELL": {"rsi_min": 70, "rsi_max": 100, "sentiment_max": -0.3}
                },
                "GBP/USD": {
                    "BUY": {"rsi_min": 0, "rsi_max": 30, "sentiment_min": 0.3},
                    "SELL": {"rsi_min": 70, "rsi_max": 100, "sentiment_max": -0.3}
                },
                "USD/JPY": {
                    "BUY": {"rsi_min": 0, "rsi_max": 30, "sentiment_min": 0.3},
                    "SELL": {"rsi_min": 70, "rsi_max": 100, "sentiment_max": -0.3}
                }
            }

    async def connect_redis(self):
        """Conectar ao Redis"""
        self.redis_client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        log.info(f"Conectado ao Redis: {self.redis_url}")

    async def subscribe_to_signals(self):
        """Subscrever a todos os canais de sinais"""
        channels = []

        for symbol in self.symbols:
            symbol_clean = symbol.replace('/', '_')
            channels.append(f"signals:tech:{symbol_clean}")
            channels.append(f"signals:sentiment:{symbol_clean}")

        await self.pubsub.psubscribe("signals:*")
        log.info(f"Subscrito aos canais de sinais: {channels}")

    def evaluate_decision(self, symbol: str) -> Optional[str]:
        """
        Avalia se deve tomar uma decisão de trade.

        Args:
            symbol: Par de moedas

        Returns:
            'BUY', 'SELL' ou None
        """
        state = self.signal_state[symbol]

        # Precisa ter ambos os sinais
        if state["technical"] is None or state["sentiment"] is None:
            return None

        tech_indicators = state["technical"].get("indicators", {})
        rsi = tech_indicators.get("rsi")
        sentiment_score = state["sentiment"].get("sentiment_score")

        if rsi is None or sentiment_score is None:
            return None

        # Buscar regras para este símbolo
        rules = self.decision_rules.get(symbol)
        if not rules:
            log.warning(f"Nenhuma regra definida para {symbol}")
            return None

        # Avaliar regra de COMPRA
        buy_rule = rules.get("BUY", {})
        if (buy_rule.get("rsi_min", 0) <= rsi <= buy_rule.get("rsi_max", 30) and
            sentiment_score >= buy_rule.get("sentiment_min", 0.3)):

            # Só comprar se não estiver em posição LONG
            if state["position"] != "LONG":
                return "BUY"

        # Avaliar regra de VENDA
        sell_rule = rules.get("SELL", {})
        if (sell_rule.get("rsi_min", 70) <= rsi <= sell_rule.get("rsi_max", 100) and
            sentiment_score <= sell_rule.get("sentiment_max", -0.3)):

            # Só vender se não estiver em posição SHORT
            if state["position"] != "SHORT":
                return "SELL"

        return None

    async def publish_order(self, symbol: str, decision: str, price: float):
        """
        Publica ordem de execução no Redis.

        Args:
            symbol: Par de moedas
            decision: BUY ou SELL
            price: Preço atual
        """
        # Calcular tamanho da posição (simplificado - 1% do capital)
        position_size = 0.01  # 1% do capital

        order = {
            "symbol": symbol,
            "side": decision,
            "size": position_size,
            "price": price,
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": "RSI_SENTIMENT_V1"
        }

        channel = "orders:execute"
        message = json.dumps(order)

        await self.redis_client.publish(channel, message)

        log.info(f"🎯 ORDEM PUBLICADA: {decision} {symbol} @ {price} (size={position_size})")

        # Atualizar estado da posição
        self.signal_state[symbol]["position"] = "LONG" if decision == "BUY" else "SHORT"
        self.signal_state[symbol]["last_decision"] = decision

    async def process_signal(self, channel: str, signal_data: Dict[str, Any]):
        """
        Processa um sinal recebido.

        Args:
            channel: Canal Redis (signals:tech:EUR_USD ou signals:sentiment:EUR_USD)
            signal_data: Dados do sinal
        """
        symbol = signal_data.get("symbol")
        if not symbol:
            return

        # Atualizar estado
        if "tech" in channel:
            self.signal_state[symbol]["technical"] = signal_data
            log.debug(f"Sinal técnico atualizado para {symbol}: RSI={signal_data.get('indicators', {}).get('rsi')}")

        elif "sentiment" in channel:
            self.signal_state[symbol]["sentiment"] = signal_data
            log.debug(f"Sinal de sentimento atualizado para {symbol}: score={signal_data.get('sentiment_score')}")

        # Avaliar se deve tomar decisão
        decision = self.evaluate_decision(symbol)

        if decision:
            price = signal_data.get("price", 0.0)
            await self.publish_order(symbol, decision, price)

    async def start(self):
        """Inicia o motor de decisão"""
        await self.connect_redis()
        await self.subscribe_to_signals()

        log.info("Decision Engine Service iniciado")
        log.info(f"Símbolos monitorados: {self.symbols}")

        # Loop de processamento de mensagens
        async for message in self.pubsub.listen():
            if message["type"] == "pmessage":
                try:
                    signal_data = json.loads(message["data"])
                    await self.process_signal(message["channel"], signal_data)
                except Exception as e:
                    log.error(f"Erro ao processar sinal: {e}")

    async def shutdown(self):
        """Encerra conexões"""
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis_client:
            await self.redis_client.close()
        log.info("Decision Engine Service encerrado")


async def main():
    """Função principal"""
    engine = DecisionEngine()

    try:
        await engine.start()
    except KeyboardInterrupt:
        log.info("Recebido sinal de interrupção")
    finally:
        await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
