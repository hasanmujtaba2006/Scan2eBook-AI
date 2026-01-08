import { useState } from 'react';

// FIX: Use the DIRECT subdomain URL, not the HF Spaces Hub URL
const API_BASE_URL = "https://hasanmujtaba-scan2ebook-ai.hf.space";

function App() {
  const [file, setFile] = useState(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

  const handleProcess = async () => {
    if (!file) return alert("Please select a file!");
    
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/process-page`, {
        method: 'POST',
        body: formData,
        // IMPORTANT: Do NOT set Headers manually for FormData
      });

      if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Server Error");
      }

      const data = await response.json();
      setContent(data.clean);
    } catch (error) {
      console.error("Connection Error:", error);
      alert("Network Error: Check browser console (Inspect > Console) for CORS details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>Scan2Ebook AI</h1>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={handleProcess} disabled={loading}>
        {loading ? "Processing..." : "Start OCR"}
      </button>
      <div className="output-box">
        <h3>Corrected Urdu Text:</h3>
        <textarea value={content} readOnly rows={10} style={{width: '100%'}} />
      </div>
    </div>
  );
}

export default App;