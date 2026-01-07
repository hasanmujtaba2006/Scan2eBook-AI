import { useState } from 'react'
import './App.css'

const API_BASE_URL = "https://scan2ebook-ai.onrender.com"; 

function App() {
  const [files, setFiles] = useState([]);
  const [cover, setCover] = useState(null);
  const [coverPreview, setCoverPreview] = useState(null);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [msg, setMsg] = useState("");
  const [dlUrl, setDlUrl] = useState("");
  
  // Preview States
  const [editableContent, setEditableContent] = useState("");
  const [isPreviewing, setIsPreviewing] = useState(false);

  const handleCover = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCover(file);
      setCoverPreview(URL.createObjectURL(file));
    }
  };

  const handleGetPreview = async () => {
    if (!files.length) return;
    setStatus("processing");
    setMsg("Analyzing first page for preview...");
    
    const formData = new FormData();
    formData.append("file", files[0]);

    try {
      const res = await fetch(`${API_BASE_URL}/preview-page`, { method: 'POST', body: formData });
      const data = await res.json();
      setEditableContent(data.html);
      setIsPreviewing(true);
      setStatus("idle");
    } catch (e) {
      setStatus("error");
      setMsg("Preview failed.");
    }
  };

  const handleUpload = async () => {
    if (!files.length) return;
    setStatus("processing");
    setMsg("Starting full conversion...");

    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    if (cover) formData.append("cover", cover);
    formData.append("title", title || "My Urdu eBook");

    try {
      const res = await fetch(`${API_BASE_URL}/upload`, { method: 'POST', body: formData });
      const { task_id } = await res.json();
      
      const interval = setInterval(async () => {
        const sRes = await fetch(`${API_BASE_URL}/status/${task_id}`);
        const data = await sRes.json();
        setProgress(data.progress);
        setMsg(data.message);

        if (data.status === 'completed') {
          clearInterval(interval);
          setDlUrl(`${API_BASE_URL}${data.download_url}`);
          setStatus("success");
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setStatus("error");
        }
      }, 3000);
    } catch (e) { setStatus("error"); }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>📚 Scan2eBook Pro</h1>
        <input type="text" placeholder="Book Title" value={title} onChange={e => setTitle(e.target.value)} className="text-input" />
        
        <div className="upload-section">
          <label>Book Cover:</label>
          <input type="file" onChange={handleCover} accept="image/*" />
          {coverPreview && <img src={coverPreview} className="cover-preview" alt="cover" />}
        </div>

        <div className="upload-section">
          <label>Select Pages:</label>
          <input type="file" multiple onChange={e => setFiles(Array.from(e.target.files))} accept="image/*" />
          {files.length > 0 && <p className="page-count">✅ {files.length} pages ready</p>}
        </div>

        {isPreviewing && (
          <div className="preview-container">
            <h3>📝 Quick Preview (Page 1)</h3>
            <textarea 
              className="urdu-editor" 
              dir="rtl" 
              value={editableContent} 
              onChange={(e) => setEditableContent(e.target.value)}
            />
          </div>
        )}

        <div className="action-buttons">
          {status === "idle" && files.length > 0 && !isPreviewing && (
            <button onClick={handleGetPreview} className="secondary-btn">🔍 Preview Text</button>
          )}
          {status === "idle" && files.length > 0 && (
            <button onClick={handleUpload} className="primary-btn">🚀 Create Full eBook</button>
          )}
        </div>

        {status === "processing" && (
          <div className="prog-container">
            <div className="spinner"></div>
            <p>{msg}</p>
            <div className="bar"><div className="fill" style={{width: `${progress}%`}}></div></div>
          </div>
        )}

        {status === "success" && (
          <div className="success-box">
            <a href={dlUrl} className="download-btn">Download .EPUB ⬇️</a>
            <button onClick={() => window.location.reload()} className="reset-btn">Start New</button>
          </div>
        )}
      </div>
    </div>
  );
}
export default App;