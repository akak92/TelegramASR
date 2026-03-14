"""
app.py - Bot Service

Telegram bot que recibe audios de médicos, los transcribe mediante el
servicio Transcriber (Azure Speech AI) y los corrige/formatea mediante
el servicio Corrector (Azure OpenAI). El resultado se almacena en MongoDB
y se responde al médico con un informe formateado.
"""

import os
import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import httpx
from dotenv import load_dotenv

from Components.MongoConnection import MongoConnection
from Components.PDFGenerator import PDFGenerator

pdf_generator = PDFGenerator()

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ========================
# Config
# ========================
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TRANSCRIBER_URL: str = os.getenv("TRANSCRIBER_URL", "http://transcriber:8001")
CORRECTOR_URL: str = os.getenv("CORRECTOR_URL", "http://corrector:8002")
MONGO_URI: str = os.getenv(
    "MONGO_URI",
    "mongodb://admin:adminpass@mongo:27017/MedicalASR?authSource=admin",
)
MONGO_DB: str = os.getenv("MONGO_DB_NAME", "MedicalASR")
MONGO_COLLECTION: str = os.getenv("MONGO_COLLECTION", "transcriptions")

if not TELEGRAM_TOKEN:
    raise RuntimeError("Falta la variable de entorno TELEGRAM_BOT_TOKEN")

mongo = MongoConnection(MONGO_URI, MONGO_DB, MONGO_COLLECTION)

# ========================
# Handlers de Telegram
# ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hola, soy el asistente de transcripción médica.\n\n"
        "Enviame un mensaje de voz o un archivo de audio y lo transcribiré "
        "y corregiré automáticamente, devolviéndote un informe médico formateado."
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = message.from_user
    chat_id = message.chat_id

    # Soporta tanto mensajes de voz como archivos de audio adjuntos
    audio_obj = message.voice or message.audio
    if not audio_obj:
        await message.reply_text(
            "⚠️ Por favor, enviá un mensaje de voz o un archivo de audio."
        )
        return

    await message.reply_text("🎙️ Audio recibido. Transcribiendo, aguardá un momento...")

    file_id = audio_obj.file_id
    duration = getattr(audio_obj, "duration", 0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"voice_{user.id}_{timestamp}.ogg"

    # Descarga el audio desde Telegram
    tg_file = await context.bot.get_file(file_id)
    audio_bytes = bytes(await tg_file.download_as_bytearray())

    # Inserta registro en MongoDB con estado PENDING
    record = {
        "telegram_user_id": user.id,
        "telegram_username": user.username or user.first_name,
        "chat_id": chat_id,
        "audio_filename": filename,
        "audio_duration_seconds": duration,
        "raw_transcription": None,
        "corrected_transcription": None,
        "created_at": datetime.now(timezone.utc),
        "status": "PENDING",
    }
    record_id = mongo.insert_record(record)

    try:
        # Paso 1: Transcripción
        async with httpx.AsyncClient(timeout=120.0) as client:
            transcribe_resp = await client.post(
                f"{TRANSCRIBER_URL}/transcribe",
                files={"audio": (filename, audio_bytes, "audio/ogg")},
            )
            transcribe_resp.raise_for_status()
        raw_text: str = transcribe_resp.json()["transcription"]
        logging.info("Transcripción obtenida para %s: %.80s...", filename, raw_text)
        mongo.update_record(
            record_id, {"raw_transcription": raw_text, "status": "TRANSCRIBED"}
        )

        # Paso 2: Corrección y formateo
        async with httpx.AsyncClient(timeout=120.0) as client:
            correct_resp = await client.post(
                f"{CORRECTOR_URL}/correct",
                json={"text": raw_text},
            )
            correct_resp.raise_for_status()
        corrected_text: str = correct_resp.json()["corrected"]
        logging.info("Corrección completada para %s.", filename)
        mongo.update_record(
            record_id,
            {"corrected_transcription": corrected_text, "status": "CORRECTED"},
        )

        # Respuesta al médico — texto
        try:
            await message.reply_text(
                f"📋 *Informe médico:*\n\n{corrected_text}",
                parse_mode="Markdown",
            )
        except Exception:
            await message.reply_text(f"📋 Informe médico:\n\n{corrected_text}")

        # Respuesta al médico — PDF
        try:
            pdf_bytes = pdf_generator.generate(
                corrected_text=corrected_text,
                raw_text=raw_text,
                username=user.username or user.first_name,
                timestamp=datetime.now(timezone.utc),
            )
            pdf_filename = f"informe_{timestamp}.pdf"
            await message.reply_document(
                document=pdf_bytes,
                filename=pdf_filename,
                caption="📄 Informe médico en PDF",
            )
            logging.info("PDF enviado: %s", pdf_filename)
        except Exception as exc:
            logging.error("Error generando PDF para %s: %s", filename, exc)

    except httpx.HTTPStatusError as exc:
        logging.error("HTTP error procesando %s: %s", filename, exc)
        mongo.update_record(record_id, {"status": "ERROR", "error": str(exc)})
        await message.reply_text(
            "❌ Ocurrió un error al procesar el audio. Intentá de nuevo más tarde."
        )
    except Exception as exc:
        logging.error("Error inesperado procesando %s: %s", filename, exc)
        mongo.update_record(record_id, {"status": "ERROR", "error": str(exc)})
        await message.reply_text(
            "❌ Ocurrió un error al procesar el audio. Intentá de nuevo más tarde."
        )


# ========================
# Main
# ========================

def main() -> None:
    logging.info("Iniciando bot médico de transcripción...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))

    logging.info("Bot corriendo. Esperando mensajes... (Ctrl+C para detener)")
    app.run_polling()


if __name__ == "__main__":
    main()
