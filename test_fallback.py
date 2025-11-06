import asyncio
import os
from agent_service.llm_client import get_resilient_chat_completion

async def test_fallback():
    # Testar a funcionalidade de fallback
    print("Testando funcionalidade de fallback...")
    
    system_prompt = "Você é um assistente útil."
    user_prompt = "Responda com um simples 'OK' para confirmar que você recebeu esta mensagem."
    
    # Isso usará o cliente primário (OpenAI) ou fallback para Ollama
    response = await get_resilient_chat_completion(system_prompt, user_prompt)
    
    print(f"Resposta recebida: {response}")

if __name__ == "__main__":
    asyncio.run(test_fallback())