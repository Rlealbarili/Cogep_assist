"""
Market Data Service - Main
===========================

Serviço principal para ingestão de dados de mercado.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

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

class MarketDataService:
    """
    Serviço de ingestão de dados de mercado via WebSocket.
    Publica ticks no Redis Pub/Sub para consumo downstream.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.symbols = os.getenv("TRADING_SYMBOLS", "EUR/USD,GBP/USD,USD/JPY").split(",")
        self.exchange_type = os.getenv("EXCHANGE_TYPE", "alpaca")  # alpaca ou oanda

    async def connect_redis(self):
        """Conectar ao Redis para Pub/Sub"""
        self.redis_client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        log.info(f"Conectado ao Redis: {self.redis_url}")

    async def publish_tick(self, symbol: str, tick_data: Dict[str, Any]):
        """
        Publica tick no canal Redis.

        Args:
            symbol: Par de moedas (ex: EUR/USD)
            tick_data: Dados do tick (price, volume, timestamp)
        """
        channel = f"market:ticks:{symbol.replace('/', '_')}"
        message = json.dumps(tick_data)

        await self.redis_client.publish(channel, message)
        log.debug(f"Publicado em {channel}: {message}")

    async def start(self):
        """Inicia o serviço de ingestão de dados"""
        await self.connect_redis()

        log.info(f"Market Data Service iniciado para {self.exchange_type}")
        log.info(f"Símbolos monitorados: {self.symbols}")

        # TODO: Implementar conexão WebSocket específica da exchange
        # Por enquanto, modo simulação para teste
        await self._run_simulation_mode()

    async def _run_simulation_mode(self):
        """
        Modo de simulação para testes (gera dados sintéticos).
        Será substituído pela conexão WebSocket real.
        """
        log.warning("Rodando em MODO SIMULAÇÃO - dados sintéticos")

        import random
        base_prices = {
            "EUR/USD": 1.0850,
            "GBP/USD": 1.2650,
            "USD/JPY": 149.50
        }

        while True:
            for symbol in self.symbols:
                # Gerar tick sintético
                base_price = base_prices.get(symbol, 1.0)
                price = base_price + random.uniform(-0.0010, 0.0010)

                tick_data = {
                    "symbol": symbol,
                    "price": round(price, 5),
                    "bid": round(price - 0.0002, 5),
                    "ask": round(price + 0.0002, 5),
                    "volume": random.randint(100, 1000),
                    "timestamp": datetime.utcnow().isoformat()
                }

                await self.publish_tick(symbol, tick_data)

            await asyncio.sleep(1)  # 1 tick por segundo por símbolo

    async def shutdown(self):
        """Encerra conexões gracefully"""
        if self.redis_client:
            await self.redis_client.close()
        log.info("Market Data Service encerrado")


async def main():
    """Função principal"""
    service = MarketDataService()

    try:
        await service.start()
    except KeyboardInterrupt:
        log.info("Recebido sinal de interrupção")
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
