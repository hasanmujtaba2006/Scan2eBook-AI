import os
import shutil
import cv2
import pytesseract
from typing import List
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from ebooklib import epub
from dotenv import load_dotenv # Import the secret manager

# --- 1. LOAD SECRETS ---
load_dotenv() # This reads your .env file

# --- 2. CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Get key securely
#pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Check if key exists
if not GROQ_API_KEY:
    print("❌ ERROR: GROQ_API_KEY not found! Did you create the .env file?")

# --- 3. INITIALIZE APP (Crucial Step!) ---
app = FastAPI()
client = Groq(api_key=GROQ_API_KEY)

# Allow Frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER FUNCTIONS ---

def preprocess_image(img_path):
    img = cv2.imread(img_path)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)

def clean_text_with_ai(raw_text):
    if not raw_text.strip(): return "No text detected."
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a book editor. Fix OCR errors. Return clean text."},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception:
        return raw_text

def create_book_from_pages(pages_text, output_path, book_title):
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title(book_title)
    book.set_language("en")

    chapters = []
    for i, page_content in enumerate(pages_text):
        chapter_title = f'Page {i+1}'
        filename = f'page_{i+1}.xhtml'
        c = epub.EpubHtml(title=chapter_title, file_name=filename, lang='en')
        formatted_text = page_content.replace("\n", "<br>")
        c.content = f"<h2>{chapter_title}</h2><p>{formatted_text}</p>"
        book.add_item(c)
        chapters.append(c)

    book.toc = tuple(chapters)
    book.spine = ['nav'] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(output_path, book, {})
    return output_path

# --- SERVER ENDPOINTS ---

@app.post("/convert-to-epub/")
async def convert_to_epub(
    files: List[UploadFile] = File(...), 
    title: str = Form("My Scanned Book")
):
    output_epub = "download.epub"
    collected_text = []

    print(f"📥 Creating Book: '{title}' with {len(files)} pages.")

    for i, file in enumerate(files):
        temp_filename = f"temp_{i}_{file.filename}"
        try:
            with open(temp_filename, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            processed_img = preprocess_image(temp_filename)
            custom_config = r'--oem 3 --psm 6'
            raw_text = pytesseract.image_to_string(processed_img, config=custom_config)
            clean_text = clean_text_with_ai(raw_text)
            collected_text.append(clean_text)
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    create_book_from_pages(collected_text, output_epub, title)
    return FileResponse(output_epub, media_type='application/epub+zip', filename=f"{title}.epub")