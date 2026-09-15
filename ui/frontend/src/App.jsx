import { Navigate, Route, Routes } from 'react-router-dom'
import Scratch from './pages/Scratch'

function App() {
  return (
    <Routes>
      <Route path="/scratch" element={<Scratch />} />
      <Route path="*" element={<Navigate to="/scratch" replace />} />
    </Routes>
  )
}

export default App
