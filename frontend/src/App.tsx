import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import WorkspacePage from './pages/WorkspacePage'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          <Route path="/" element={<WorkspacePage />} />
          <Route path="/experiment/:id" element={
            <div className="flex items-center justify-center h-screen">
              <div className="text-center">
                <h2 className="text-2xl font-semibold text-gray-900 mb-4">Experiment View</h2>
                <p className="text-gray-600">Coming soon...</p>
              </div>
            </div>
          } />
        </Routes>
      </div>
    </Router>
  )
}

export default App