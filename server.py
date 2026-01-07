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

# --- HIGH-ACCURACY MEMORY-SAFE ENHANCEMENT ---
def enhance_image(img_path):
    img = cv2.imread(img_path)
    if img is None: return Image.open(img_path)
    
    # Resize to a consistent "safe" height for 512MB RAM limits
    h, w = img.shape[:2]
    target_h = 1500
    if h > target_h:
        ratio = target_h / h
        img = cv2.resize(img, (int(w * ratio), target_h), interpolation=cv2.INTER_AREA)
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Simple binary thresholding is faster and uses less RAM than adaptive
    _, thr = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # Explicitly clear raw image from memory
    del img
    gc.collect()
    return Image.fromarray(thr)

# --- DEEP RECONSTRUCTION AI ---
def clean_text_with_ai(raw_text):
    if not raw_text.strip(): return ""
    
    # Stronger prompt to eliminate English hallucinations (e.g., 'Cab', 'SUP')
    prompt = f"""
    You are an expert Urdu and Arabic scholar. The provided text is from a religious 
    book and contains many OCR errors like random English letters and broken words.

    TASKS:
    1. RECONSTRUCT the Urdu and Arabic sentences based on context.
    2. REMOVE all random English characters (like 'OK', 'Cab', 'SUP', 'RU').
    3. FIX word ligatures and spelling errors in Urdu.
    4. Apply <p dir="rtl" style="text-align: right;"> for all paragraphs.
    5. Return ONLY the cleaned HTML body content. Do not translate.

    TEXT: {raw_text}
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except:
        return f"<p dir='rtl'>{raw_text}</p>"

# --- BACKGROUND ENGINE ---
def process_task(task_id: str, paths: list, title: str, cover_p: str = None):
    try:
        tasks[task_id]['status'] = 'processing'
        work = os.path.join(BASE_DIR, "temp", task_id)
        oebps = os.path.join(work, "OEBPS")
        meta = os.path.join(work, "META-INF")
        os.makedirs(oebps); os.makedirs(meta)

        with open(os.path.join(work, "mimetype"), "w") as f: 
            f.write("application/epub+zip")
            
        with open(os.path.join(meta, "container.xml"), "w") as f:
             f.write('<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        
        manifest, spine = "", ""
        if cover_p:
            shutil.copy(cover_p, os.path.join(oebps, "cover.jpg"))
            manifest = '<item id="c-i" href="cover.jpg" media-type="image/jpeg"/><item id="c-p" href="cover.html" media-type="application/xhtml+xml"/>\n'
            spine = '<itemref idref="c-p"/>\n'
            with open(os.path.join(oebps, "cover.html"), "w") as f:
                f.write('<html><body style="margin:0;text-align:center;"><img src="cover.jpg" style="width:100%"/></body></html>')

        manifest += '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        
        for i, p in enumerate(paths):
            tasks[task_id]['progress'] = int(10 + (i/len(paths)*80))
            tasks[task_id]['message'] = f"Analyzing Script Page {i+1}..."
            
            enhanced = enhance_image(p)
            
            # ACCURACY FIX: Restricted to urd+ara ONLY to stop English hallucinations
            raw = pytesseract.image_to_string(enhanced, lang='urd+ara', config='--oem 3 --psm 3')
            
            # Free memory immediately
            enhanced.close()
            
            clean = clean_text_with_ai(raw)
            p_name = f"p{i}.html"
            with open(os.path.join(oebps, p_name), "w", encoding="utf-8") as f:
                f.write(f"<html><body style='direction:rtl;'>{clean}</body></html>")
            
            manifest += f'<item id="p{i}" href="{p_name}" media-type="application/xhtml+xml"/>\n'
            spine += f'<itemref idref="p{i}"/>\n'
            gc.collect()

        with open(os.path.join(oebps, "content.opf"), "w") as f:
            f.write(f'<package xmlns="http://www.idpf.org/2007/opf" version="2.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{title}</dc:title><dc:language>ur</dc:language></metadata><manifest>{manifest}</manifest><spine toc="ncx">{spine}</spine></package>')
        
        with open(os.path.join(oebps, "toc.ncx"), "w") as f:
            f.write('<?xml version="1.0"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><navMap><navPoint id="n1"><navLabel><text>Start</text></navLabel><content src="p0.html"/></navPoint></navMap></ncx>')

        # FINAL PACKAGING FIX: Uncompressed mimetype
        out_fn = f"{task_id}.epub"
        final_p = os.path.join(OUTPUT_DIR, out_fn)
        with zipfile.ZipFile(final_p, 'w') as z:
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

@app.post("/upload")
async def upload(bg: BackgroundTasks, files: list[UploadFile] = File(...), cover: UploadFile = File(None), title: str = Form("Urdu eBook")):
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
    tasks[tid] = {'status': 'queued', 'progress': 0}
    bg.add_task(process_task, tid, paths, title, cp)
    return {"task_id": tid}

@app.get("/status/{tid}")
async def status(tid: str): return tasks.get(tid)

@app.get("/download/{fn}")
async def download(fn: str): return FileResponse(os.path.join(OUTPUT_DIR, fn), filename=fn, media_type='application/epub+zip')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)