import os
import io
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps
from groq import Groq
from paddleocr import PaddleOCR

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL INITIALIZATION ---
print("🚀 Loading AI Models... (Please wait)")

# Load Models (CPU Optimized)
# We disable 'use_angle_cls' here to save RAM, as we fix rotation via EXIF now.
ocr_ur = PaddleOCR(lang='ur', use_angle_cls=False, show_log=False)
ocr_en = PaddleOCR(lang='en', use_angle_cls=False, show_log=False)

print("✅ Models Ready!")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def optimize_image(image: Image.Image) -> Image.Image:
    """
    1. Fix Rotation (EXIF): Solves 'upside down' text.
    2. Convert to Grayscale: Solves color noise.
    3. Resize: Solves speed issues (limit to 1280px).
    """
    # 1. Fix Orientation (Phone cameras often save rotated)
    image = ImageOps.exif_transpose(image)

    # 2. Resize if too big (Speed Boost)
    max_dimension = 1280
    if max(image.size) > max_dimension:
        ratio = max_dimension / max(image.size)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # 3. Convert to RGB (Paddle expects 3 channels)
    return image.convert("RGB")

@app.get("/")
async def root():
    return {"message": "High-Performance OCR Server Running ⚡"}

@app.post("/process-page")
async def process_page(
    file: UploadFile = File(...), 
    language: str = Form("ur")
):
    try:
        # 1. Read & Optimize Image
        contents = await file.read()
        raw_image = Image.open(io.BytesIO(contents))
        
        # SPEED & ACCURACY BOOST HERE
        processed_image = optimize_image(raw_image)
        img_array = np.array(processed_image)

        # 2. Select Engine
        engine = ocr_en if language == 'en' else ocr_ur
        print(f"Processing {language} page...")

        # 3. Run OCR (Fast Mode)
        result = engine.ocr(img_array, cls=False)

        extracted_text = ""
        if result and result[0]:
            # Join text blocks
            extracted_text = "\n".join([line[1][0] for line in result[0]])

        if not extracted_text.strip():
            return {"clean": "No text detected. Try a clearer photo."}

        # 4. AI Correction (Llama 3.1)
        prompt_lang = "English" if language == "en" else "Urdu"
        system_prompt = (
            f"You are an expert {prompt_lang} editor. "
            "The user will provide text scanned from a book. "
            "Fix OCR errors, broken words, and spelling. "
            "Output ONLY the corrected text. Do not add any introduction or notes."
        )

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": extracted_text}
            ]
        )
        
        clean_text = completion.choices[0].message.content
        return {"clean": clean_text}

    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)