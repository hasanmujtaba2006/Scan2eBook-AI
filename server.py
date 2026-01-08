import os
import io
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from groq import Groq
# New Powerful OCR Engine
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

# --- GLOBAL INITIALIZATION (SPEED BOOST) ---
# Load model once at startup, not every request
print("Loading PaddleOCR Model... (This takes 10s on first run)")
# use_gpu=False for Hugging Face Free Tier (CPU only)
ocr_engine = PaddleOCR(use_angle_cls=True, lang='ur', use_gpu=False, show_log=False)
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
        
        # 2. Convert to format Paddle understands (Numpy Array)
        img_array = np.array(image)

        # 3. Perform OCR (The Heavy Lifting)
        # cls=True fixes upside-down images automatically
        result = ocr_engine.ocr(img_array, cls=True)

        # 4. Extract Text
        # Paddle returns a complex list of boxes/text/confidence. We just want text.
        extracted_text = ""
        if result and result[0]:
            # Join all detected lines with a newline
            extracted_text = "\n".join([line[1][0] for line in result[0]])

        if not extracted_text.strip():
            return {"clean": "No text detected. Try a clearer photo."}

        # 5. AI Cleaning (Llama 3.1)
        # Now the AI gets much better input, so it works faster and better.
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