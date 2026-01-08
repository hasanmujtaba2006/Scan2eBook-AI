import os
import io
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
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

# --- GLOBAL INITIALIZATION ---
print("Loading PaddleOCR Model... (This takes 10s on first run)")

# FIX: Removed 'use_gpu' and 'show_log'. Only keeping essential params.
# Paddle will automatically use CPU since GPU is not available.
ocr_engine = PaddleOCR(use_angle_cls=True, lang='ur') 

print("PaddleOCR Model Ready!")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.get("/")
async def root():
    return {"message": "PaddleOCR Server is Running 🚀"}

@app.post("/process-page")
async def process_page(file: UploadFile = File(...)):
    try:
        # 1. Read Image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # 2. Convert to Numpy Array
        img_array = np.array(image)

        # 3. Perform OCR
        result = ocr_engine.ocr(img_array, cls=True)

        # 4. Extract Text
        extracted_text = ""
        if result and result[0]:
            # Join text cleanly
            extracted_text = "\n".join([line[1][0] for line in result[0]])

        if not extracted_text.strip():
            return {"clean": "No text detected. Try a clearer photo."}

        # 5. AI Cleaning
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert Urdu editor. Correct the following Urdu text derived from OCR. Fix spelling and spacing. Output ONLY the corrected Urdu text."},
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