"""
app.py - Transcriber Service

Microservicio FastAPI que recibe archivos de audio (OGG, MP3, WAV, etc.)
y devuelve la transcripción usando Azure Speech AI con reconocimiento continuo.
"""

import os
import logging
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from Components.AzureFastTranscriber import AzureFastTranscriber

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ========================
# Config
# ========================
AZURE_SPEECH_KEY: str = os.getenv("AZURE_SPEECH_AI_KEY", "")
AZURE_SPEECH_REGION: str = os.getenv("AZURE_SPEECH_AI_REGION", "")
SPEECH_LANGUAGE: str = os.getenv("SPEECH_LANGUAGE", "es-AR")

if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
    raise RuntimeError(
        "Faltan las variables de entorno AZURE_SPEECH_AI_KEY o AZURE_SPEECH_AI_REGION"
    )

transcriber = AzureFastTranscriber(
    key=AZURE_SPEECH_KEY,
    region=AZURE_SPEECH_REGION,
    language=SPEECH_LANGUAGE,
)

# ========================
# FastAPI app
# ========================
app = FastAPI(
    title="Transcriber Service",
    description="Transcribe archivos de audio usando Azure Speech AI.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.get("/health", tags=["Health"])
def health() -> JSONResponse:
    return JSONResponse(content={"status": "Transcriber Service is OK"})


@app.post("/transcribe", tags=["Transcription"])
def transcribe(audio: UploadFile = File(...)) -> JSONResponse:
    """
    Recibe un archivo de audio y devuelve su transcripción.
    Soporta OGG/Opus (Telegram), WAV, MP3, entre otros.
    """
    filename = audio.filename or "audio.ogg"
    audio_bytes = audio.file.read()

    logging.info("Transcribiendo '%s' (%d bytes)...", filename, len(audio_bytes))

    try:
        audio_buffer = BytesIO(audio_bytes)
        transcription = transcriber.transcribe(audio_buffer, filename)
        logging.info("Transcripción exitosa para '%s': %.80s...", filename, transcription)
        return JSONResponse(content={"transcription": transcription})
    except Exception as exc:
        logging.error("Error transcribiendo '%s': %s", filename, exc)
        raise HTTPException(status_code=500, detail=str(exc))
