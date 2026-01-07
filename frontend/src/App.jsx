import { useState } from 'react'
import './App.css'

// CONFIGURATION: Ensure this matches your Render URL exactly
const API_BASE_URL = "https://scan2ebook-ai.onrender.com"; 

function App() {
  const [files, setFiles] = useState([]);
  const [cover, setCover] = useState(null);
  const [coverPreview, setCoverPreview] = useState(null);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("idle"); // idle, processing, success, error
  const [progress, setProgress] = useState(0);
  const [msg, setMsg] = useState("");
  const [dlUrl, setDlUrl] = useState("");

  // Handle Cover Image Selection
  const handleCover = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCover(file);
      setCoverPreview(URL.createObjectURL(file));
    }
  };

  // Handle Page Selection
  const handleFiles = (e) => {
    const selected = Array.from(e.target.files);
    setFiles(selected);
  };

  const handleUpload = async () => {
    if (!files.length) return;

    setStatus("processing");
    setProgress(0);
    setMsg("Initializing upload...");

    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    if (cover) formData.append("cover", cover);
    formData.append("title", title || "My Scanned Book");

    try {
      // 1. Send the files to get a task_id
      const res = await fetch(`${API_BASE_URL}/upload`, { 
        method: 'POST', 
        body: formData 
      });

      if (!res.ok) throw new Error("Server upload failed");

      const { task_id } = await res.json();
      
      // 2. Poll the status endpoint every 3 seconds
      // Using 3 seconds to give the server breathing room for image enhancement
      const interval = setInterval(async () => {
        try {
          const sRes = await fetch(`${API_BASE_URL}/status/${task_id}`);
          if (!sRes.ok) return;

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
            setMsg(data.message || "Conversion failed");
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, 3000); 

    } catch (e) {
      console.error(e);
      setStatus("error");
      setMsg("Connection error. Please try again.");
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>📚 Scan2eBook Pro</h1>
        <p className="subtitle">High-Accuracy AI Conversion</p>

        <div className="input-group">
          <label>Book Title</label>
          <input 
            type="text" 
            placeholder="e.g., Personal Journal" 
            value={title} 
            onChange={e => setTitle(e.target.value)} 
            className="text-input" 
          />
        </div>
        
        <div className="upload-section">
          <label>Step 1: Book Cover (Optional)</label>
          <div className="upload-zone">
            <input type="file" onChange={handleCover} accept="image/*" />
            {coverPreview ? (
              <img src={coverPreview} className="cover-preview" alt="cover" />
            ) : (
              <p>Tap to select cover</p>
            )}
          </div>
        </div>

        <div className="upload-section">
          <label>Step 2: Book Pages</label>
          <div className="upload-zone">
            <input type="file" multiple onChange={handleFiles} accept="image/*" />
            {files.length > 0 ? (
              <p>✅ {files.length} pages selected</p>
            ) : (
              <p>Tap to select pages</p>
            )}
          </div>
        </div>

        {status === "idle" && (
          <button 
            onClick={handleUpload} 
            className="primary-btn" 
            disabled={!files.length}
          >
            🚀 Start Conversion
          </button>
        )}
        
        {status === "processing" && (
          <div className="prog-container">
            <div className="spinner"></div>
            <p className="status-msg">🤖 {msg}</p>
            <div className="bar">
              <div className="fill" style={{width: `${progress}%`}}></div>
            </div>
            <p className="percent">{progress}%</p>
          </div>
        )}

        {status === "success" && (
          <div className="success-area">
            <h2>🎉 Ready!</h2>
            <a href={dlUrl} className="download-btn">Download .EPUB</a>
            <button onClick={() => window.location.reload()} className="reset-btn">New Project</button>
          </div>
        )}

        {status === "error" && (
          <div className="error-area">
            <p>⚠️ {msg}</p>
            <button onClick={() => setStatus("idle")} className="primary-btn">Try Again</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;