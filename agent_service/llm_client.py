import asyncio
import logging
from openai import AsyncOpenAI
import httpx
import os
import json

# Configuração do logger
log = logging.getLogger(__name__)

# Instanciar o cliente primário (OpenAI)
primary_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def get_resilient_chat_completion(system_prompt: str, user_prompt: str) -> str:
    """
    Função que tenta primeiro o cliente primário (OpenAI) e, em caso de falha,
    faz fallback para o cliente secundário (Ollama).
    """
    # Tentar primeiro com o cliente primário (OpenAI)
    try:
        response = await primary_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e_primary:
        log.warning(f'Falha no LLM Primário (OpenAI): {e_primary}. Tentando fallback (Ollama).')
        
        # Em caso de falha no primário, tentar com o Ollama diretamente via httpx
        try:
            ollama_base_url = os.getenv("OLLAMA_API_BASE_URL")
            ollama_model_name = os.getenv("OLLAMA_CHAT_MODEL_NAME")
            
            if not ollama_base_url or not ollama_model_name:
                raise Exception("Variáveis de ambiente do Ollama não configuradas corretamente")
            
            payload = {
                "model": ollama_model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ollama_base_url.rstrip('/')}/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                else:
                    raise Exception(f"Erro na API do Ollama: {response.status_code} - {response.text}")
                    
        except Exception as e_fallback:
            log.error(f'Falha no LLM de Fallback (Ollama): {e_fallback}.')
            return 'Desculpe, nossos sistemas de IA estão temporariamente indisponíveis. Por favor, tente novamente em alguns instantes.'