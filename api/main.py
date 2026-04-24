import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


AI_API_KEY = os.getenv("AI_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
REVIEW_TIMEOUT_SECONDS = int(os.getenv("REVIEW_TIMEOUT_SECONDS", "300"))
PROMPT_PATH = Path(__file__).parent / "prompt.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")

app = FastAPI(title="llm-gateway", version="0.1.0")


class ReviewTaskRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    model: str | None = None


class ReviewTaskResponse(BaseModel):
    model: str
    duration_seconds: float
    result: str


def verify_api_key(x_api_key: str | None) -> None:
    if not AI_API_KEY or AI_API_KEY == "change-this-secret-key":
        raise HTTPException(
            status_code=500,
            detail="Server API key is not configured. Change AI_API_KEY in .env.",
        )

    if x_api_key != AI_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def build_review_messages(task_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Проанализируй задачу:\n\n{task_text}"},
    ]


async def get_ollama_status() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
        return {
            "status": "ok",
            "models_count": len(data.get("models", [])),
        }
    except Exception as exc:  # noqa: BLE001 - health endpoint must not crash
        return {
            "status": "error",
            "error": str(exc),
        }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "llm-gateway",
        "default_model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_URL,
        "ollama": await get_ollama_status(),
    }


@app.post("/review-task", response_model=ReviewTaskResponse)
async def review_task(
    request: ReviewTaskRequest,
    x_api_key: str | None = Header(default=None),
) -> ReviewTaskResponse:
    verify_api_key(x_api_key)

    model = request.model or OLLAMA_MODEL

    payload = {
        "model": model,
        "messages": build_review_messages(request.text),
        "stream": False,
        "format": "json",
        "options": {
            "num_ctx": 2048,
            "num_predict": 400,
            "temperature": 0.1,
        },
    }

    started_at = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=REVIEW_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot connect to Ollama: {str(exc)}",
        ) from exc

    duration_seconds = round(time.perf_counter() - started_at, 3)
    result = data.get("message", {}).get("content", "")

    if not result:
        raise HTTPException(
            status_code=502,
            detail="Ollama returned empty response.",
        )

    return ReviewTaskResponse(
        model=data.get("model", model),
        duration_seconds=duration_seconds,
        result=result,
    )
