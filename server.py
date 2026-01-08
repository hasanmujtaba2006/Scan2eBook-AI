import os
import io
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class BookData(BaseModel):
    title: str
    pages: List[str]

@app.get("/")
async def root():
    return {"message": "Backend Running"}

@app.post("/process-page")
async def process_page(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        raw_text = pytesseract.image_to_string(image, lang='urd+ara')
        
        if not raw_text.strip():
            return {"clean": "No text detected."}

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert Urdu editor. Fix OCR errors. Return ONLY the cleaned Urdu text."},
                {"role": "user", "content": raw_text}
            ]
        )
        return {"clean": completion.choices[0].message.content}
    except Exception as e:
        print(f"OCR Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-epub")
async def generate_epub(book: BookData):
    try:
        # 1. Create Book
        eb = epub.EpubBook()
        eb.set_identifier(f'id_{book.title}')
        eb.set_title(book.title)
        eb.set_language('ur')
        
        if not book.pages:
            raise HTTPException(status_code=400, detail="Book has no pages")

        # 2. Add Chapters
        chapters = []
        for i, page_text in enumerate(book.pages):
            c = epub.EpubHtml(title=f'Page {i+1}', file_name=f'page_{i+1}.xhtml', lang='ur')
            # Add simple CSS for clean text
            c.content = f"""
                <div dir="rtl" style="text-align: right; font-family: sans-serif; padding: 20px;">
                    <h1>Page {i+1}</h1>
                    <p style="white-space: pre-wrap;">{page_text}</p>
                </div>
            """
            eb.add_item(c)
            chapters.append(c)

        eb.toc = (tuple(chapters),)
        eb.add_item(epub.EpubNcx())
        eb.add_item(epub.EpubNav())
        eb.spine = ['nav'] + chapters

        # 3. FIX: Write to RAM Buffer instead of Disk
        buffer = io.BytesIO()
        epub.write_epub(buffer, eb, {})
        buffer.seek(0)

        # 4. Return Stream
        return StreamingResponse(
            buffer, 
            headers={'Content-Disposition': f'attachment; filename="{book.title}.epub"'},
            media_type='application/epub+zip'
        )

    except Exception as e:
        print(f"EPUB Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)