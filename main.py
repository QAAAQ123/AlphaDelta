from fastapi import FastAPI

app = FastAPI(title="AlphaDelta API")

@app.get("/")
def read_root():
    return {"status": "AlpahDelta 개발 환경 초기화"}