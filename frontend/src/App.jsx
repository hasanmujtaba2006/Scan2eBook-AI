import { useState } from 'react';
import './App.css';

const API_BASE_URL = "https://hasanmujtaba-scan2ebook-ai.hf.space";

function App() {
  const [file, setFile] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

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
      alert("Error processing image. Is the Backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>📱 Scan2Ebook AI</h1>
      
      <div className="upload-container">
        {/* capture हटा दिया गया है ताकि गैलरी का ऑप्शन भी आए */}
        <input 
          type="file" 
          accept="image/*" 
          onChange={(e) => setFile(e.target.files[0])} 
        />
        <p style={{marginTop: '10px', color: '#666'}}>
          {file ? `Selected: ${file.name}` : "Choose a file or take a photo"}
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