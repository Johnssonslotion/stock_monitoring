import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary.tsx'

// --- Global Axios Configuration ---
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'; // Default if missing
const API_KEY = import.meta.env.VITE_API_KEY || '';

// Set default base URL
// Note: App.tsx calls `/candles/...` so we set base to `/api/v1`
axios.defaults.baseURL = API_URL.endsWith('/api/v1') ? API_URL : `${API_URL}/api/v1`;

// Set default headers
if (API_KEY) {
  axios.defaults.headers.common['x-api-key'] = API_KEY;
}

console.log(`🌐 Axios Configured: Base=${axios.defaults.baseURL}, KeyPresent=${!!API_KEY}`);


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
