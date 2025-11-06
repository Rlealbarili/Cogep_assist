import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Carregar as variáveis de ambiente
load_dotenv()

async def test_fallback_real():
    # Salvar a chave original
    original_key = os.getenv("OPENAI_API_KEY")
    
    # Definir uma chave inválida temporariamente para testar o fallback
    os.environ["OPENAI_API_KEY"] = "invalid_key_for_testing"
    
    # Importar novamente após a alteração de ambiente
    # Usar o nosso cliente resiliente
    from agent_service.llm_client import get_resilient_chat_completion
    
    print("Testando fallback com OpenAI API inválida...")
    
    system_prompt = "Você é um assistente útil."
    user_prompt = "Responda com um simples 'FALLBACK_OK' para confirmar que você recebeu esta mensagem via fallback."
    
    # Isso deve falhar no primário e usar o fallback
    response = await get_resilient_chat_completion(system_prompt, user_prompt)
    
    print(f"Resposta recebida: {response}")
    
    # Restaurar a chave original
    os.environ["OPENAI_API_KEY"] = original_key
    
    print("Chave original restaurada.")

if __name__ == "__main__":
    asyncio.run(test_fallback_real())