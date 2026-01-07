FROM python:3.9-bullseye

# Install Tesseract, OpenCV dependencies, and language packs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-urd \
    tesseract-ocr-hin \
    tesseract-ocr-ara \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]