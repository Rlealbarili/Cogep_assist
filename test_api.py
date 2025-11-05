import asyncio
import httpx

async def test_api():
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Testar endpoint raiz
        response = await client.get("/")
        print(f"GET / -> {response.status_code}: {response.text}")
        
        # Testar endpoint de ingestão
        data = {
            "source_uri": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "namespace": "test_namespace"
        }
        response = await client.post("/api/v1/ingest", json=data)
        print(f"POST /api/v1/ingest -> {response.status_code}: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_api())