#!/usr/bin/env python3
"""
FastAPI server for Concept MRI - MoE interpretability through Concept Trajectory Analysis.
"""

from contextlib import asynccontextmanager
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import torch
from api.routers import probes, routes, clustering, insights, temporal, generation, prompts, agent
from api.dependencies import initialize_capture_service, is_model_loaded, get_loading_status

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Concept MRI API")
    await initialize_capture_service()  # starts background thread, returns immediately
    logger.info("API serving — model loading in background")
    yield
    logger.info("Shutting down Concept MRI API")

# Create FastAPI app
app = FastAPI(title="Concept MRI API", version="1.0", lifespan=lifespan)

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(probes.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
app.include_router(clustering.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(temporal.router, prefix="/api")
app.include_router(generation.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(agent.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Concept MRI API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": is_model_loaded(),
        "loading": get_loading_status(),
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "sessions_available": True,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
