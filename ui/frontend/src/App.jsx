import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Shell from './components/Shell'
import { SessionProvider, useSession } from './lib/session'
import Ask from './pages/Ask'
import Banquets from './pages/Banquets'
import BanquetDetail from './pages/BanquetDetail'
import Brain from './pages/Brain'
import Connections from './pages/Connections'
import DataStudio from './pages/DataStudio'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Proof from './pages/Proof'
import Scratch from './pages/Scratch'

function SignedIn({ children }) {
  const { user, signOut } = useSession()
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return (
    <Shell user={user} onSignOut={signOut}>
      {children}
    </Shell>
  )
}

function Routing() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/scratch" element={<Scratch />} />
      <Route
        path="/overview"
        element={
          <SignedIn>
            <Overview />
          </SignedIn>
        }
      />
      <Route
        path="/banquets"
        element={
          <SignedIn>
            <Banquets />
          </SignedIn>
        }
      />
      <Route
        path="/banquets/:eventId"
        element={
          <SignedIn>
            <BanquetDetail />
          </SignedIn>
        }
      />
      <Route
        path="/proof"
        element={
          <SignedIn>
            <Proof />
          </SignedIn>
        }
      />
      <Route
        path="/ask"
        element={
          <SignedIn>
            <Ask />
          </SignedIn>
        }
      />
      <Route
        path="/data"
        element={
          <SignedIn>
            <DataStudio />
          </SignedIn>
        }
      />
      <Route
        path="/brain"
        element={
          <SignedIn>
            <Brain />
          </SignedIn>
        }
      />
      <Route
        path="/connections"
        element={
          <SignedIn>
            <Connections />
          </SignedIn>
        }
      />
      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <SessionProvider>
      <Routing />
    </SessionProvider>
  )
}

export default App
