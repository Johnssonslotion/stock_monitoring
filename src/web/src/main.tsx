import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary.tsx'

// Configure Axios globally before any components load
axios.defaults.baseURL = '/api/v1';
axios.defaults.headers.common['x-api-key'] = import.meta.env.VITE_API_KEY || 'super-secret-key';
console.log('🔑 [main.tsx] API Key configured:', axios.defaults.headers.common['x-api-key']);


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
