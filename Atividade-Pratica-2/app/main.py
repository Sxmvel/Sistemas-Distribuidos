from fastapi import FastAPI

app = FastAPI(title="API de Biblioteca", version="1.0.0")

@app.get("/v1/saude")
def saude():
    return {"status": "ok"}