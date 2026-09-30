import { Link } from "react-router-dom";
import { useAnalyses } from "../hooks/useAnalyses";
import { formatDate, formatStatus } from "../lib/format";

export default function DashboardPage() {
  const { data, isLoading, isError } = useAnalyses();

  return (
    <div>
      <div className="page-header">
        <h1>Análises</h1>
        <Link to="/analyses/new" className="btn btn-primary">
          + Nova análise
        </Link>
      </div>

      {isLoading && <p>Carregando...</p>}
      {isError && <p className="error-text">Não foi possível carregar as análises.</p>}

      {data && data.items.length === 0 && (
        <div className="empty-state card">
          <p>Nenhuma análise ainda.</p>
          <Link to="/analyses/new" className="btn btn-primary">
            Criar a primeira análise
          </Link>
        </div>
      )}

      {data && data.items.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Participante</th>
              <th>Objetivo</th>
              <th>Status</th>
              <th>Data</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              <tr key={item.id}>
                <td>
                  <Link
                    to={
                      item.status === "COMPLETED" || item.status === "FAILED"
                        ? `/analyses/${item.id}`
                        : `/analyses/${item.id}/processing`
                    }
                  >
                    {item.participant_name}
                  </Link>
                </td>
                <td>{item.objective}</td>
                <td>
                  <span className={`status-badge status-${item.status}`}>
                    {formatStatus(item.status)}
                  </span>
                </td>
                <td>{formatDate(item.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
