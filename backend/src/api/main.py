#!/usr/bin/env python3
"""
FastAPI server for Concept MRI - Minimal working implementation.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import probes, experiments
from api.dependencies import initialize_capture_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model once
    print("🚀 Starting Concept MRI API - loading model...")
    await initialize_capture_service()
    print("✅ Model loaded successfully - API ready")
    yield
    # Shutdown: cleanup if needed
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

@app.get("/")
async def root():
    return {"message": "Concept MRI API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)