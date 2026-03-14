"""
app.py - Corrector Service

Microservicio FastAPI que recibe una transcripción médica cruda y devuelve
el texto corregido y formateado como informe médico profesional,
utilizando Azure OpenAI.
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from Components.LLM import LLM

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

llm = LLM()

# ========================
# FastAPI app
# ========================
app = FastAPI(
    title="Corrector Service",
    description="Corrige y formatea transcripciones médicas usando Azure OpenAI.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


class CorrectionRequest(BaseModel):
    text: str


@app.get("/health", tags=["Health"])
def health() -> JSONResponse:
    return JSONResponse(content={"status": "Corrector Service is OK"})


@app.post("/correct", tags=["Correction"])
def correct(request: CorrectionRequest) -> JSONResponse:
    """
    Recibe una transcripción médica cruda y devuelve el texto corregido
    y formateado como informe médico.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío.")

    logging.info("Corrigiendo transcripción: %.80s...", text)

    try:
        corrected = llm.correct(text)
        logging.info("Corrección exitosa.")
        return JSONResponse(content={"corrected": corrected})
    except Exception as exc:
        logging.error("Error en la corrección: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
