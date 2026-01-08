import os
import io
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pytesseract
from PIL import Image
from groq import Groq
# IMPORTANT: This import requires the library to be installed
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

# Helper to delete file after download
def remove_file(path: str):
    try:
        os.unlink(path)
    except Exception:
        pass

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
async def generate_epub(book: BookData, background_tasks: BackgroundTasks):
    # 1. Check if pages exist
    if not book.pages:
        raise HTTPException(status_code=400, detail="Book is empty")

    # 2. Define safe path in /tmp
    file_path = f"/tmp/{uuid.uuid4()}.epub"

    try:
        # 3. Create Book
        eb = epub.EpubBook()
        eb.set_identifier(f'id_{book.title}')
        eb.set_title(book.title)
        eb.set_language('ur')

        chapters = []
        for i, page_text in enumerate(book.pages):
            c = epub.EpubHtml(title=f'Page {i+1}', file_name=f'page_{i+1}.xhtml', lang='ur')
            c.content = f'<div dir="rtl" style="text-align: right; padding: 20px;"><h1>Page {i+1}</h1><p>{page_text}</p></div>'
            eb.add_item(c)
            chapters.append(c)

        eb.toc = (tuple(chapters),)
        eb.add_item(epub.EpubNcx())
        eb.add_item(epub.EpubNav())
        eb.spine = ['nav'] + chapters

        # 4. Write file to disk (This works in /tmp)
        epub.write_epub(file_path, eb, {})

        # 5. Schedule cleanup
        background_tasks.add_task(remove_file, file_path)

        # 6. Return file
        return FileResponse(
            path=file_path, 
            filename=f"{book.title}.epub",
            media_type='application/epub+zip'
        )

    except Exception as e:
        print(f"EPUB Error: {str(e)}")
        # Clean up if crash
        if os.path.exists(file_path):
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)