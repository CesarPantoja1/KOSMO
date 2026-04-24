from fastapi import FastAPI

app = FastAPI(
    title="KOSMO API",
    description="Backend API for KOSMO platform",
    version="0.1.0"
)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to KOSMO API"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }