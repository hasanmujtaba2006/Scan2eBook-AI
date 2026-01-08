import { useState, useRef } from 'react';
import './App.css';

// Your backend URL
const API_BASE_URL = "https://hasanmujtaba-scan2ebook-ai.hf.space";

function App() {
  const [file, setFile] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

  // References to hidden inputs
  const cameraInputRef = useRef(null);
  const galleryInputRef = useRef(null);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleProcess = async () => {
    if (!file) return alert("Please select or take a photo first!");
    
    setLoading(true);
    setContent("");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/process-page`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Server Error");
      }

      const data = await response.json();
      setContent(data.clean);
    } catch (error) {
      console.error("Connection Error:", error);
      alert("Error processing image. Check your internet or backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>📱 Scan2Ebook AI</h1>
      
      <div className="upload-container">
        {/* Hidden Input for Camera (Force Camera) */}
        <input 
          type="file" 
          accept="image/*" 
          capture="environment"
          ref={cameraInputRef}
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        {/* Hidden Input for Gallery (Standard Picker) */}
        <input 
          type="file" 
          accept="image/*" 
          ref={galleryInputRef}
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        {/* Custom Buttons */}
        <div className="button-group">
          <button 
            className="action-btn camera-btn" 
            onClick={() => cameraInputRef.current.click()}
          >
            📸 Take Photo
          </button>
          
          <button 
            className="action-btn gallery-btn" 
            onClick={() => galleryInputRef.current.click()}
          >
            🖼️ Open Gallery
          </button>
        </div>

        <p style={{marginTop: '15px', color: '#666', fontWeight: 'bold'}}>
          {file ? `✅ Selected: ${file.name}` : "No image selected"}
        </p>
      </div>

      <button className="primary-btn" onClick={handleProcess} disabled={loading}>
        {loading ? (
          <>
            <span className="loader"></span> Processing...
          </>
        ) : "✨ Start OCR & AI Clean"}
      </button>

      {content && (
        <div className="output-box">
          <h3>Corrected Urdu Text:</h3>
          <textarea value={content} readOnly rows={15} dir="rtl" />
        </div>
      )}
    </div>
  );
}

export default App;