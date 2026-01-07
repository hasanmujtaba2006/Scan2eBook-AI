import { useState } from 'react'
import './App.css'

const API_BASE_URL = "https://scan2ebook-ai.onrender.com"; 

function App() {
  const [files, setFiles] = useState([]);
  const [cover, setCover] = useState(null);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("idle");
  const [progress, setProgress] = useState(0);
  const [summary, setSummary] = useState("");
  const [dlUrl, setDlUrl] = useState("");
  const [editableContent, setEditableContent] = useState("");
  const [isPreviewing, setIsPreviewing] = useState(false);

  const handleGetPreview = async () => {
    if (!files.length) return;
    setStatus("processing");
    const formData = new FormData();
    formData.append("file", files[0]);
    const res = await fetch(`${API_BASE_URL}/preview-page`, { method: 'POST', body: formData });
    const data = await res.json();
    setEditableContent(data.html);
    setIsPreviewing(true);
    setStatus("idle");
  };

  const handleUpload = async () => {
    setStatus("processing");
    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    if (cover) formData.append("cover", cover);
    formData.append("title", title || "My Urdu eBook");

    const res = await fetch(`${API_BASE_URL}/upload`, { method: 'POST', body: formData });
    const { task_id } = await res.json();
    const interval = setInterval(async () => {
      const sRes = await fetch(`${API_BASE_URL}/status/${task_id}`);
      const data = await sRes.json();
      setProgress(data.progress);
      if (data.status === 'completed') {
        clearInterval(interval);
        setDlUrl(`${API_BASE_URL}${data.download_url}`);
        setSummary(data.summary);
        setStatus("success");
      }
    }, 3000);
  };

  return (
    <div className="container">
      <div className="card">
        <h1>📚 Scan2eBook AI</h1>
        <input type="text" placeholder="Book Title" value={title} onChange={e => setTitle(e.target.value)} className="text-input" />
        <input type="file" multiple onChange={e => setFiles(Array.from(e.target.files))} accept="image/*" className="file-input" />
        
        {isPreviewing && (
          <div className="preview-mode">
            <h3>📝 Page Editor</h3>
            <textarea dir="rtl" className="urdu-editor" value={editableContent} onChange={e => setEditableContent(e.target.value)} />
          </div>
        )}

        {status === "idle" && (
          <div className="btn-group">
            <button onClick={handleGetPreview} className="sec-btn">🔍 Preview Page 1</button>
            <button onClick={handleUpload} className="pri-btn">🚀 Convert Full Book</button>
          </div>
        )}

        {status === "processing" && (
          <div className="loader">
            <div className="bar"><div className="fill" style={{width: `${progress}%`}}></div></div>
            <p>Processing: {progress}%</p>
          </div>
        )}

        {status === "success" && (
          <div className="success">
            <div className="summary-box" dir="rtl">
              <strong>AI Summary:</strong>
              <p>{summary}</p>
            </div>
            <a href={dlUrl} className="dl-btn">Download EPUB</a>
          </div>
        )}
      </div>
    </div>
  );
}
export default App;