"""FastAPI application entry point for the World Cup Predictor backend."""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.groups import router as groups_router
from backend.routes.knockout import router as knockout_router
from backend.routes.predictions import router as predictions_router

# Configure logging so errors show up in the console
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Read the football-data.org API key from environment
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")

app = FastAPI(
    title="World Cup Predictor API",
    description="REST API for World Cup 2026 predictions and tournament data",
    version="0.1.0",
)

# Configure CORS middleware to allow requests from the frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route handlers
app.include_router(groups_router)
app.include_router(knockout_router)
app.include_router(predictions_router)
