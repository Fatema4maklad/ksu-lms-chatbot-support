import { useState } from 'react';
import ReactMarkdown from 'react-markdown'; // <-- Add this import
import './App.css';

function App() {
  const [apiMessage, setApiMessage] = useState('Connecting to backend...')

  useEffect(() => {
    // Calls the FastAPI server running locally
    fetch('http://127.0.0.1:8000/')
      .then(response => response.json())
      .then(data => setApiMessage(data.message))
      .catch(error => setApiMessage('Backend offline'))
  }, [])

  return (
    <div className="flex h-screen items-center justify-center bg-slate-100">
      <div className="p-8 rounded-lg shadow-lg bg-white border border-slate-200">
        <h1 className="text-2xl font-bold text-blue-800">
          Status: {apiMessage}
        </h1>
      </div>
    </div>
  )
}

export default App;