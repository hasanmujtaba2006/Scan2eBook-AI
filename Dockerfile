FROM python:3.9-slim-bullseye

# Install minimal Tesseract, language packs, and light-weight system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-urd \
    tesseract-ocr-hin \
    tesseract-ocr-ara \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ensure we use headless OpenCV in requirements to save memory
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]