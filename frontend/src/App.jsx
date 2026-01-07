import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [files, setFiles] = useState([]) 
  const [previews, setPreviews] = useState([])
  const [bookTitle, setBookTitle] = useState("") 
  const [status, setStatus] = useState("idle") 
  const [downloadUrl, setDownloadUrl] = useState("")

  // When files change, generate preview URLs
  const handleFileChange = (e) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setFiles(selectedFiles);

      // Create object URLs for previews
      const newPreviews = selectedFiles.map(file => URL.createObjectURL(file));
      setPreviews(newPreviews);
    }
  };

  const handleUpload = async () => {
    if (!files.length) return;

    setStatus("processing");
    const formData = new FormData();
    
    // Add Files
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }
    // Add Title (Defaults to "My Book" if empty)
    formData.append("title", bookTitle || "My Scanned Book");

    try {
      const response = await fetch("http://127.0.0.1:8000/convert-to-epub/", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        setDownloadUrl(url);
        setStatus("success");
      } else {
        setStatus("error");
      }
    } catch (error) {
      setStatus("error");
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>📚 Scan2eBook Pro</h1>
        <p className="subtitle">Batch process your book pages into one eBook</p>

        {/* 1. Title Input */}
        <div className="input-group">
          <label>Book Title:</label>
          <input 
            type="text" 
            placeholder="e.g. Physics Notes Ch 1" 
            value={bookTitle}
            onChange={(e) => setBookTitle(e.target.value)}
            className="text-input"
          />
        </div>

        {/* 2. File Upload */}
        <div className="upload-zone">
          <input type="file" onChange={handleFileChange} accept="image/*" multiple />
          {files.length === 0 && <p>Drag & Drop pages here or click to select</p>}
        </div>

        {/* 3. Image Previews (The New Feature!) */}
        {previews.length > 0 && (
          <div className="preview-grid">
            {previews.map((src, index) => (
              <div key={index} className="preview-item">
                <img src={src} alt={`Page ${index + 1}`} />
                <span>Pg {index + 1}</span>
              </div>
            ))}
          </div>
        )}

        {/* 4. Action Button */}
        {status === "idle" && (
          <button onClick={handleUpload} disabled={files.length === 0} className="primary-btn">
            {files.length > 0 ? `✨ Convert ${files.length} Pages` : "Select Pages First"}
          </button>
        )}

        {/* Loading State */}
        {status === "processing" && (
          <div className="loading">
            <div className="spinner"></div>
            <p>🤖 Reading {files.length} pages...</p>
          </div>
        )}

        {/* Success State */}
        {status === "success" && (
          <div className="success">
            <h2>🎉 "{bookTitle || "My Scanned Book"}" is Ready!</h2>
            <a href={downloadUrl} download={`${bookTitle || "My_Book"}.epub`} className="download-btn">
              Download eBook ⬇️
            </a>
            <button onClick={() => {setStatus("idle"); setFiles([]); setPreviews([]);}} className="reset-btn">
              Scan New Book
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default App