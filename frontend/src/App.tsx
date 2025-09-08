import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import WorkspacePage from './pages/WorkspacePage'
import ExperimentPage from './pages/ExperimentPage'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<WorkspacePage />} />
          <Route path="/experiment" element={<ExperimentPage />} />
          <Route path="/experiment/:id" element={<ExperimentPage />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App