from fastapi import FastAPI

app = FastAPI(title="Jawab")


@app.get("/health")
def health():
    return {"status": "ok"}
