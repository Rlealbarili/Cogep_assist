from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Servidor respondendo corretamente"}

@app.get("/api/v1/test")
def test_endpoint():
    return {"status": "ok"}