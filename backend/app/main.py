from fastapi import FastAPI
from app.modules.ingestion import router as ingestion_router
from app.modules.analysis import router as analysis_router # <-- NEW IMPORT

app = FastAPI(
    title="Inclusify Backend",
    description="API for checking inclusive language"
)

@app.get("/")
async def root():
    return {"message": "Inclusify API is running", "status": "OK"}

# Connect the routers
app.include_router(ingestion_router.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
app.include_router(analysis_router.router, prefix="/api/v1/analysis", tags=["Analysis"]) # <-- NEW ROUTER

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)