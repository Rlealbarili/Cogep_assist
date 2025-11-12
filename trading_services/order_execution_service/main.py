"""
Order Execution Service - Main
===============================

Execução de ordens na exchange.
Único serviço com permissões de escrita (API keys).
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


class OrderExecutionService:
    """
    Serviço de execução de ordens.
    Consome ordens do Redis e executa na exchange.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.pubsub = None

        # Configurações da exchange
        self.exchange_type = os.getenv("EXCHANGE_TYPE", "alpaca")  # alpaca ou oanda
        self.api_key = os.getenv("EXCHANGE_API_KEY", "")
        self.api_secret = os.getenv("EXCHANGE_API_SECRET", "")
        self.paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"

        # Validar credenciais
        if not self.api_key or not self.api_secret:
            log.warning("⚠️  CREDENCIAIS DA EXCHANGE NÃO CONFIGURADAS - Rodando em modo SIMULAÇÃO")
            self.simulation_mode = True
        else:
            self.simulation_mode = False

    async def connect_redis(self):
        """Conectar ao Redis"""
        self.redis_client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.pubsub = self.redis_client.pubsub()
        log.info(f"Conectado ao Redis: {self.redis_url}")

    async def subscribe_to_orders(self):
        """Subscrever ao canal de ordens"""
        await self.pubsub.subscribe("orders:execute")
        log.info("Subscrito ao canal: orders:execute")

    async def execute_order_alpaca(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa ordem via Alpaca API.

        Args:
            order: Dados da ordem

        Returns:
            Resultado da execução
        """
        # TODO: Implementar integração real com Alpaca API
        # Por enquanto, simulação

        symbol = order["symbol"].replace("/", "")  # EUR/USD -> EURUSD
        side = order["side"].lower()  # BUY -> buy
        size = order["size"]

        log.info(f"📋 [ALPACA] Executando ordem: {side.upper()} {symbol} size={size}")

        # Simular latência da API
        await asyncio.sleep(0.1)

        # Simulação de resposta
        result = {
            "success": True,
            "order_id": f"alp_{datetime.utcnow().timestamp()}",
            "symbol": order["symbol"],
            "side": order["side"],
            "size": size,
            "filled_price": order["price"],
            "timestamp": datetime.utcnow().isoformat(),
            "exchange": "alpaca",
            "paper_trading": self.paper_trading
        }

        return result

    async def execute_order_oanda(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa ordem via OANDA API.

        Args:
            order: Dados da ordem

        Returns:
            Resultado da execução
        """
        # TODO: Implementar integração real com OANDA API
        # Por enquanto, simulação

        symbol = order["symbol"].replace("/", "_")  # EUR/USD -> EUR_USD
        side = order["side"]
        units = order["size"] * 10000  # Converter para units (1 lot = 10k units)

        if side == "SELL":
            units = -units  # OANDA usa units negativas para sell

        log.info(f"📋 [OANDA] Executando ordem: {side} {symbol} units={units}")

        # Simular latência da API
        await asyncio.sleep(0.1)

        # Simulação de resposta
        result = {
            "success": True,
            "order_id": f"oan_{datetime.utcnow().timestamp()}",
            "symbol": order["symbol"],
            "side": side,
            "units": units,
            "filled_price": order["price"],
            "timestamp": datetime.utcnow().isoformat(),
            "exchange": "oanda",
            "paper_trading": self.paper_trading
        }

        return result

    async def execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa ordem na exchange configurada.

        Args:
            order: Dados da ordem

        Returns:
            Resultado da execução
        """
        if self.simulation_mode:
            log.warning("🎮 MODO SIMULAÇÃO - Ordem NÃO será enviada à exchange real")

            return {
                "success": True,
                "order_id": f"sim_{datetime.utcnow().timestamp()}",
                "symbol": order["symbol"],
                "side": order["side"],
                "size": order["size"],
                "filled_price": order["price"],
                "timestamp": datetime.utcnow().isoformat(),
                "exchange": "simulation",
                "paper_trading": True,
                "note": "Simulação - sem execução real"
            }

        try:
            if self.exchange_type == "alpaca":
                result = await self.execute_order_alpaca(order)
            elif self.exchange_type == "oanda":
                result = await self.execute_order_oanda(order)
            else:
                raise ValueError(f"Exchange não suportada: {self.exchange_type}")

            log.info(f"✅ Ordem executada com sucesso: {result['order_id']}")
            return result

        except Exception as e:
            log.error(f"❌ Erro ao executar ordem: {e}")
            return {
                "success": False,
                "error": str(e),
                "order": order,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def log_execution_result(self, result: Dict[str, Any]):
        """
        Loga resultado da execução no PostgreSQL.

        Args:
            result: Resultado da execução

        TODO: Implementar persistência no banco de dados
        """
        # Por enquanto, apenas log
        log.info(f"💾 Resultado da execução: {json.dumps(result, indent=2)}")

    async def process_order(self, order_data: Dict[str, Any]):
        """
        Processa uma ordem recebida.

        Args:
            order_data: Dados da ordem
        """
        log.info(f"🎯 Nova ordem recebida: {order_data['side']} {order_data['symbol']}")

        # Executar ordem
        result = await self.execute_order(order_data)

        # Logar resultado
        await self.log_execution_result(result)

    async def start(self):
        """Inicia o serviço"""
        await self.connect_redis()
        await self.subscribe_to_orders()

        mode = "SIMULAÇÃO" if self.simulation_mode else ("PAPER TRADING" if self.paper_trading else "LIVE")
        log.info(f"Order Execution Service iniciado - Modo: {mode}")
        log.info(f"Exchange: {self.exchange_type}")

        # Loop de processamento de mensagens
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    order_data = json.loads(message["data"])
                    await self.process_order(order_data)
                except Exception as e:
                    log.error(f"Erro ao processar ordem: {e}")

    async def shutdown(self):
        """Encerra conexões"""
        if self.pubsub:
            await self.pubsub.unsubscribe()
        if self.redis_client:
            await self.redis_client.close()
        log.info("Order Execution Service encerrado")


async def main():
    """Função principal"""
    service = OrderExecutionService()

    try:
        await service.start()
    except KeyboardInterrupt:
        log.info("Recebido sinal de interrupção")
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
