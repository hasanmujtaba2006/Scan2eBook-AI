import os
import io
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
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

# --- GLOBAL INITIALIZATION (Dual Engine) ---
print("Loading OCR Models... (Please wait)")

# FIX: Removed 'show_log' and 'use_angle_cls'. Using simplest initialization.
# 1. Load Urdu Engine
ocr_ur = PaddleOCR(lang='ur')
print("✅ Urdu Model Ready")

# 2. Load English Engine
ocr_en = PaddleOCR(lang='en')
print("✅ English Model Ready")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.get("/")
async def root():
    return {"message": "Multi-Language OCR Server Running 🚀"}

@app.post("/process-page")
async def process_page(
    file: UploadFile = File(...), 
    language: str = Form("ur") # Default to Urdu
):
    try:
        # 1. Read Image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        img_array = np.array(image)

        # 2. Select Engine based on User Choice
        engine = ocr_en if language == 'en' else ocr_ur
        print(f"Processing with {language} engine...")

        # 3. Perform OCR
        # FIX: Removed 'cls=True' to prevent "unexpected keyword" error
        result = engine.ocr(img_array)

        extracted_text = ""
        if result and result[0]:
            extracted_text = "\n".join([line[1][0] for line in result[0]])

        if not extracted_text.strip():
            return {"clean": "No text detected."}

        # 4. Dynamic AI Prompt
        prompt_lang = "English" if language == "en" else "Urdu"
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": f"You are an expert {prompt_lang} editor. Correct the following text from OCR. Fix spelling/grammar. Output ONLY the corrected text."},
                {"role": "user", "content": extracted_text}
            ]
        )
        
        clean_text = completion.choices[0].message.content
        return {"clean": clean_text}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)