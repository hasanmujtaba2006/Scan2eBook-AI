import os
import io
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pytesseract
from PIL import Image
from groq import Groq
from ebooklib import epub

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
        
        # OCR Processing
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
        print(f"OCR Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-epub")
async def generate_epub(book: BookData):
    tmp_path = None
    try:
        # 1. Create Book Object
        eb = epub.EpubBook()
        eb.set_identifier(f'id_{book.title}')
        eb.set_title(book.title)
        eb.set_language('ur')

        # 2. Add Chapters
        chapters = []
        for i, page_text in enumerate(book.pages):
            c = epub.EpubHtml(title=f'Page {i+1}', file_name=f'page_{i+1}.xhtml', lang='ur')
            c.content = f'<div dir="rtl" style="text-align: right; font-family: sans-serif;"><h1>Page {i+1}</h1><p>{page_text}</p></div>'
            eb.add_item(c)
            chapters.append(c)

        # 3. Add Navigation & Styles
        eb.toc = (tuple(chapters),)
        eb.add_item(epub.EpubNcx())
        eb.add_item(epub.EpubNav())
        style = 'body { font-family: sans-serif; }'
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        eb.add_item(nav_css)
        eb.spine = ['nav'] + chapters

        # 4. FIX: Write to a Temporary File first (RAM write causes crash)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp:
            tmp_path = tmp.name
        
        epub.write_epub(tmp_path, eb)

        # 5. Read file back into memory for download
        with open(tmp_path, "rb") as f:
            file_data = f.read()

        # 6. Cleanup: Delete the temp file
        os.unlink(tmp_path)

        # 7. Return the file
        return StreamingResponse(
            io.BytesIO(file_data), 
            headers={'Content-Disposition': f'attachment; filename="{book.title}.epub"'},
            media_type='application/epub+zip'
        )

    except Exception as e:
        # Cleanup if error occurs
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        print(f"EPUB Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)