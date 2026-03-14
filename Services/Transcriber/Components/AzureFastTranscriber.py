"""
AzureFastTranscriber.py

Transcribe archivos de audio usando Azure Speech AI con reconocimiento
continuo, lo que permite procesar dictados médicos de cualquier duración.

Soporta OGG/Opus (mensajes de voz de Telegram), WAV, MP3 y otros formatos
mediante conversión interna a PCM 16 kHz mono con pydub + ffmpeg.
"""

import threading
import logging
from io import BytesIO

import azure.cognitiveservices.speech as speechsdk  # type: ignore
from pydub import AudioSegment  # type: ignore

logger = logging.getLogger(__name__)


class AzureFastTranscriber:
    def __init__(self, key: str, region: str, language: str = "es-AR"):
        self.speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        self.speech_config.speech_recognition_language = language

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _to_pcm_wav(self, audio_buffer: BytesIO, filename: str) -> BytesIO:
        """Convierte cualquier formato de audio a PCM 16 kHz mono WAV."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "ogg"
        audio_segment: AudioSegment = AudioSegment.from_file(audio_buffer, format=ext)
        audio_segment = (
            audio_segment
            .set_frame_rate(16000)
            .set_channels(1)
            .set_sample_width(2)
        )
        wav_buffer = BytesIO()
        audio_segment.export(wav_buffer, format="wav")
        wav_buffer.seek(0)
        return wav_buffer

    # ------------------------------------------------------------------
    # Transcripción principal
    # ------------------------------------------------------------------

    def transcribe(self, audio_buffer: BytesIO, filename: str = "audio.ogg") -> str:
        """
        Transcribe un audio utilizando reconocimiento continuo de Azure Speech AI.

        Se usa reconocimiento continuo (start_continuous_recognition) en lugar de
        recognize_once para capturar dictados médicos de cualquier duración.

        Args:
            audio_buffer: Buffer en memoria con el audio original.
            filename:     Nombre del archivo (se usa para inferir su extensión).

        Returns:
            Texto transcripto unido en un solo string.
        """
        wav_buffer = self._to_pcm_wav(audio_buffer, filename)

        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config,
        )

        results: list[str] = []
        done = threading.Event()

        def on_recognized(evt: speechsdk.SpeechRecognitionEventArgs) -> None:
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                results.append(evt.result.text)
                logger.debug("Segmento reconocido: %s", evt.result.text)

        def on_canceled(evt: speechsdk.SpeechRecognitionCanceledEventArgs) -> None:
            if evt.result.cancellation_details.reason != speechsdk.CancellationReason.EndOfStream:
                logger.error(
                    "Reconocimiento cancelado: %s — %s",
                    evt.result.cancellation_details.reason,
                    evt.result.cancellation_details.error_details,
                )
            done.set()

        def on_session_stopped(evt) -> None:
            done.set()

        recognizer.recognized.connect(on_recognized)
        recognizer.session_stopped.connect(on_session_stopped)
        recognizer.canceled.connect(on_canceled)

        recognizer.start_continuous_recognition()

        # Escribe el audio al stream en un hilo separado para no bloquear
        def _write_audio() -> None:
            chunk_size = 4096
            while True:
                chunk = wav_buffer.read(chunk_size)
                if not chunk:
                    break
                push_stream.write(chunk)
            push_stream.close()

        writer = threading.Thread(target=_write_audio, daemon=True)
        writer.start()
        writer.join()

        # Espera a que Azure termine de procesar el audio
        done.wait(timeout=60)
        recognizer.stop_continuous_recognition()

        if not results:
            return "[No se reconoció ningún texto]"

        return " ".join(results)
