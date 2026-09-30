import type { ReactNode } from "react";
import { Routes, Route, Link, NavLink } from "react-router-dom";
import DashboardPage from "./routes/DashboardPage";
import NewAnalysisPage from "./routes/NewAnalysisPage";
import ProcessingPage from "./routes/ProcessingPage";
import ResultPage from "./routes/ResultPage";
import LoginPage from "./routes/LoginPage";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import "./App.css";

function AuthenticatedShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell app-shell-authenticated">
      <aside className="app-sidebar">
        <Link to="/" className="app-logo">
          GerAD
        </Link>
        <nav className="app-nav">
          <NavLink to="/" end className="nav-link">
            Dashboard
          </NavLink>
          <NavLink to="/analyses/new" className="nav-link">
            Nova Análise
          </NavLink>
          <span className="nav-link disabled" aria-disabled="true">
            Métricas
          </span>
          <span className="nav-link disabled" aria-disabled="true">
            Conteúdo
          </span>
          <span className="nav-link disabled" aria-disabled="true">
            Assistente de IA
          </span>
        </nav>
        <div className="user-menu">
          <div className="user-menu-info">
            <span className="user-menu-name">{user?.name}</span>
            <span className="user-menu-role">{user?.role}</span>
          </div>
          <button type="button" className="btn btn-secondary user-menu-logout" onClick={() => logout()}>
            Sair
          </button>
        </div>
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route
          path="/"
          element={
            <AuthenticatedShell>
              <DashboardPage />
            </AuthenticatedShell>
          }
        />
        <Route
          path="/analyses/new"
          element={
            <AuthenticatedShell>
              <NewAnalysisPage />
            </AuthenticatedShell>
          }
        />
        <Route
          path="/analyses/:id/processing"
          element={
            <AuthenticatedShell>
              <ProcessingPage />
            </AuthenticatedShell>
          }
        />
        <Route
          path="/analyses/:id"
          element={
            <AuthenticatedShell>
              <ResultPage />
            </AuthenticatedShell>
          }
        />
      </Route>
    </Routes>
  );
}

export default App;
