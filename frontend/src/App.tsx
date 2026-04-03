import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import MUDApp from './pages/MUDApp'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<MUDApp />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App