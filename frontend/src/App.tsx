import { useState } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchHello = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/hello')
      const data = await response.json()
      setMessage(data.message)
    } catch (error) {
      console.error('Error fetching hello:', error)
      setMessage('Error: Could not reach the backend API.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="card">
        <h1>Vata Knowledge Graph</h1>
        <p className="description">
          A local-first application for managing personal knowledge using a graph-based structure.
        </p>
        
        <div className="action-area">
          <button 
            onClick={fetchHello} 
            disabled={loading}
            className="fetch-button"
          >
            {loading ? 'Fetching...' : 'Fetch Hello World'}
          </button>
        </div>

        {message && (
          <div className="message-box animate-fade-in">
            <p>{message}</p>
          </div>
        )}
      </div>
      
      <div className="footer">
        Powered by FastAPI & React
      </div>
    </div>
  )
}

export default App
