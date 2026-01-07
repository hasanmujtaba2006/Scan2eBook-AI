FROM python:3.9-slim

# Install Tesseract engine AND the specific language packs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-urd \
    tesseract-ocr-hin \
    tesseract-ocr-ara \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
# Note: 'urd' is Urdu, 'hin' is Hindi, 'ara' is Arabic
WORKDIR /app

# Copy and install requirements first (better for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

EXPOSE 8000

# Start the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]