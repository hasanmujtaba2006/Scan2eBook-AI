import { useState, useRef } from 'react';
import './App.css';

const API_BASE_URL = "https://hasanmujtaba-scan2ebook-ai.hf.space";

function App() {
  const [file, setFile] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  
  // New States for Book Mode
  const [pages, setPages] = useState([]);
  const [bookTitle, setBookTitle] = useState("My Urdu Book");
  const [downloading, setDownloading] = useState(false);

  const cameraInputRef = useRef(null);
  const galleryInputRef = useRef(null);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleProcess = async () => {
    if (!file) return alert("Select a photo first!");
    setLoading(true);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/process-page`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) throw new Error("Backend Error");
      const data = await response.json();
      setContent(data.clean);
    } catch (error) {
      alert("OCR Failed. Is backend running?");
    } finally {
      setLoading(false);
    }
  };

  // Add current text to the book list
  const addPage = () => {
    if (!content) return;
    setPages([...pages, content]);
    setContent(""); // Clear for next page
    setFile(null); // Reset file
    alert(`Page ${pages.length + 1} added!`);
  };

  // Download the final EPUB
  const downloadEpub = async () => {
    if (pages.length === 0) return alert("No pages scanned yet!");
    setDownloading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/generate-epub`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: bookTitle, pages: pages }),
      });

      if (!response.ok) throw new Error("Download Failed");

      // Handle the file blob
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${bookTitle}.epub`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (error) {
      console.error(error);
      alert("Failed to create eBook.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="App">
      <h1>📱 Scan2Ebook AI</h1>

      {/* Book Title Input */}
      <input 
        className="title-input"
        type="text" 
        value={bookTitle} 
        onChange={(e) => setBookTitle(e.target.value)}
        placeholder="Enter Book Title"
      />
      
      <div className="upload-container">
        {/* Hidden Inputs */}
        <input type="file" accept="image/*" capture="environment" ref={cameraInputRef} style={{ display: 'none' }} onChange={handleFileSelect} />
        <input type="file" accept="image/*" ref={galleryInputRef} style={{ display: 'none' }} onChange={handleFileSelect} />

        <div className="button-group">
          <button className="action-btn camera-btn" onClick={() => cameraInputRef.current.click()}>📸 Photo</button>
          <button className="action-btn gallery-btn" onClick={() => galleryInputRef.current.click()}>🖼️ Gallery</button>
        </div>
        <p style={{marginTop: '10px', fontWeight: 'bold'}}>{file ? `✅ ${file.name}` : "Select a page"}</p>
      </div>

      <button className="primary-btn" onClick={handleProcess} disabled={loading}>
        {loading ? "Processing..." : "✨ Scan Page"}
      </button>

      {/* Editor Area */}
      <textarea 
        className="editor-box"
        value={content} 
        onChange={(e) => setContent(e.target.value)} // User can edit text
        dir="rtl" 
        placeholder="Scanned text will appear here..."
      />

      {/* Book Actions */}
      <div className="book-actions">
        <button className="secondary-btn" onClick={addPage} disabled={!content}>
          ➕ Add Page to Book ({pages.length})
        </button>
        
        {pages.length > 0 && (
          <button className="download-btn" onClick={downloadEpub} disabled={downloading}>
            {downloading ? "Building..." : "📚 Download EPUB"}
          </button>
        )}
      </div>
    </div>
  );
}

export default App;