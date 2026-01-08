# 1. Start with the base image
FROM python:3.10-slim

# 2. Install system-level packages first (as root)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-urd \
    tesseract-ocr-ara \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Create the user Hugging Face expects
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# 4. Set the working directory INSIDE the user's home
WORKDIR $HOME/app

# 5. Create writable folders BEFORE copying code to avoid permission errors
RUN mkdir -p uploads outputs temp && chmod -R 777 uploads outputs temp

# 6. Copy requirements and install
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy the rest of your app
COPY --chown=user:user . .

# 8. Expose port and start
EXPOSE 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]