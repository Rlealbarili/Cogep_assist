"""
Decision Engine Service
=======================

Responsável por:
- Subscrever a TODOS os canais signals:* (tech + sentiment)
- Manter estado da estratégia
- Carregar regras de decisão (decision_trees.json)
- Tomar decisão de trade (BUY/SELL/HOLD)
- Publicar ordens no Redis (canal: orders:execute)
"""
