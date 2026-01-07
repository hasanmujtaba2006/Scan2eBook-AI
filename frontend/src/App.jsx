import { useState } from 'react'
import './App.css'

// CONFIGURATION: Ensure this matches your Render URL
const API_BASE_URL = "https://scan2ebook-ai.onrender.com"; 

function App() {
  const [files, setFiles] = useState([]) 
  const [previews, setPreviews] = useState([])
  const [bookTitle, setBookTitle] = useState("") 
  
  // Status and Progress states
  const [status, setStatus] = useState("idle") // idle, processing, success, error
  const [progress, setProgress] = useState(0)
  const [statusMessage, setStatusMessage] = useState("")
  const [downloadUrl, setDownloadUrl] = useState("")

  // Handle file selection and generate previews
  const handleFileChange = (e) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setFiles(selectedFiles);

      // Create object URLs for image previews
      const newPreviews = selectedFiles.map(file => URL.createObjectURL(file));
      setPreviews(newPreviews);
    }
  };

  const handleUpload = async () => {
    if (!files.length) return;

    // Reset states for a new conversion
    setStatus("processing");
    setProgress(0);
    setStatusMessage("Uploading images to server...");

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }
    
    // Send title (Backend defaults to "Scanned Book" if not used)
    formData.append("title", bookTitle || "My Scanned Book");

    try {
      // 1. Initial Request to get the Task ID
      const uploadRes = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) throw new Error("Upload failed");

      const { task_id } = await uploadRes.json();
      
      // 2. Poll the server for status every 2 seconds
      const intervalId = setInterval(async () => {
        try {
          const statusRes = await fetch(`${API_BASE_URL}/status/${task_id}`);
          const data = await statusRes.json();

          // Sync progress and message from the Python backend
          setProgress(data.progress);
          setStatusMessage(data.message);

          if (data.status === 'completed') {
            clearInterval(intervalId);
            // Construct the download URL using the backend's response
            setDownloadUrl(`${API_BASE_URL}${data.download_url}`);
            setStatus("success");
          }
          
          if (data.status === 'failed') {
            clearInterval(intervalId);
            setStatus("error");
            setStatusMessage(data.message || "Something went wrong during conversion.");
          }

        } catch (err) {
          console.error("Polling error:", err);
          clearInterval(intervalId);
          setStatus("error");
          setStatusMessage("Lost connection to the server.");
        }
      }, 2000); 

    } catch (error) {
      console.error("Upload error:", error);
      setStatus("error");
      setStatusMessage("Could not connect to the processing server.");
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>📚 Scan2eBook Pro</h1>
        <p className="subtitle">AI-Powered Batch Image to eBook Converter</p>

        {/* 1. Title Input */}
        <div className="input-group">
          <label>Book Title:</label>
          <input 
            type="text" 
            placeholder="e.g. Physics Ch 1 Notes" 
            value={bookTitle}
            onChange={(e) => setBookTitle(e.target.value)}
            className="text-input"
          />
        </div>

        {/* 2. Upload Zone */}
        <div className="upload-zone">
          <input type="file" onChange={handleFileChange} accept="image/*" multiple />
          {files.length === 0 && <p>Drag & Drop pages here or click to select</p>}
        </div>

        {/* 3. Previews */}
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

        {/* 4. Convert Button */}
        {status === "idle" && (
          <button onClick={handleUpload} disabled={files.length === 0} className="primary-btn">
            {files.length > 0 ? `✨ Convert ${files.length} Pages` : "Select Pages First"}
          </button>
        )}

        {/* 5. Processing / Progress Bar */}
        {status === "processing" && (
          <div className="loading">
            <div className="spinner"></div>
            <p className="loading-text">🤖 {statusMessage}</p>
            
            <div className="progress-container" style={{ width: '100%', backgroundColor: '#222', borderRadius: '10px', marginTop: '15px', border: '1px solid #444' }}>
              <div className="progress-bar" style={{
                width: `${progress}%`,
                height: '10px',
                backgroundColor: '#646cff',
                borderRadius: '10px',
                transition: 'width 0.4s ease-in-out'
              }}></div>
            </div>
            <p style={{textAlign: 'right', fontSize: '0.8rem', marginTop: '5px', color: '#888'}}>{progress}%</p>
          </div>
        )}

        {/* 6. Download / Success */}
        {status === "success" && (
          <div className="success">
            <h2>🎉 Conversion Finished!</h2>
            <p>Your eBook is ready for download.</p>
            <a href={downloadUrl} className="download-btn">
              Download .EPUB ⬇️
            </a>
            <button onClick={() => {setStatus("idle"); setFiles([]); setPreviews([]); setProgress(0);}} className="reset-btn">
              Convert Another Book
            </button>
          </div>
        )}

        {/* 7. Error State */}
        {status === "error" && (
            <div className="error">
                <h3>⚠️ Processing Error</h3>
                <p>{statusMessage}</p>
                <button onClick={() => setStatus("idle")} className="primary-btn">Try Again</button>
            </div>
        )}
      </div>
    </div>
  )
}

export default App