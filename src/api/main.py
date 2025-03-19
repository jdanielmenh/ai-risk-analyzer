from fastapi import FastAPI
from src.api.routers.search_router import router as search_router

# FastAPI Instance
app = FastAPI(title="AIRA API - Vector Search", version="1.0.0")

# Include the search router
app.include_router(search_router, prefix="/api", tags=["search"])