FROM python:3.9-slim

# Install only the essential Tesseract OCR engine
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements first (better for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

EXPOSE 8000

# Start the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]