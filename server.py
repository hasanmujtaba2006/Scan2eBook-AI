import os, shutil, uuid, zipfile, uvicorn, cv2, gc
import numpy as np
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

tasks = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
for d in [UPLOAD_DIR, OUTPUT_DIR]: 
    if not os.path.exists(d): os.makedirs(d)

def enhance_image_memory_safe(img_path):
    img = cv2.imread(img_path)
    if img is None: return Image.open(img_path)
    
    # Memory Guard: Avoid resizing large images which causes the 512MB crash
    h, w = img.shape[:2]
    if w < 1000:
        img = cv2.resize(img, None, fx=1.1, fy=1.1, interpolation=cv2.INTER_LINEAR)
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Clear raw image from memory immediately
    del img
    gc.collect()
    return Image.fromarray(thr)

def clean_text_with_ai(raw_text):
    if not raw_text.strip(): return ""
    prompt = f"Fix OCR errors. Wrap Urdu/Arabic in <p dir='rtl'>, English/Hindi in <p dir='ltr'>. Return ONLY HTML. TEXT: {raw_text}"
    try:
        res = client.chat.completions.create(model="llama3-8b-8192", messages=[{"role": "user", "content": prompt}], temperature=0)
        return res.choices[0].message.content
    except: return f"<p>{raw_text}</p>"

def process_task(task_id, paths, title, cover_p):
    try:
        tasks[task_id]['status'] = 'processing'
        work = os.path.join(BASE_DIR, "temp", task_id)
        oebps = os.path.join(work, "OEBPS"); meta = os.path.join(work, "META-INF")
        os.makedirs(oebps); os.makedirs(meta)

        with open(os.path.join(work, "mimetype"), "w") as f: f.write("application/epub+zip")
        
        manifest = '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="css" href="styles.css" media-type="text/css"/>'
        spine = ""
        
        if cover_p:
            shutil.copy(cover_p, os.path.join(oebps, "cover.jpg"))
            manifest += '<item id="c-i" href="cover.jpg" media-type="image/jpeg"/><item id="c-p" href="cover.html" media-type="application/xhtml+xml"/>'
            spine = '<itemref idref="c-p"/>'
            with open(os.path.join(oebps, "cover.html"), "w") as f: f.write('<html><body><img src="cover.jpg" style="width:100%"/></body></html>')

        for i, p in enumerate(paths):
            tasks[task_id]['progress'] = int(10 + (i/len(paths)*80))
            tasks[task_id]['message'] = f"Processing Page {i+1}..."
            
            enhanced = enhance_image_memory_safe(p)
            raw = pytesseract.image_to_string(enhanced, lang='eng+urd+hin+ara', config='--oem 3 --psm 3')
            
            # Explicitly close image to free RAM
            enhanced.close()
            
            clean = clean_text_with_ai(raw)
            p_name = f"p{i}.html"
            with open(os.path.join(oebps, p_name), "w", encoding="utf-8") as f:
                f.write(f"<html><body>{clean}</body></html>")
            
            manifest += f'<item id="p{i}" href="{p_name}" media-type="application/xhtml+xml"/>'
            spine += f'<itemref idref="p{i}"/>'
            gc.collect() # Force garbage collection between pages

        with open(os.path.join(oebps, "styles.css"), "w") as f: f.write("body { font-family: sans-serif; margin: 5%; }")
        with open(os.path.join(oebps, "content.opf"), "w") as f:
            f.write(f'<package version="2.0" xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title><dc:language>en</dc:language></metadata><manifest>{manifest}</manifest><spine toc="ncx">{spine}</spine></package>')
        with open(os.path.join(oebps, "toc.ncx"), "w") as f:
            f.write('<?xml version="1.0"?><ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/"><navMap><navPoint id="n1"><navLabel><text>Start</text></navLabel><content src="p0.html"/></navPoint></navMap></ncx>')

        out_fn = f"{task_id}.epub"
        final_p = os.path.join(OUTPUT_DIR, out_fn)
        with zipfile.ZipFile(final_p, 'w') as z:
            z.write(os.path.join(work, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
            for r, _, fls in os.walk(work):
                for fl in fls:
                    if fl == "mimetype": continue
                    z.write(os.path.join(r, fl), os.path.relpath(os.path.join(r, fl), work), compress_type=zipfile.ZIP_DEFLATED)
        
        shutil.rmtree(work)
        tasks[task_id].update({'status': 'completed', 'progress': 100, 'download_url': f"/download/{out_fn}"})
    except Exception as e:
        tasks[task_id].update({'status': 'failed', 'message': str(e)})

@app.post("/upload")
async def upload(bg: BackgroundTasks, files: list[UploadFile] = File(...), cover: UploadFile = File(None), title: str = Form("Book")):
    tid = str(uuid.uuid4()); tdir = os.path.join(UPLOAD_DIR, tid); os.makedirs(tdir)
    paths = []
    for f in files:
        p = os.path.join(tdir, f.filename);
        with open(p, "wb") as b: b.write(f.file.read())
        paths.append(p)
    cp = None
    if cover:
        cp = os.path.join(tdir, "c.jpg")
        with open(cp, "wb") as b: b.write(cover.file.read())
    tasks[tid] = {'status': 'queued', 'progress': 0}
    bg.add_task(process_task, tid, paths, title, cp)
    return {"task_id": tid}

@app.get("/status/{tid}")
async def status(tid: str): return tasks.get(tid)

@app.get("/download/{fn}")
async def dl(fn: str): return FileResponse(os.path.join(OUTPUT_DIR, fn), filename=fn, media_type='application/epub+zip')