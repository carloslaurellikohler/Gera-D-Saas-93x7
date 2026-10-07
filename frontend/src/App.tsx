import type { ReactNode } from "react";
import { Routes, Route } from "react-router-dom";
import DashboardPage from "./routes/DashboardPage";
import NewAnalysisPage from "./routes/NewAnalysisPage";
import ProcessingPage from "./routes/ProcessingPage";
import ResultPage from "./routes/ResultPage";
import LoginPage from "./routes/LoginPage";
import MetricsPage from "./routes/MetricsPage";
import LibraryPage from "./routes/LibraryPage";
import LearningPathDetailPage from "./routes/LearningPathDetailPage";
import AssistantPage from "./routes/AssistantPage";
import AdminDashboardPage from "./routes/AdminDashboardPage";
import CalibrationPage from "./routes/CalibrationPage";
import UserAdminPage from "./routes/UserAdminPage";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import RequireRole from "./components/auth/RequireRole";
import Sidebar from "./components/ui/Sidebar";
import "./App.css";

function AuthenticatedShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell app-shell-authenticated">
      <Sidebar />
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
        <Route
          path="/metricas"
          element={
            <AuthenticatedShell>
              <MetricsPage />
            </AuthenticatedShell>
          }
        />
        <Route
          path="/biblioteca"
          element={
            <AuthenticatedShell>
              <LibraryPage />
            </AuthenticatedShell>
          }
        />
        <Route
          path="/biblioteca/trilhas/:id"
          element={
            <AuthenticatedShell>
              <LearningPathDetailPage />
            </AuthenticatedShell>
          }
        />
        <Route
          path="/assistente"
          element={
            <AuthenticatedShell>
              <AssistantPage />
            </AuthenticatedShell>
          }
        />
        <Route
          path="/admin"
          element={
            <AuthenticatedShell>
              <RequireRole allow={["ADMIN"]}>
                <AdminDashboardPage />
              </RequireRole>
            </AuthenticatedShell>
          }
        />
        <Route
          path="/calibracao"
          element={
            <AuthenticatedShell>
              <RequireRole allow={["ADMIN"]}>
                <CalibrationPage />
              </RequireRole>
            </AuthenticatedShell>
          }
        />
        <Route
          path="/usuarios"
          element={
            <AuthenticatedShell>
              <RequireRole allow={["ADMIN"]}>
                <UserAdminPage />
              </RequireRole>
            </AuthenticatedShell>
          }
        />
      </Route>
    </Routes>
  );
}

export default App;
