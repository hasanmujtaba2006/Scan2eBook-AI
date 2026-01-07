import os
import shutil
import uuid
import zipfile
import uvicorn
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import pytesseract

# --- CONFIGURATION ---
# UPDATE THIS PATH if on Windows. If using Docker/Linux, you might not need it.
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = FastAPI()

# Enable CORS for your React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Dictionary to store task status
tasks = {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

# --- THE BACKGROUND ENGINE ---
def process_epub_conversion(task_id: str, file_paths: list):
    """
    This runs in the background. It does not block the server.
    """
    try:
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 5
        
        # 1. Setup Temp Directory
        work_dir = os.path.join(BASE_DIR, "temp", task_id)
        oebps_dir = os.path.join(work_dir, "OEBPS")
        meta_inf_dir = os.path.join(work_dir, "META-INF")
        
        if os.path.exists(work_dir): shutil.rmtree(work_dir)
        os.makedirs(oebps_dir)
        os.makedirs(meta_inf_dir)

        # 2. Create Static EPUB Files
        with open(os.path.join(work_dir, "mimetype"), "w") as f: f.write("application/epub+zip")
        with open(os.path.join(meta_inf_dir, "container.xml"), "w") as f:
             f.write('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        with open(os.path.join(oebps_dir, "styles.css"), "w") as f:
            f.write("body { font-family: serif; margin: 5%; } img { max-width: 100%; }")

        # 3. Process Images Loop
        manifest_items = '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
        manifest_items += '<item id="style" href="styles.css" media-type="text/css"/>\n'
        spine_items = ""
        
        total = len(file_paths)
        
        for i, img_path in enumerate(file_paths):
            index = i + 1
            
            # UPDATE PROGRESS for React
            percent = int(10 + ((i / total) * 80))
            tasks[task_id]['progress'] = percent
            tasks[task_id]['message'] = f"Converting Page {index} of {total}..."
            
            # A. OCR (Tesseract)
            # Future: Use 'groq' here to clean up raw_text if needed
            raw_text = pytesseract.image_to_string(Image.open(img_path))
            
            # B. Generate HTML
            html_content = f"""<?xml version='1.0' encoding='utf-8'?>
            <html xmlns="http://www.w3.org/1999/xhtml">
            <head><title>Page {index}</title><link href="styles.css" rel="stylesheet" type="text/css"/></head>
            <body><h3>Page {index}</h3><p>{raw_text}</p></body></html>"""
            
            page_filename = f"page_{index}.html"
            with open(os.path.join(oebps_dir, page_filename), "w", encoding="utf-8") as f:
                f.write(html_content)
                
            manifest_items += f'<item id="page_{index}" href="{page_filename}" media-type="application/xhtml+xml"/>\n'
            spine_items += f'<itemref idref="page_{index}"/>\n'

        # 4. Finalize & Zip
        tasks[task_id]['message'] = "Packaging EPUB..."
        
        opf_content = f"""<?xml version="1.0" encoding="utf-8"?>
<package version="2.0" unique-identifier="BookId" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Scanned Book</dc:title><dc:language>en</dc:language></metadata>
  <manifest>{manifest_items}</manifest>
  <spine toc="ncx">{spine_items}</spine>
</package>"""
        with open(os.path.join(oebps_dir, "content.opf"), "w", encoding="utf-8") as f: f.write(opf_content)

        # Basic NCX (Required for some readers)
        with open(os.path.join(oebps_dir, "toc.ncx"), "w", encoding="utf-8") as f:
            f.write(f'<?xml version="1.0"?><ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/"><head><meta name="dtb:uid" content="BookId"/></head><docTitle><text>Book</text></docTitle><navMap><navPoint id="navPoint-1" playOrder="1"><navLabel><text>Start</text></navLabel><content src="page_1.html"/></navPoint></navMap></ncx>')

        output_filename = f"{task_id}.epub"
        final_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with zipfile.ZipFile(final_path, 'w') as epub:
            epub.write(os.path.join(work_dir, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    if file == "mimetype": continue
                    f_path = os.path.join(root, file)
                    arcname = os.path.relpath(f_path, work_dir)
                    epub.write(f_path, arcname, compress_type=zipfile.ZIP_DEFLATED)

        # Cleanup
        shutil.rmtree(work_dir)
        
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['download_url'] = f"/download/{output_filename}"

    except Exception as e:
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['message'] = str(e)
        print(f"Error: {e}")

# --- API ENDPOINTS ---

@app.post("/upload")
async def upload_files(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)):
    task_id = str(uuid.uuid4())
    
    # Save Uploads Temporarily
    task_upload_dir = os.path.join(UPLOAD_DIR, task_id)
    os.makedirs(task_upload_dir)
    file_paths = []
    
    for file in files:
        file_location = os.path.join(task_upload_dir, file.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())
        file_paths.append(file_location)
    
    # Initialize Task
    tasks[task_id] = {'status': 'queued', 'progress': 0, 'message': 'Queued...'}
    
    # Hand off to Background Task (This makes the UI responsive immediately)
    background_tasks.add_task(process_epub_conversion, task_id, file_paths)
    
    return {"task_id": task_id}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return {"error": "File not found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)