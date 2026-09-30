import { Routes, Route, Link } from "react-router-dom";
import DashboardPage from "./routes/DashboardPage";
import NewAnalysisPage from "./routes/NewAnalysisPage";
import ProcessingPage from "./routes/ProcessingPage";
import ResultPage from "./routes/ResultPage";
import "./App.css";

function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-logo">
          GerAD
        </Link>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/analyses/new" element={<NewAnalysisPage />} />
          <Route path="/analyses/:id/processing" element={<ProcessingPage />} />
          <Route path="/analyses/:id" element={<ResultPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
