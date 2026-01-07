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

  const handleCover = (e) => {
    const file = e.target.files[0];
    if (file) {
      setCover(file);
      setCoverPreview(URL.createObjectURL(file));
    }
  };

  const handleUpload = async () => {
    if (!files.length) return;
    setStatus("processing");
    setMsg("Uploading...");

    const formData = new FormData();
    files.forEach(f => formData.append("files", f));
    if (cover) formData.append("cover", cover);
    formData.append("title", title || "My Scanned Book");

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
      }, 2000);
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
          <label>Pages:</label>
          <input type="file" multiple onChange={e => setFiles(Array.from(e.target.files))} accept="image/*" />
        </div>

        {status === "idle" && <button onClick={handleUpload} className="primary-btn">Create eBook</button>}
        
        {status === "processing" && (
          <div className="prog-container">
            <p>{msg}</p>
            <div className="bar"><div className="fill" style={{width: `${progress}%`}}></div></div>
          </div>
        )}

        {status === "success" && <a href={dlUrl} className="download-btn">Download .EPUB ⬇️</a>}
      </div>
    </div>
  );
}
export default App;