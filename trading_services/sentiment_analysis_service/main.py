"""
Sentiment Analysis Service - Main
==================================

Análise de sentimento usando RAG + Qwen 14B.
Refatorado do orchestrator.py original.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

import redis.asyncio as aioredis
from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from core.database import get_db
from core.models import RagDocuments1536
from agent_service.llm_client import get_resilient_chat_completion
import openai

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
)
log = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# FastAPI app
app = FastAPI(
    title="Sentiment Analysis Service",
    description="Análise de sentimento para Trading Bot usando RAG + LLM",
    version="0.1.0"
)


class SentimentAnalyzer:
    """Classe para análise de sentimento usando RAG"""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None

    async def connect_redis(self):
        """Conectar ao Redis"""
        if not self.redis_client:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            log.info(f"Conectado ao Redis: {self.redis_url}")

    async def get_query_embedding(self, text: str) -> List[float]:
        """Gera embedding para a query usando OpenAI"""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise Exception("OPENAI_API_KEY não encontrada")

        client = openai.AsyncOpenAI(api_key=openai_api_key)

        response = await client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )

        return response.data[0].embedding

    async def get_relevant_news(self, symbol: str, session: AsyncSession) -> List[str]:
        """
        Busca notícias relevantes do RAG para o símbolo.

        Args:
            symbol: Par de moedas (EUR/USD)
            session: Sessão do banco de dados

        Returns:
            Lista de chunks de texto relevantes
        """
        # Criar query contextualizada
        query_text = f"News and analysis about {symbol} forex pair trading sentiment market outlook"

        # Gerar embedding da query
        query_vector = await self.get_query_embedding(query_text)

        # Buscar documentos similares no RAG
        stmt = select(
            RagDocuments1536.content
        ).filter(
            RagDocuments1536.namespace == 'forex_news',  # Namespace específico para Forex
            RagDocuments1536.embedding.cosine_distance(query_vector) < 0.7
        ).order_by(
            RagDocuments1536.embedding.cosine_distance(query_vector)
        ).limit(5)

        result = await session.execute(stmt)
        context_chunks = result.scalars().all()

        return list(context_chunks)

    async def analyze_sentiment(self, symbol: str, news_chunks: List[str]) -> float:
        """
        Analisa o sentimento das notícias usando o LLM.

        Args:
            symbol: Par de moedas
            news_chunks: Lista de chunks de notícias

        Returns:
            Score de sentimento de -1.0 (muito negativo) a +1.0 (muito positivo)
        """
        if not news_chunks:
            log.warning(f"Nenhuma notícia encontrada para {symbol}, retornando sentimento neutro")
            return 0.0

        context = "\n\n---\n\n".join(news_chunks)

        system_prompt = """Você é um analista de sentimento de mercado Forex.
Analise as notícias fornecidas e retorne APENAS um número de -1.0 a +1.0:
- -1.0: Muito negativo (forte sinal de VENDA)
- -0.5: Negativo
- 0.0: Neutro
- +0.5: Positivo
- +1.0: Muito positivo (forte sinal de COMPRA)

Responda APENAS com o número, sem explicações."""

        user_prompt = f"""Notícias sobre {symbol}:

{context}

Score de sentimento (-1.0 a +1.0):"""

        try:
            llm_response = await get_resilient_chat_completion(system_prompt, user_prompt)

            # Extrair o número da resposta
            sentiment_score = float(llm_response.strip())

            # Garantir que está no intervalo [-1.0, +1.0]
            sentiment_score = max(-1.0, min(1.0, sentiment_score))

            return round(sentiment_score, 2)

        except ValueError:
            log.error(f"Falha ao parsear resposta do LLM: {llm_response}")
            return 0.0

    async def publish_sentiment_signal(self, symbol: str, sentiment_score: float):
        """Publica sinal de sentimento no Redis"""
        await self.connect_redis()

        channel = f"signals:sentiment:{symbol.replace('/', '_')}"

        signal = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "sentiment_score": sentiment_score,
            "signal_type": "SENTIMENT"
        }

        message = json.dumps(signal)
        await self.redis_client.publish(channel, message)

        log.info(f"Sinal de sentimento publicado em {channel}: score={sentiment_score}")


# Instância global
analyzer = SentimentAnalyzer()


@app.post("/api/v1/sentiment/{symbol}")
async def get_sentiment(symbol: str, session: AsyncSession = Depends(get_db)):
    """
    Endpoint para obter sentimento de um símbolo.

    Args:
        symbol: Par de moedas (ex: EUR/USD, GBP/USD)

    Returns:
        Score de sentimento + publicação no Redis
    """
    log.info(f"Requisição de sentimento para {symbol}")

    # Buscar notícias relevantes
    news_chunks = await analyzer.get_relevant_news(symbol, session)

    # Analisar sentimento
    sentiment_score = await analyzer.analyze_sentiment(symbol, news_chunks)

    # Publicar no Redis
    await analyzer.publish_sentiment_signal(symbol, sentiment_score)

    return {
        "symbol": symbol,
        "sentiment_score": sentiment_score,
        "news_count": len(news_chunks),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "sentiment_analysis"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
