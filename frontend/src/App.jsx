import { useState } from 'react'
import './App.css'

const API_BASE_URL = "https://scan2ebook-ai.onrender.com"; 

function App() {
  const [files, setFiles] = useState([]);
  const [cover, setCover] = useState(null);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("idle"); // idle, processing, success, error
  const [progress, setProgress] = useState(0);
  const [msg, setMsg] = useState("");
  const [summary, setSummary] = useState("");
  const [dlUrl, setDlUrl] = useState("");
  const [editableContent, setEditableContent] = useState("");
  const [isPreviewing, setIsPreviewing] = useState(false);

  // Remove a specific page before uploading
  const removeFile = (index) => {
    const updatedFiles = files.filter((_, i) => i !== index);
    setFiles(updatedFiles);
  };

  const handleGetPreview = async () => {
    if (!files.length) return;
    setStatus("processing");
    setMsg("Analyzing first page for Urdu script...");
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
      setMsg("Preview failed. Check connection.");
    }
  };

  const handleUpload = async () => {
    if (!files.length) return;
    setStatus("processing");
    setMsg("Starting high-accuracy conversion...");

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
        setMsg(data.message || "Processing...");

        if (data.status === 'completed') {
          clearInterval(interval);
          setDlUrl(`${API_BASE_URL}${data.download_url}`);
          setSummary(data.summary);
          setStatus("success");
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setStatus("error");
          setMsg(data.message);
        }
      }, 3000);
    } catch (e) { 
      setStatus("error");
      setMsg("Upload failed.");
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>📚 Scan2eBook AI</h1>
        
        <div className="input-group">
          <input 
            type="text" 
            placeholder="Book Title (Urdu/English)" 
            value={title} 
            onChange={e => setTitle(e.target.value)} 
            className="text-input" 
          />
        </div>
        
        <div className="upload-section">
          <label>Step 1: Select Book Pages</label>
          <input 
            type="file" 
            multiple 
            onChange={e => setFiles([...files, ...Array.from(e.target.files)])} 
            accept="image/*" 
            className="file-input" 
          />
          
          <div className="file-preview-grid">
            {files.map((file, index) => (
              <div key={index} className="file-chip">
                <span className="file-name">{file.name}</span>
                <button onClick={() => removeFile(index)} className="delete-btn">×</button>
              </div>
            ))}
          </div>
        </div>

        {isPreviewing && (
          <div className="preview-mode">
            <h3>📝 Page 1 Editor (Review Script)</h3>
            <textarea 
              dir="rtl" 
              className="urdu-editor" 
              value={editableContent} 
              onChange={e => setEditableContent(e.target.value)} 
            />
            <p className="hint">Edit the text above if the AI missed any ligatures.</p>
          </div>
        )}

        {status === "idle" && files.length > 0 && (
          <div className="btn-group">
            {!isPreviewing && (
              <button onClick={handleGetPreview} className="sec-btn">🔍 Preview Urdu Text</button>
            )}
            <button onClick={handleUpload} className="pri-btn">🚀 Generate Full eBook</button>
          </div>
        )}

        {status === "processing" && (
          <div className="loader">
            <div className="spinner"></div>
            <p>{msg}</p>
            <div className="bar"><div className="fill" style={{width: `${progress}%`}}></div></div>
            <p className="percent-text">{progress}%</p>
          </div>
        )}

        {status === "success" && (
          <div className="success">
            <div className="summary-box" dir="rtl">
              <strong>✨ AI Book Summary:</strong>
              <p>{summary}</p>
            </div>
            <a href={dlUrl} className="dl-btn">Download .EPUB ⬇️</a>
            <button onClick={() => window.location.reload()} className="reset-btn">Convert Another Book</button>
          </div>
        )}

        {status === "error" && (
          <div className="error-box">
            <p>⚠️ {msg}</p>
            <button onClick={() => setStatus("idle")} className="pri-btn">Try Again</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;