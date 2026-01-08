import { useState, useRef } from 'react';
import './App.css';

// Your backend URL
const API_BASE_URL = "https://hasanmujtaba-scan2ebook-ai.hf.space";

function App() {
  const [file, setFile] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  
  // Book State
  const [pages, setPages] = useState([]);
  const [bookTitle, setBookTitle] = useState("My Urdu Book");

  // Input Refs
  const cameraInputRef = useRef(null);
  const galleryInputRef = useRef(null);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleProcess = async () => {
    if (!file) return alert("Please select a file first!");
    setLoading(true);
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/process-page`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Backend Error");
      }

      const data = await response.json();
      setContent(data.clean);
    } catch (error) {
      console.error(error);
      alert("OCR Failed: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const addPage = () => {
    if (!content) return;
    setPages([...pages, content]);
    setContent(""); 
    setFile(null);
    alert(`Page ${pages.length + 1} Added!`);
  };

  // ✅ NEW: Download Book directly in Browser (No Server Needed)
  const downloadBook = () => {
    if (pages.length === 0) return alert("No pages to save!");

    // 1. Create simple HTML content with Urdu styling
    const header = `
      <html>
        <head>
          <meta charset="utf-8">
          <title>${bookTitle}</title>
          <style>
            body { 
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
              padding: 40px; 
              max-width: 800px; 
              margin: 0 auto; 
              direction: rtl; /* Right to Left for Urdu */
              text-align: right;
              background-color: #f9f9f9;
            }
            .page { 
              background: white; 
              padding: 20px; 
              margin-bottom: 20px; 
              border: 1px solid #ddd; 
              border-radius: 8px; 
            }
            h1 { text-align: center; color: #4f46e5; }
            h2 { color: #666; border-bottom: 1px solid #eee; padding-bottom: 10px; }
            p { font-size: 1.2rem; line-height: 1.8; white-space: pre-wrap; }
          </style>
        </head>
        <body>
          <h1>${bookTitle}</h1>
    `;

    const bodyContent = pages.map((pageText, index) => `
      <div class="page">
        <h2>Page ${index + 1}</h2>
        <p>${pageText}</p>
      </div>
    `).join("");

    const footer = `</body></html>`;
    const fullContent = header + bodyContent + footer;

    // 2. Create a Blob (File) from the text
    const blob = new Blob([fullContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);

    // 3. Trigger Download
    const a = document.createElement('a');
    a.href = url;
    a.download = `${bookTitle}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="App">
      <h1>📱 Scan2Ebook AI</h1>
      
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

      {/* Editor */}
      <textarea 
        className="editor-box"
        value={content} 
        onChange={(e) => setContent(e.target.value)}
        dir="rtl" 
        placeholder="Scanned text will appear here..."
      />

      {/* Actions */}
      <div className="book-actions">
        <button className="secondary-btn" onClick={addPage} disabled={!content}>
          ➕ Add Page ({pages.length})
        </button>
        
        {pages.length > 0 && (
          <button className="download-btn" onClick={downloadBook}>
            💾 Download Book (HTML)
          </button>
        )}
      </div>
    </div>
  );
}

export default App;