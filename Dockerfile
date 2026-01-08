FROM python:3.9-slim

# 1. Install System Dependencies
# 'libgl1-mesa-glx' ko 'libgl1' se badal diya gaya hai
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Create a writable cache directory for PaddleOCR
RUN mkdir -p /app/.paddleocr && chmod -R 777 /app/.paddleocr
ENV HOME=/app

# 4. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy app code
COPY . .

# 6. Expose the port
EXPOSE 7860

# 7. Start the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]