FROM python:3.11-slim

# ffmpeg: conversión OGG/MP3 → WAV (pydub)
# libssl-dev + libgomp1: dependencias del SDK de Azure Speech en Linux
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libssl-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
