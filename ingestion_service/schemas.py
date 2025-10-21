from pydantic import BaseModel, HttpUrl

class IngestionRequest(BaseModel):
    """
    Define o corpo da requisição para o endpoint de ingestão.
    """
    source_uri: HttpUrl
    namespace: str
    metadata: dict | None = None
