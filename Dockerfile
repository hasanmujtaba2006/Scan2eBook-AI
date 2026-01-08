# Python 3.9 se 3.10 par update kiya
FROM python:3.10-slim

# 1. Install System Dependencies (libgl1 for new Debian)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Create writable cache for PaddleOCR
RUN mkdir -p /app/.paddleocr && chmod -R 777 /app/.paddleocr
ENV HOME=/app

# 4. Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy app code
COPY . .

# 6. Expose port
EXPOSE 7860

# 7. Start app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]