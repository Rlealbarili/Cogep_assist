"""
Sentiment Analysis Service
===========================

Responsável por:
- Reaproveitar a infraestrutura RAG do Cogep_assist
- Processar notícias de Forex (ForexFactory, DailyFX, Bloomberg)
- Usar Qwen 14B (local) para análise de sentimento
- Publicar score de sentimento no Redis (canal: signals:sentiment:<SYMBOL>)
"""
