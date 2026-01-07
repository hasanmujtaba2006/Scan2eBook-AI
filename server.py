import os
import shutil
import uuid
import zipfile
import uvicorn
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Form
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract

# --- IMPORTS FOR AI ---
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq Client
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

if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

# --- AI HELPER FUNCTION ---
def clean_text_with_ai(raw_text):
    if not raw_text.strip(): return ""
    prompt = f"""
    You are an expert book digitizer. 
    1. Fix OCR errors in the text below.
    2. Format as clean HTML (use <p>, <h2>, <ul>).
    3. No <html>/<body> tags or filler text.
    
    RAW TEXT: {raw_text}
    """
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"<p>{raw_text}</p>"

# --- THE BACKGROUND ENGINE ---
def process_epub_conversion(task_id: str, file_paths: list, book_title: str):
    try:
        tasks[task_id]['status'] = 'processing'
        work_dir = os.path.join(BASE_DIR, "temp", task_id)
        oebps_dir = os.path.join(work_dir, "OEBPS")
        meta_inf_dir = os.path.join(work_dir, "META-INF")
        
        if os.path.exists(work_dir): shutil.rmtree(work_dir)
        os.makedirs(oebps_dir)
        os.makedirs(meta_inf_dir)

        # Create Static EPUB Files
        with open(os.path.join(work_dir, "mimetype"), "w") as f: f.write("application/epub+zip")
        with open(os.path.join(meta_inf_dir, "container.xml"), "w") as f:
             f.write('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        with open(os.path.join(oebps_dir, "styles.css"), "w") as f:
            f.write("body { font-family: serif; margin: 5%; line-height: 1.6; } h1, h2 { text-align: center; }")

        manifest_items = '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
        manifest_items += '<item id="style" href="styles.css" media-type="text/css"/>\n'
        spine_items = ""
        total = len(file_paths)
        
        for i, img_path in enumerate(file_paths):
            index = i + 1
            tasks[task_id]['progress'] = int(10 + ((i / total) * 80))
            tasks[task_id]['message'] = f"Reading Page {index}..."
            
            with Image.open(img_path) as img:
                img = img.convert('RGB')
                if img.width > 1500 or img.height > 1500:
                    img.thumbnail((1500, 1500))
                raw_text = pytesseract.image_to_string(img)
            
            tasks[task_id]['message'] = f"AI Cleaning Page {index}..."
            clean_html_body = clean_text_with_ai(raw_text)
            
            html_content = f"<?xml version='1.0' encoding='utf-8'?><html xmlns='http://www.w3.org/1999/xhtml'><head><link href='styles.css' rel='stylesheet' type='text/css'/></head><body>{clean_html_body}</body></html>"
            
            page_filename = f"page_{index}.html"
            with open(os.path.join(oebps_dir, page_filename), "w", encoding="utf-8") as f:
                f.write(html_content)
                
            manifest_items += f'<item id="page_{index}" href="{page_filename}" media-type="application/xhtml+xml"/>\n'
            spine_items += f'<itemref idref="page_{index}"/>\n'

        tasks[task_id]['message'] = "Packaging EPUB..."
        opf_content = f"""<?xml version="1.0" encoding="utf-8"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{book_title}</dc:title><dc:language>en</dc:language></metadata>
  <manifest>{manifest_items}</manifest>
  <spine toc="ncx">{spine_items}</spine>
</package>"""
        with open(os.path.join(oebps_dir, "content.opf"), "w", encoding="utf-8") as f: f.write(opf_content)

        with open(os.path.join(oebps_dir, "toc.ncx"), "w", encoding="utf-8") as f:
            f.write(f'<?xml version="1.0"?><ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/"><head><meta name="dtb:uid" content="BookId"/></head><docTitle><text>{book_title}</text></docTitle><navMap><navPoint id="p1" playOrder="1"><navLabel><text>Start</text></navLabel><content src="page_1.html"/></navPoint></navMap></ncx>')

        output_filename = f"{task_id}.epub"
        final_path = os.path.join(OUTPUT_DIR, output_filename)
        with zipfile.ZipFile(final_path, 'w') as epub:
            epub.write(os.path.join(work_dir, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
            for root, _, files in os.walk(work_dir):
                for file in files:
                    if file == "mimetype": continue
                    f_path = os.path.join(root, file)
                    epub.write(f_path, os.path.relpath(f_path, work_dir), compress_type=zipfile.ZIP_DEFLATED)

        shutil.rmtree(work_dir)
        tasks[task_id].update({'status': 'completed', 'progress': 100, 'download_url': f"/download/{output_filename}"})

    except Exception as e:
        tasks[task_id].update({'status': 'failed', 'message': str(e)})

# --- API ENDPOINTS ---

@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks, 
    files: list[UploadFile] = File(...), 
    title: str = Form("My Scanned Book") # Now accepts title from React
):
    task_id = str(uuid.uuid4())
    task_upload_dir = os.path.join(UPLOAD_DIR, task_id)
    os.makedirs(task_upload_dir)
    file_paths = []
    
    for file in files:
        file_location = os.path.join(task_upload_dir, file.filename)
        with open(file_location, "wb+") as f: f.write(file.file.read())
        file_paths.append(file_location)
    
    tasks[task_id] = {'status': 'queued', 'progress': 0, 'message': 'Queued...'}
    background_tasks.add_task(process_epub_conversion, task_id, file_paths, title)
    return {"task_id": task_id}

# FORWARDING OLD URL TO NEW ONE (Fixes your 404 errors)
@app.post("/convert-to-epub/")
async def legacy_endpoint():
    return RedirectResponse(url="/upload", status_code=307)

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    return tasks.get(task_id) or HTTPException(status_code=404, detail="Not found")

@app.get("/download/{filename}")
async def download_file(filename: str):
    return FileResponse(os.path.join(OUTPUT_DIR, filename), filename=filename)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)