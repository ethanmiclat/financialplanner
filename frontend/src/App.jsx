import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import { LogProvider } from './components/LogSheet'
import PlanPage from './pages/PlanPage'
import GoalPage from './pages/GoalPage'
import ProjectionPage from './pages/ProjectionPage'
import SchedulePage from './pages/SchedulePage'
import AccountsPage from './pages/AccountsPage'
import { AskAnswer, AskIndex } from './pages/AskPage'
import { LearnDetail, LearnIndex } from './pages/LearnPage'
import YouPage from './pages/YouPage'
import { api } from './lib/api'
import { useApi } from './lib/useApi'

export default function App() {
  // Loaded once and shared: every page can turn jargon into a tappable definition.
  const { data: glossary } = useApi(api.glossary, [])

  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>
      <LogProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<PlanPage glossary={glossary} />} />
          <Route path="/projection" element={<ProjectionPage glossary={glossary} />} />
          <Route path="/schedule" element={<SchedulePage glossary={glossary} />} />
          <Route path="/goal" element={<GoalPage glossary={glossary} />} />
          <Route path="/accounts" element={<AccountsPage glossary={glossary} />} />
          <Route path="/ask" element={<AskIndex glossary={glossary} />} />
          <Route path="/ask/:id" element={<AskAnswer glossary={glossary} />} />
          <Route path="/learn" element={<LearnIndex glossary={glossary} />} />
          <Route path="/learn/:key" element={<LearnDetail glossary={glossary} />} />
          <Route path="/you" element={<YouPage glossary={glossary} />} />
        </Routes>
      </AppShell>
      </LogProvider>
    </BrowserRouter>
  )
}
