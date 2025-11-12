"""
Technical Signal Service - Main
================================

Calcula indicadores técnicos e publica sinais.
"""

import asyncio
import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any

import redis.asyncio as aioredis
import numpy as np
from dotenv import load_dotenv

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
)
log = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()


class TechnicalSignalService:
    """
    Serviço de cálculo de indicadores técnicos.
    Consome ticks do Redis, calcula indicadores e publica sinais.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.pubsub = None
        self.symbols = os.getenv("TRADING_SYMBOLS", "EUR/USD,GBP/USD,USD/JPY").split(",")

        # Buffer de ticks para agregação em velas
        self.tick_buffers = defaultdict(lambda: deque(maxlen=1000))

        # Configurações de indicadores
        self.rsi_period = int(os.getenv("RSI_PERIOD", "14"))
        self.macd_fast = int(os.getenv("MACD_FAST", "12"))
        self.macd_slow = int(os.getenv("MACD_SLOW", "26"))
        self.macd_signal = int(os.getenv("MACD_SIGNAL", "9"))

    async def connect_redis(self):
        """Conectar ao Redis"""
        self.redis_client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        log.info(f"Conectado ao Redis: {self.redis_url}")

    async def subscribe_to_market_data(self):
        """Subscrever aos canais de ticks de mercado"""
        channels = [f"market:ticks:{symbol.replace('/', '_')}" for symbol in self.symbols]

        await self.pubsub.subscribe(*channels)
        log.info(f"Subscrito aos canais: {channels}")

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Calcula o RSI (Relative Strength Index).

        Args:
            prices: Lista de preços de fechamento
            period: Período do RSI

        Returns:
            Valor do RSI (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Valor neutro se não houver dados suficientes

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi, 2)

    def calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """
        Calcula o MACD (Moving Average Convergence Divergence).

        Args:
            prices: Lista de preços de fechamento

        Returns:
            Dict com macd, signal, histogram
        """
        if len(prices) < self.macd_slow:
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}

        prices_array = np.array(prices)

        # EMA rápida e lenta
        ema_fast = self._calculate_ema(prices_array, self.macd_fast)
        ema_slow = self._calculate_ema(prices_array, self.macd_slow)

        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(np.array([macd_line]), self.macd_signal)
        histogram = macd_line - signal_line

        return {
            "macd": round(macd_line, 5),
            "signal": round(signal_line, 5),
            "histogram": round(histogram, 5)
        }

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA (Exponential Moving Average)"""
        if len(prices) == 0:
            return 0.0

        multiplier = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema

        return ema

    async def process_tick(self, channel: str, tick_data: Dict[str, Any]):
        """
        Processa um tick recebido e calcula indicadores.

        Args:
            channel: Canal Redis (market:ticks:EUR_USD)
            tick_data: Dados do tick
        """
        symbol = tick_data.get("symbol")
        price = tick_data.get("price")

        if not symbol or not price:
            return

        # Adicionar ao buffer
        self.tick_buffers[symbol].append(price)

        # Se houver dados suficientes, calcular indicadores
        if len(self.tick_buffers[symbol]) >= self.rsi_period + 1:
            prices = list(self.tick_buffers[symbol])

            rsi = self.calculate_rsi(prices, self.rsi_period)
            macd = self.calculate_macd(prices)

            # Criar sinal técnico
            signal = {
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "price": price,
                "indicators": {
                    "rsi": rsi,
                    "macd": macd
                }
            }

            # Publicar sinal
            await self.publish_signal(symbol, signal)

    async def publish_signal(self, symbol: str, signal: Dict[str, Any]):
        """Publica sinal técnico no Redis"""
        channel = f"signals:tech:{symbol.replace('/', '_')}"
        message = json.dumps(signal)

        await self.redis_client.publish(channel, message)
        log.info(f"Sinal publicado em {channel}: RSI={signal['indicators']['rsi']:.2f}")

    async def start(self):
        """Inicia o serviço"""
        await self.connect_redis()
        await self.subscribe_to_market_data()

        log.info("Technical Signal Service iniciado")
        log.info(f"Configuração: RSI={self.rsi_period}, MACD={self.macd_fast}/{self.macd_slow}/{self.macd_signal}")

        # Loop de processamento de mensagens
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    tick_data = json.loads(message["data"])
                    await self.process_tick(message["channel"], tick_data)
                except Exception as e:
                    log.error(f"Erro ao processar tick: {e}")

    async def shutdown(self):
        """Encerra conexões"""
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis_client:
            await self.redis_client.close()
        log.info("Technical Signal Service encerrado")


async def main():
    """Função principal"""
    service = TechnicalSignalService()

    try:
        await service.start()
    except KeyboardInterrupt:
        log.info("Recebido sinal de interrupção")
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
