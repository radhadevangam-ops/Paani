from fastapi import FastAPI

app = FastAPI(
    title="Paani API",
    description="Water supply monitoring and prediction platform",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "Welcome to Paani!",
        "status": "running"
    }
