#!/usr/bin/env python3
"""
FastAPI server for Concept MRI - MoE interpretability through Concept Trajectory Analysis.
"""

from contextlib import asynccontextmanager
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import torch
from api.routers import probes, experiments, generation, prompts
from api.dependencies import initialize_capture_service, is_model_loaded

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model once
    print("🚀 Starting Concept MRI API - loading model...")
    start = time.time()
    try:
        await initialize_capture_service()
        elapsed = time.time() - start
        print(f"✅ Model loaded successfully in {elapsed:.0f}s - API ready")
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Model loading failed after {elapsed:.0f}s: {e}")
        print("✅ API started in limited mode (analysis endpoints work, probe capture won't)")
    yield
    # Shutdown
    print("🛑 Shutting down Concept MRI API")

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
app.include_router(experiments.router, prefix="/api")
app.include_router(generation.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Concept MRI API", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": is_model_loaded(),
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "sessions_available": True,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
