import os
import shutil
import uuid
import zipfile
import uvicorn
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Form
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract

# --- AI & ENV SETUP ---
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

for d in [UPLOAD_DIR, OUTPUT_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- NEW: IMAGE ENHANCEMENT FUNCTION ---
def enhance_image_for_ocr(img_path):
    """
    Uses Computer Vision to remove shadows and make text pop.
    """
    # Read image
    image = cv2.imread(img_path)
    if image is None:
        return Image.open(img_path) # Fallback to PIL if OpenCV fails

    # 1. Convert to Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. Rescale (Zoom in 2x) for better character recognition
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # 3. Adaptive Thresholding (Removes shadows and page curves)
    processed_img = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Convert back to PIL format for Tesseract
    return Image.fromarray(processed_img)

# --- UPDATED: HIGH-ACCURACY AI PROOFREADER ---
def clean_text_with_ai(raw_text):
    if not raw_text.strip(): return ""
    
    prompt = f"""
    You are a professional book proofreader. Restore this messy OCR text to 100% accuracy.
    
    TASKS:
    1. Fix character swaps (e.g., 'cl' -> 'd', 'rn' -> 'm').
    2. Rejoin words split by line breaks.
    3. Remove hallucinated noise characters like |, _, or random dots.
    4. Apply logical paragraph breaks (<p>) and chapter headings (<h2>).
    5. Maintain original tone exactly—do not rewrite.
    
    OUTPUT: Return ONLY HTML body content.
    
    TEXT:
    {raw_text}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192", # Switched to 70B for much higher intelligence
            messages=[{"role": "user", "content": prompt}],
            temperature=0 # Zero temperature ensures accuracy over creativity
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"AI Error: {e}")
        return f"<p>{raw_text}</p>"

# --- THE BACKGROUND ENGINE ---
def process_epub_conversion(task_id: str, file_paths: list, book_title: str, cover_path: str = None):
    try:
        tasks[task_id]['status'] = 'processing'
        work_dir = os.path.join(BASE_DIR, "temp", task_id)
        oebps_dir = os.path.join(work_dir, "OEBPS")
        meta_inf_dir = os.path.join(work_dir, "META-INF")
        os.makedirs(oebps_dir); os.makedirs(meta_inf_dir)

        # 1. Structure Setup
        with open(os.path.join(work_dir, "mimetype"), "w") as f: f.write("application/epub+zip")
        with open(os.path.join(meta_inf_dir, "container.xml"), "w") as f:
             f.write('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        
        # 2. Handle Cover
        manifest_cover, spine_cover, meta_cover = "", "", ""
        if cover_path:
            shutil.copy(cover_path, os.path.join(oebps_dir, "cover.jpg"))
            manifest_cover = '<item id="cover-img" href="cover.jpg" media-type="image/jpeg"/>\n<item id="cover-page" href="cover.html" media-type="application/xhtml+xml"/>\n'
            spine_cover = '<itemref idref="cover-page"/>\n'
            meta_cover = '<meta name="cover" content="cover-img"/>'
            with open(os.path.join(oebps_dir, "cover.html"), "w") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Cover</title></head><body style="margin:0;text-align:center;"><img src="cover.jpg" style="height:100%;max-width:100%;"/></body></html>')

        # 3. Enhanced Processing Loop
        manifest_items = manifest_cover + '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="css" href="styles.css" media-type="text/css"/>\n'
        spine_items = spine_cover
        
        for i, img_path in enumerate(file_paths):
            index = i + 1
            tasks[task_id]['progress'] = int(10 + ((i / len(file_paths)) * 80))
            
            # A. Image Enhancement
            tasks[task_id]['message'] = f"Enhancing Image {index}..."
            enhanced_img = enhance_image_for_ocr(img_path)
            
            # B. Optimized OCR
            tasks[task_id]['message'] = f"Reading Text {index}..."
            custom_config = r'--oem 3 --psm 3'
            text = pytesseract.image_to_string(enhanced_img, config=custom_config)
            
            # C. Deep AI Proofread
            tasks[task_id]['message'] = f"AI Deep Cleaning Page {index}..."
            html_body = clean_text_with_ai(text)
            
            page_name = f"page_{index}.html"
            with open(os.path.join(oebps_dir, page_name), "w", encoding="utf-8") as f:
                f.write(f"<?xml version='1.0' encoding='utf-8'?><html xmlns='http://www.w3.org/1999/xhtml'><head><link href='styles.css' rel='stylesheet' type='text/css'/></head><body>{html_body}</body></html>")
            
            manifest_items += f'<item id="p{index}" href="{page_name}" media-type="application/xhtml+xml"/>\n'
            spine_items += f'<itemref idref="p{index}"/>\n'

        # 4. Packaging
        with open(os.path.join(oebps_dir, "styles.css"), "w") as f: f.write("body { font-family: serif; margin: 5%; line-height: 1.6; }")
        with open(os.path.join(oebps_dir, "content.opf"), "w") as f:
            f.write(f'<?xml version="1.0" encoding="utf-8"?><package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{book_title}</dc:title><dc:language>en</dc:language>{meta_cover}</metadata><manifest>{manifest_items}</manifest><spine toc="ncx">{spine_items}</spine></package>')
        with open(os.path.join(oebps_dir, "toc.ncx"), "w") as f:
            f.write(f'<?xml version="1.0"?><ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint id="n1" playOrder="1"><navLabel><text>Start</text></navLabel><content src="page_1.html"/></navPoint></navMap></ncx>')

        output_fn = f"{task_id}.epub"
        final_p = os.path.join(OUTPUT_DIR, output_fn)
        with zipfile.ZipFile(final_p, 'w') as epub:
            epub.write(os.path.join(work_dir, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
            for r, _, f_list in os.walk(work_dir):
                for f in f_list:
                    if f == "mimetype": continue
                    abs_p = os.path.join(r, f)
                    epub.write(abs_p, os.path.relpath(abs_p, work_dir), compress_type=zipfile.ZIP_DEFLATED)
        
        shutil.rmtree(work_dir)
        tasks[task_id].update({'status': 'completed', 'progress': 100, 'download_url': f"/download/{output_fn}"})
    except Exception as e:
        tasks[task_id].update({'status': 'failed', 'message': str(e)})

# --- ENDPOINTS ---
@app.post("/upload")
async def upload(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...), cover: UploadFile = File(None), title: str = Form("My Book")):
    t_id = str(uuid.uuid4())
    t_dir = os.path.join(UPLOAD_DIR, t_id); os.makedirs(t_dir)
    paths = []
    for f in files:
        p = os.path.join(t_dir, f.filename)
        with open(p, "wb") as buf: buf.write(f.file.read())
        paths.append(p)
    
    c_path = None
    if cover:
        c_path = os.path.join(t_dir, "cover_input.jpg")
        with open(c_path, "wb") as buf: buf.write(cover.file.read())
    
    tasks[t_id] = {'status': 'queued', 'progress': 0, 'message': 'Queued...'}
    background_tasks.add_task(process_epub_conversion, t_id, paths, title, c_path)
    return {"task_id": t_id}

@app.get("/status/{task_id}")
async def status(task_id: str): return tasks.get(task_id)

@app.get("/download/{fn}")
async def download(fn: str): return FileResponse(os.path.join(OUTPUT_DIR, fn), filename=fn, media_type='application/epub+zip')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)