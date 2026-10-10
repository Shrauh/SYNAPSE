"""
Ollama Status API — Check local LLM availability.
"""
from fastapi import APIRouter
from app.ai_module.llm.ollama_client import check_ollama_status

router = APIRouter(prefix="/ollama", tags=["Ollama LLM"])


@router.get("/status")
async def ollama_status():
    """Check Ollama connection and available models."""
    return await check_ollama_status()
