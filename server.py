import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image
from groq import Groq

app = FastAPI()

# 1. FIX: Comprehensive CORS Policy (Must be BEFORE routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use ["*"] to allow all, or list your Vercel URL specifically
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize Groq (Secret must be set in HF Space Settings)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.get("/")
async def root():
    return {"message": "OCR Backend is Running!"}

@app.post("/process-page")
async def process_page(file: UploadFile = File(...)):
    try:
        # Read and open image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # OCR for Urdu and Arabic
        raw_text = pytesseract.image_to_string(image, lang='urd+ara')
        
        if not raw_text.strip():
            return {"raw": "", "clean": "No text detected in image."}

        # AI Cleaning using Llama 3.1 (Current supported model)
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert Urdu editor. Fix OCR errors in the following Urdu text. Keep it original, just fix spelling/formatting."},
                {"role": "user", "content": raw_text}
            ]
        )
        
        clean_text = completion.choices[0].message.content
        return {"raw": raw_text, "clean": clean_text}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)