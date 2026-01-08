import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import pytesseract
from PIL import Image
from groq import Groq
from ebooklib import epub
from typing import List
from pydantic import BaseModel

app = FastAPI()

# CORS: Allow connection from Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Data Model for receiving pages
class BookData(BaseModel):
    title: str
    pages: List[str]

@app.get("/")
async def root():
    return {"message": "Scan2Ebook Backend is Running!"}

@app.post("/process-page")
async def process_page(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # OCR (Phase 1: Tesseract - We will upgrade this to PaddleOCR in next step)
        raw_text = pytesseract.image_to_string(image, lang='urd+ara')
        
        if not raw_text.strip():
            return {"clean": "No text detected."}

        # AI Cleaning
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert Urdu editor. Fix OCR errors. Return ONLY the cleaned Urdu text, no intro/outro."},
                {"role": "user", "content": raw_text}
            ]
        )
        
        clean_text = completion.choices[0].message.content
        return {"clean": clean_text}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-epub")
async def generate_epub(book: BookData):
    try:
        # Create EPUB Book
        eb = epub.EpubBook()
        eb.set_identifier(f'id_{book.title}')
        eb.set_title(book.title)
        eb.set_language('ur')

        # Add Chapters
        chapters = []
        for i, page_text in enumerate(book.pages):
            c = epub.EpubHtml(title=f'Page {i+1}', file_name=f'page_{i+1}.xhtml', lang='ur')
            # Add RTL styling for Urdu
            c.content = f'<div dir="rtl" style="text-align: right; font-family: sans-serif;"><h1>Page {i+1}</h1><p>{page_text}</p></div>'
            eb.add_item(c)
            chapters.append(c)

        # Navigation
        eb.toc = (tuple(chapters),)
        eb.add_item(epub.EpubNcx())
        eb.add_item(epub.EpubNav())

        # Define CSS style
        style = 'body { font-family: sans-serif; }'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        eb.add_item(nav_css)

        # Spine (Reading Order)
        eb.spine = ['nav'] + chapters

        # Write to memory buffer
        buffer = io.BytesIO()
        epub.write_epub(buffer, eb)
        buffer.seek(0)

        # Return file for download
        headers = {'Content-Disposition': f'attachment; filename="{book.title}.epub"'}
        return StreamingResponse(buffer, headers=headers, media_type='application/epub+zip')

    except Exception as e:
        print(f"EPUB Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)