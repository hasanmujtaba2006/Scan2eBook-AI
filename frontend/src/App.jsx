import { useState } from 'react'
import './App.css'

const API_BASE_URL = "https://scan2ebook-ai.onrender.com"; 

function App() {
  const [files, setFiles] = useState([]);
  const [cover, setCover] = useState(null);
  const [title, setTitle] = useState("");
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [msg, setMsg] = useState("");
  const [summary, setSummary] = useState("");
  const [dlUrl, setDlUrl] = useState("");
  const [editableContent, setEditableContent] = useState("");
  const [isPreviewing, setIsPreviewing] = useState(false);

  const moveFile = (index, direction) => {
    const updatedFiles = [...files];
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= files.length) return;
    [updatedFiles[index], updatedFiles[newIndex]] = [updatedFiles[newIndex], updatedFiles[index]];
    setFiles(updatedFiles);
  };

  const removeFile = (index) => setFiles(files.filter((_, i) => i !== index));

  const handleGetPreview = async () => {
    if (!files.length) return;
    setStatus("processing");
    setMsg("Reading Page 1 script...");
    const formData = new FormData();
    formData.append("file", files[0]);
    try {
      const res = await fetch(`${API_BASE_URL}/preview-page`, { method: 'POST', body: formData });
      const data = await res.json();
      setEditableContent(data.html);
      setIsPreviewing(true);
      setStatus("idle");
    } catch (e) { setStatus("error"); setMsg("Preview failed."); }
  };

  const handleUpload = async () => {
    setStatus("processing");
    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    if (cover) formData.append("cover", cover);
    formData.append("title", title || "My Urdu eBook");
    formData.append("skip_summary", isBatchMode);

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
          setSummary(data.summary);
          setStatus("success");
        }
      }, 3000);
    } catch (e) { setStatus("error"); }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>📚 Scan2eBook AI</h1>
        <input type="text" placeholder="Book Title" value={title} onChange={e => setTitle(e.target.value)} className="text-input" />
        <div className="upload-section">
          <label>Add Pages:</label>
          <input type="file" multiple onChange={e => setFiles([...files, ...Array.from(e.target.files)])} accept="image/*" className="file-input" />
          <div className="file-preview-grid">
            {files.map((file, index) => (
              <div key={index} className="file-chip">
                <div className="reorder-btns">
                  <button onClick={() => moveFile(index, 'up')} disabled={index === 0}>▲</button>
                  <button onClick={() => moveFile(index, 'down')} disabled={index === files.length - 1}>▼</button>
                </div>
                <span className="file-name">{file.name}</span>
                <button onClick={() => removeFile(index)} className="delete-btn">×</button>
              </div>
            ))}
          </div>
        </div>

        <div className="toggle-container">
          <label className="switch">
            <input type="checkbox" checked={isBatchMode} onChange={(e) => setIsBatchMode(e.target.checked)} />
            <span className="slider round"></span>
          </label>
          <span className="toggle-label">⚡ Batch Mode (Faster)</span>
        </div>

        {isPreviewing && (
          <div className="preview-mode">
            <textarea dir="rtl" className="urdu-editor" value={editableContent} onChange={e => setEditableContent(e.target.value)} />
          </div>
        )}

        {status === "idle" && files.length > 0 && (
          <div className="btn-group">
            <button onClick={handleGetPreview} className="sec-btn">🔍 Preview Text</button>
            <button onClick={handleUpload} className="pri-btn">🚀 Start Conversion</button>
          </div>
        )}

        {status === "processing" && (
          <div className="loader">
            <div className="spinner"></div>
            <p>{msg}</p>
            <div className="bar"><div className="fill" style={{width: `${progress}%`}}></div></div>
          </div>
        )}

        {status === "success" && (
          <div className="success">
            <div className="summary-box" dir="rtl"><strong>Summary:</strong><p>{summary}</p></div>
            <a href={dlUrl} className="dl-btn">Download .EPUB</a>
            <button onClick={() => window.location.reload()} className="reset-btn">New Book</button>
          </div>
        )}
      </div>
    </div>
  );
}
export default App;