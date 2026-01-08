# Use Python 3.10 slim for a smaller footprint
FROM python:3.10-slim

# Install Tesseract, Urdu/Arabic packs, and OpenCV dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-urd \
    tesseract-ocr-ara \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user (Hugging Face Requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy and install requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create writable directories
RUN mkdir -p uploads outputs temp && chmod -R 777 uploads outputs temp

# Copy the rest of the application
COPY --chown=user:user . .

# Expose the mandatory Hugging Face port
EXPOSE 7860

# Run with Uvicorn on port 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]