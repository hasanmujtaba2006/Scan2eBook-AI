import os
import io
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# Added ImageEnhance for Contrast/Sharpness
from PIL import Image, ImageOps, ImageEnhance 
from groq import Groq
from paddleocr import PaddleOCR

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🚀 Loading HD AI Models...")
# Initialize standard models
ocr_ur = PaddleOCR(lang='ur')
ocr_en = PaddleOCR(lang='en')
print("✅ Models Ready!")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def optimize_image(image: Image.Image) -> Image.Image:
    """
    HD Pre-processing Pipeline:
    1. Fix Rotation
    2. Resize (Keep High Quality 2000px)
    3. Boost Contrast & Sharpness (Crucial for Urdu)
    """
    # 1. Fix Orientation
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    # 2. Resize (Increased to 2000px for better detail)
    max_dimension = 2000 
    if max(image.size) > max_dimension:
        ratio = max_dimension / max(image.size)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # 3. Convert to RGB
    image = image.convert("RGB")

    # 4. Apply Filters (Magic Step)
    # Increase Contrast by 50%
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # Increase Sharpness by 2x (Makes text edges crisp)
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)

    return image

@app.get("/")
async def root():
    return {"message": "HD OCR Server Running ⚡"}

@app.post("/process-page")
async def process_page(
    file: UploadFile = File(...), 
    language: str = Form("ur")
):
    try:
        contents = await file.read()
        raw_image = Image.open(io.BytesIO(contents))
        
        # Apply HD Optimization
        processed_image = optimize_image(raw_image)
        img_array = np.array(processed_image)

        engine = ocr_en if language == 'en' else ocr_ur
        print(f"Processing {language} page...")

        # Run OCR
        result = engine.ocr(img_array)

        extracted_text = ""
        if result and result[0]:
            extracted_text = "\n".join([line[1][0] for line in result[0]])

        # DEBUG LOG: See how much text was actually found
        print(f"🔍 Raw OCR Found: {len(extracted_text)} characters")

        if len(extracted_text) < 10:
            return {"clean": "Text too blurry. Please take a clearer photo."}

        # AI Correction
        prompt_lang = "English" if language == "en" else "Urdu"
        
        # Updated Prompt to be less aggressive (Don't delete text)
        system_prompt = (
            f"You are an expert {prompt_lang} editor. "
            "The user will provide text scanned from a book. "
            "The OCR might have some errors, but DO NOT summarize. "
            "Keep ALL the original sentences. Just fix spelling and grammar. "
            "Output ONLY the full corrected text."
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