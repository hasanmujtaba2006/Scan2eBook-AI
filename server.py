import os
import shutil
import uuid
import zipfile
import uvicorn
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract
from groq import Groq
from dotenv import load_dotenv

# --- INITIALIZATION ---
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

# Enable CORS for frontend communication
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

# --- MEMORY-SAFE IMAGE ENHANCEMENT ---
def enhance_image(img_path):
    img = cv2.imread(img_path)
    if img is None: return Image.open(img_path)
    
    # Check size: only resize if very small to prevent Memory Limit crashes
    h, w = img.shape[:2]
    if w < 1200:
        img = cv2.resize(img, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_LINEAR)
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Otsu's Thresholding for high-contrast B&W (ideal for OCR)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thr)

# --- AI DIRECTION-AWARE PROOFREADER ---
def clean_text_with_ai(raw_text):
    if not raw_text.strip(): return ""
    
    # Detects script direction and fixes OCR typos
    prompt = f"""
    Act as a professional book editor. Fix OCR errors in this text.
    SCRIPTS: English, Urdu, Hindi, or Arabic.
    
    TASKS:
    1. Detect script direction (RTL for Urdu/Arabic, LTR for English/Hindi).
    2. Wrap Urdu/Arabic in <p dir="rtl" style="text-align:right;">.
    3. Wrap English/Hindi in <p dir="ltr" style="text-align:left;">.
    4. Maintain original language exactly—DO NOT TRANSLATE.
    
    RETURN ONLY HTML BODY CONTENT.
    TEXT: {raw_text}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return completion.choices[0].message.content
    except:
        return f"<p>{raw_text}</p>"

# --- THE BACKGROUND ENGINE ---
def process_task(task_id: str, paths: list, title: str, cover_p: str = None):
    try:
        tasks[task_id]['status'] = 'processing'
        work = os.path.join(BASE_DIR, "temp", task_id)
        oebps = os.path.join(work, "OEBPS")
        meta = os.path.join(work, "META-INF")
        os.makedirs(oebps); os.makedirs(meta)

        # 1. Mimetype - MUST BE UNCOMPRESSED
        with open(os.path.join(work, "mimetype"), "w") as f: 
            f.write("application/epub+zip")
            
        with open(os.path.join(meta, "container.xml"), "w") as f:
             f.write('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        
        # 2. Cover Logic
        manifest, spine = "", ""
        if cover_p:
            shutil.copy(cover_p, os.path.join(oebps, "cover.jpg"))
            manifest = '<item id="c-i" href="cover.jpg" media-type="image/jpeg"/><item id="c-p" href="cover.html" media-type="application/xhtml+xml"/>\n'
            spine = '<itemref idref="c-p"/>\n'
            with open(os.path.join(oebps, "cover.html"), "w") as f:
                f.write('<html><body style="margin:0;text-align:center;"><img src="cover.jpg" style="width:100%"/></body></html>')

        manifest += '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="css" href="styles.css" media-type="text/css"/>\n'
        
        # 3. Multilingual OCR Loop
        for i, p in enumerate(paths):
            tasks[task_id]['progress'] = int(10 + (i/len(paths)*80))
            tasks[task_id]['message'] = f"Reading Page {i+1}..."
            
            enhanced = enhance_image(p)
            # lang='eng+urd+hin+ara' enables multi-script detection
            raw = pytesseract.image_to_string(enhanced, lang='eng+urd+hin+ara', config='--oem 3 --psm 3')
            clean = clean_text_with_ai(raw)
            
            p_name = f"p{i}.html"
            with open(os.path.join(oebps, p_name), "w", encoding="utf-8") as f:
                f.write(f"<html><head><link href='styles.css' rel='stylesheet'/></head><body>{clean}</body></html>")
            
            manifest += f'<item id="p{i}" href="{p_name}" media-type="application/xhtml+xml"/>\n'
            spine += f'<itemref idref="p{i}"/>\n'

        # 4. Packaging - OPF, NCX, CSS
        with open(os.path.join(oebps, "styles.css"), "w") as f:
            f.write("body { font-family: sans-serif; margin: 5%; line-height: 1.6; } p { margin: 1em 0; }")
        
        with open(os.path.join(oebps, "content.opf"), "w") as f:
            f.write(f'<package version="2.0" xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title><dc:language>en</dc:language></metadata><manifest>{manifest}</manifest><spine toc="ncx">{spine}</spine></package>')
        
        with open(os.path.join(oebps, "toc.ncx"), "w") as f:
            f.write('<?xml version="1.0"?><ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint id="n1"><navLabel><text>Start</text></navLabel><content src="p0.html"/></navPoint></navMap></ncx>')

        # 5. CORRECT EPUB ZIP PACKAGING
        out_fn = f"{task_id}.epub"
        final_p = os.path.join(OUTPUT_DIR, out_fn)
        with zipfile.ZipFile(final_p, 'w') as z:
            # First file MUST be mimetype and MUST be uncompressed
            z.write(os.path.join(work, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
            for r, _, fls in os.walk(work):
                for fl in fls:
                    if fl == "mimetype": continue
                    abs_p = os.path.join(r, fl)
                    z.write(abs_p, os.path.relpath(abs_p, work), compress_type=zipfile.ZIP_DEFLATED)
        
        shutil.rmtree(work)
        tasks[task_id].update({'status': 'completed', 'progress': 100, 'download_url': f"/download/{out_fn}"})
    except Exception as e:
        tasks[task_id].update({'status': 'failed', 'message': str(e)})

# --- ENDPOINTS ---
@app.post("/upload")
async def upload(bg: BackgroundTasks, files: list[UploadFile] = File(...), cover: UploadFile = File(None), title: str = Form("New eBook")):
    tid = str(uuid.uuid4()); tdir = os.path.join(UPLOAD_DIR, tid); os.makedirs(tdir)
    paths = []
    for f in files:
        p = os.path.join(tdir, f.filename)
        with open(p, "wb") as b: b.write(f.file.read())
        paths.append(p)
    cp = None
    if cover:
        cp = os.path.join(tdir, "cover.jpg")
        with open(cp, "wb") as b: b.write(cover.file.read())
    tasks[tid] = {'status': 'queued', 'progress': 0, 'message': 'Queued...'}
    bg.add_task(process_task, tid, paths, title, cp)
    return {"task_id": tid}

@app.get("/status/{tid}")
async def status(tid: str): return tasks.get(tid)

@app.get("/download/{fn}")
async def download(fn: str): return FileResponse(os.path.join(OUTPUT_DIR, fn), filename=fn, media_type='application/epub+zip')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)