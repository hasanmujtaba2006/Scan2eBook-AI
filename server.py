import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image
from groq import Groq
import io

app = FastAPI()

# Enable CORS so your local frontend can talk to Hugging Face
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq using the Secret variable
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

@app.post("/process-page")
async def process_page(file: UploadFile = File(...)):
    # Read image
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    
    # OCR for Urdu and Arabic
    raw_text = pytesseract.image_to_string(image, lang='urd+ara')
    
    # AI Cleaning using Groq
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "You are an expert Urdu editor. Fix OCR errors in the following Urdu text. Keep it original, just fix spelling/formatting."},
            {"role": "user", "content": raw_text}
        ]
    )
    
    clean_text = completion.choices[0].message.content
    return {"raw": raw_text, "clean": clean_text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)